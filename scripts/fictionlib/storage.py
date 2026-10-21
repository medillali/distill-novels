"""文件事务：独占锁、原子替换、可恢复的写前日志。"""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import uuid


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def new_id(prefix):
    return prefix + '-' + uuid.uuid4().hex


def safe_path(root, relative):
    root = Path(root).resolve()
    name = str(relative)
    path = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('非法相对路径: ' + name)
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root):
        raise ValueError('路径越出资料目录: ' + name)
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('资料目录不接受符号链接: ' + name)
    return target


def read_json(path):
    def reject(value):
        raise ValueError('JSON 不接受非有限数值: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=reject)


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(text.encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def recover(root):
    """调用者必须持有锁；未完成的事务统一回滚。"""
    journal = safe_path(root, '.journal.json')
    if not journal.exists():
        return False
    before = read_json(journal)['before']
    # 先验证所有路径，不能在发现错误前就部分恢复。
    paths = {name: safe_path(root, name) for name in before}
    for name, original in before.items():
        if original is None:
            paths[name].unlink(missing_ok=True)
        else:
            atomic_write(paths[name], original)
    journal.unlink()
    return True


@contextmanager
def locked(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = safe_path(root, '.lock')
    with lock.open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError('资料库正被另一操作使用，请稍后重试') from exc
        try:
            recover(root)
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def commit(root, changes):
    """changes 为相对路径到 UTF-8 文本的映射；调用者必须持有锁。"""
    if not changes:
        return
    if any(name in ('.journal.json', '.lock') for name in changes):
        raise ValueError('不能覆盖事务控制文件')
    paths = {name: safe_path(root, name) for name in changes}
    before = {name: path.read_text(encoding='utf-8') if path.exists() else None for name, path in paths.items()}
    journal = safe_path(root, '.journal.json')
    atomic_write(journal, json_text({'before': before}))
    try:
        for name, text in changes.items():
            atomic_write(paths[name], text)
        journal.unlink()
    except BaseException:
        # 即使本次回滚被中断，下次持锁读取也会完成回滚。
        recover(root)
        raise
