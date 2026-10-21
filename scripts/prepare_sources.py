#!/usr/bin/env python3
"""Normalize prose sources into per-source UTF-8 text plus a manifest."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from fictionlib.storage import commit, json_text, locked, new_id, read_json

SUPPORTED = {".txt", ".md", ".markdown", ".rst", ".adoc", ".html", ".htm", ".rtf", ".epub", ".docx"}
CHAPTER_RE = re.compile(
    r"(?im)^[ \t]*(?:#{1,6}[ \t]*)?(?:chapter[ \t]+(?:\d+|[ivxlcdm]+)|第[零〇一二三四五六七八九十百千万两\d]+[章节回卷部篇]|序章|楔子|尾声|终章)[^\n]*"
)


def read_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16')
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def strip_markup(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", "\n", value)
    return html.unescape(value)


def extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    paragraphs = []
    for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        paragraphs.append("".join(node.text or "" for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")))
    return "\n".join(paragraphs)


def extract_epub(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        def read_member(name):
            if name not in archive.namelist():
                raise ValueError('EPUB spine 成员缺失: ' + name)
            if archive.getinfo(name).file_size > 64 * 1024 * 1024:
                raise ValueError('EPUB 成员过大: ' + name)
            return archive.read(name)
        try:
            container = ET.fromstring(read_member('META-INF/container.xml'))
            rootfile = next(n for n in container.iter() if n.tag.rsplit('}', 1)[-1] == 'rootfile')
            opf = rootfile.attrib['full-path']
            package = ET.fromstring(read_member(opf))
            items = {n.attrib['id']: n.attrib['href'] for n in package.iter() if n.tag.rsplit('}', 1)[-1] == 'item'}
            spine = [n.attrib['idref'] for n in package.iter() if n.tag.rsplit('}', 1)[-1] == 'itemref']
            if not spine:
                raise ValueError('EPUB 缺失 spine，无法确认叙事顺序')
            names = []
            for reference in spine:
                href = unquote(items[reference].split('#')[0])
                name = posixpath.normpath(posixpath.join(posixpath.dirname(opf), href))
                if name.startswith(('../', '/')) or ':' in name or '\\' in name:
                    raise ValueError('EPUB spine 包含非法路径')
                names.append(name)
            return '\n\n'.join(strip_markup(read_member(name).decode('utf-8')) for name in names)
        except (KeyError, StopIteration, ET.ParseError, UnicodeError) as exc:
            raise ValueError('EPUB spine 无效或正文编码错误: ' + str(exc)) from exc


def extract(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".epub":
        return extract_epub(path)
    value = read_text(path)
    if suffix in {".html", ".htm"}:
        value = strip_markup(value)
    if suffix == ".rtf":
        value = re.sub(r"\\'[0-9a-fA-F]{2}|\\[a-zA-Z]+-?\d* ?|[{}]", "", value)
    return value.replace("\r\n", "\n").replace("\r", "\n")


def discover(inputs: list[str]) -> list[Path]:
    found = []
    for raw in inputs:
        path = Path(raw)
        candidates = path.rglob("*") if path.is_dir() else [path]
        found.extend(candidate.resolve() for candidate in candidates if candidate.is_file() and candidate.suffix.lower() in SUPPORTED)
    return sorted(set(found))


def chapter_index(text):
    matches = list(CHAPTER_RE.finditer(text))
    starts = [(m.start(), m.group(0).strip()) for m in matches]
    if not starts or text[:starts[0][0]].strip():
        starts.insert(0, (0, '未分章正文' if not starts else '章前内容'))
    return [{'chapter_id': f'ch-{i + 1:04d}', 'title': title,
             'start_offset': start, 'end_offset': starts[i + 1][0] if i + 1 < len(starts) else len(text),
             'start_line': text.count('\n', 0, start) + 1,
             'end_line': text.count('\n', 0, (starts[i + 1][0] if i + 1 < len(starts) else len(text)) - 1) + 1}
            for i, (start, title) in enumerate(starts)]


def make_revision(text, output, source_id):
    revision = hashlib.sha256(text.encode('utf-8')).hexdigest()
    relative = f'sources/{source_id}/{revision}.txt'
    return {'revision': revision, 'normalized_path': str(output / relative), 'characters': len(text),
            'line_count': len(text.splitlines()), 'chapters': chapter_index(text)}, relative


def prepare(inputs, output, source_id=None):
    paths = discover([str(p) for p in inputs])
    if not paths:
        raise ValueError('未找到支持的来源文件；已有清单未修改')
    if source_id and len(paths) != 1:
        raise ValueError('--source-id 修订操作必须只有一个输入文件')
    output = Path(output).resolve()
    # 提取全部成功后才进入提交，坏文件不会留下半份清单。
    extracted = [(path, extract(path).replace('\r\n', '\n').replace('\r', '\n')) for path in paths]
    with locked(output):
        manifest = read_json(output / 'manifest.json') if (output / 'manifest.json').exists() else {'sources': [], 'warnings': []}
        if manifest.get('schema_version', 1) not in (1, 2):
            raise ValueError('不支持的来源清单版本')
        changes = {}
        for item in manifest['sources']:
            if 'revisions' not in item:
                legacy = Path(item['normalized_path']).resolve()
                if not legacy.is_relative_to(output) or not legacy.is_file():
                    raise ValueError('旧清单的原始文本缺失或不在输出目录，需人工迁移: ' + item['source_id'])
                text = legacy.read_text(encoding='utf-8')
                alias = item['source_id']
                item['source_id'] = new_id('src')
                item['aliases'] = [alias]
                revision, relative = make_revision(text, output, item['source_id'])
                item.update(revision)
                item['revisions'] = [revision]
                changes[relative] = text
        target = None
        if source_id:
            target = next((s for s in manifest['sources'] if source_id == s['source_id'] or source_id in s.get('aliases', [])), None)
            if target is None:
                raise ValueError('未登记的 source_id，不能推测作品身份')
        for path, text in extracted:
            if not text.strip():
                raise ValueError('来源正文为空: ' + path.name)
            content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            matches = [s for s in manifest['sources'] if any(r['revision'] == content_hash for r in s['revisions'])]
            if matches and target is not None and matches[0]['source_id'] != target['source_id']:
                raise ValueError('此内容已登记为另一个作品，需先解决来源冲突')
            if matches:
                continue
            item = target
            if item is None:
                item = {'source_id': new_id('src'), 'aliases': [], 'title': path.stem, 'revisions': []}
                manifest['sources'].append(item)
            revision, relative = make_revision(text, output, item['source_id'])
            item.update(revision)
            item.update(filename=path.name, format=path.suffix.lower())
            item['revisions'].append(revision)
            item['chapter_headings'] = [c['title'] for c in revision['chapters']]
            item['chapter_detection_confidence'] = 'high' if len(list(CHAPTER_RE.finditer(text))) >= 3 else 'low'
            changes[relative] = text
        manifest['schema_version'] = 2
        manifest['warnings'] = [s['source_id'] + ': 章节识别需检查' for s in manifest['sources'] if s.get('chapter_detection_confidence') != 'high']
        changes['manifest.json'] = json_text(manifest)
        commit(output, changes)
        return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--output", required=True)
    parser.add_argument('--source-id', help='明确将一个输入文件登记为已知作品的新修订')
    args = parser.parse_args()
    try:
        manifest = prepare(args.inputs, args.output, args.source_id)
        print(json.dumps({'sources': len(manifest['sources']), 'manifest': str(Path(args.output).resolve() / 'manifest.json'), 'warnings': manifest['warnings']}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
