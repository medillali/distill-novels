"""双端工作包、保守三方合并和可校验备份。"""

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid
import zipfile

from .graph import all_graphs, graph_path, graph_updates
from .storage import atomic_write, commit, digest, json_text, locked, new_id, read_json, safe_path
from .vault import ASSET_FIELDS, KINDS, Vault, identifier, now, require_text

GRAPH_FIELDS = {'title', 'nodes', 'edges', 'threads', 'coverage'}
MISSING = object()


def export_bundle(vault, destination, asset_ids=None, project_id=None, max_chars=30000):
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('工作包输出目录必须为空，避免覆盖既有版本')
    if max_chars < 1000:
        raise ValueError('上下文预算至少为 1000 字符')
    with locked(vault.root):
        project = vault._project(project_id) if project_id else None
        current = vault._assets()
        if asset_ids is not None:
            chosen = [vault._get_asset(aid) for aid in asset_ids]
        elif project:
            chosen = [vault._get_asset(r['asset_id'], r['revision']) for r in project['assets']]
            chosen += [a for a in current if a.get('project_id') == project_id]
        else:
            chosen = current
        graphs = [g for g in all_graphs(vault) if not project_id or g['owner'] == {'kind': 'project', 'id': project_id}]
        selected = {(a['asset_id'], a['revision']): a for a in chosen}
        for graph in graphs:
            for node in graph['nodes']:
                ids = list(node.get('characters', [])) + [k['observer'] for k in node.get('knowledge', []) if k['observer'] != 'reader']
                for aid in ids:
                    asset = vault._get_asset(aid)
                    selected.setdefault((aid, asset['revision']), asset)
        queue = list(selected.values())
        while queue:
            asset = queue.pop()
            for ref in asset.get('derived_from', []):
                key = (ref['asset_id'], ref['revision'])
                if key not in selected:
                    selected[key] = vault._get_asset(*key)
                    queue.append(selected[key])
        assets = list(selected.values())
        source_ids = {e['source_id'] for a in assets for e in a['evidence']}
        source_ids |= {c['source_id'] for g in graphs for c in g.get('coverage', [])}
        for g in graphs:
            source_ids |= {e['source_id'] for n in g['nodes'] + g['edges'] for e in n.get('evidence', [])}
        bundle = {'schema_version': 1, 'vault_id': vault._read('vault.json')['vault_id'], 'bundle_id': new_id('bundle'),
                  'created_at': now(), 'assets': assets, 'graphs': graphs, 'sources': [vault._source(s) for s in sorted(source_ids)],
                  'project': project, 'omitted_asset_ids': [a['asset_id'] for a in current if a['asset_id'] not in {s['asset_id'] for s in assets}]}
        context = ['# 小说创作工作包', '', f"资料库：{bundle['vault_id']}\n工作包：{bundle['bundle_id']}", '',
                   '完整卡片和图数据见 bundle.json。不要把参考研究卡直接当作原创作品事实。',
                   '修改通过 changes.json 回收；保留基线编号与哈希。content 的 patch 值是完整内容对象。', '']
        omitted = []
        for asset in assets:
            block = f"## {asset['title']}\n\nID: {asset['asset_id']} · v{asset['revision']} · {asset['scope']}\n\n{asset['content']['summary']}\n\n用户笔记：{asset['user_notes']}\n"
            if len('\n'.join(context)) + len(block) > max_chars:
                omitted.append(asset['asset_id'])
            else:
                context.append(block)
        context += ['## 图结构', ''] + [f"- {g['title']} · {len(g['nodes'])} 个节点 · {len(g['threads'])} 条剧情线" for g in graphs]
        context += ['', '## 上下文范围', '', '未展开卡片（仍在 bundle.json）：' + (', '.join(omitted) or '无'),
                    '未选择进工作包的资产：' + (', '.join(bundle['omitted_asset_ids']) or '无'), '']
        template = {'schema_version': 1, 'vault_id': bundle['vault_id'], 'bundle_id': bundle['bundle_id'], 'changes': [], 'new_assets': []}
        for kind, records, key in [('asset', assets, 'asset_id'), ('graph', graphs, 'graph_id')]:
            for record in records:
                template['changes'].append({'kind': kind, 'id': record[key], 'base_revision': record['revision'], 'base_hash': digest(record), 'patch': {}})
        files = {'bundle.json': json_text(bundle), 'context.md': '\n'.join(context), 'changes-template.json': json_text(template)}
        manifest = {'schema_version': 1, 'bundle_id': bundle['bundle_id'], 'files': {k: hashlib.sha256(v.encode('utf-8')).hexdigest() for k, v in files.items()}}
        destination.mkdir(parents=True, exist_ok=True)
        for name, text in {**files, 'manifest.json': json_text(manifest)}.items():
            atomic_write(safe_path(destination, name), text)
        # 必须保留共同基线，回收时不信任远端提供的旧内容。
        commit(vault.root, {f"exchanges/outbox/{bundle['bundle_id']}.json": json_text(bundle)})
        return bundle


def merge_three(base, local, remote, path=''):
    if remote == base:
        return local, []
    if local == base or local == remote:
        return remote, []
    if all(isinstance(value, dict) for value in (base, local, remote)):
        merged, conflicts = {}, []
        for key in sorted(base.keys() | local.keys() | remote.keys()):
            value, problems = merge_three(base.get(key, MISSING), local.get(key, MISSING), remote.get(key, MISSING), (path + '.' if path else '') + key)
            if value is not MISSING:
                merged[key] = value
            conflicts += problems
        return merged, conflicts
    show = lambda value: {'missing': True} if value is MISSING else value
    return local, [{'path': path, 'base': show(base), 'local': show(local), 'remote': show(remote)}]


def import_changes(vault, data, apply=False):
    if data.get('schema_version') != 1:
        raise ValueError('不支持的修改包版本')
    identifier(data['bundle_id'])
    if not isinstance(data.get('changes'), list) or not isinstance(data.get('new_assets', []), list):
        raise ValueError('修改包 changes/new_assets 必须是列表')
    package_hash = digest(data)
    receipt_path = f'exchanges/receipts/{package_hash}.json'
    with locked(vault.root):
        if data['vault_id'] != vault._read('vault.json')['vault_id']:
            raise ValueError('工作包属于另一个资料库')
        if safe_path(vault.root, receipt_path).exists():
            return {'status': 'already-applied', 'package_hash': package_hash}
        base_bundle = vault._read(f"exchanges/outbox/{data['bundle_id']}.json")
        bases = {('asset', a['asset_id'], a['revision']): a for a in base_bundle['assets']}
        bases.update({('graph', g['graph_id'], g['revision']): g for g in base_bundle['graphs']})
        graphs = {g['graph_id']: g for g in all_graphs(vault)}
        writes, conflicts, changed, seen = {}, [], [], set()
        for change in data['changes']:
            kind, key = change['kind'], identifier(change['id'])
            if (kind, key) in seen:
                raise ValueError('同一对象在修改包中重复出现')
            seen.add((kind, key))
            base = bases.get((kind, key, change['base_revision']))
            if base is None or digest(base) != change.get('base_hash'):
                raise ValueError('修改基线不在原工作包内或哈希不符')
            patch = change.get('patch')
            allowed = ASSET_FIELDS if kind == 'asset' else GRAPH_FIELDS if kind == 'graph' else set()
            if not isinstance(patch, dict) or set(patch) - allowed:
                raise ValueError('修改包含不可编辑或未知字段')
            local = vault._get_asset(key) if kind == 'asset' else graphs[key]
            remote = {**base, **copy.deepcopy(patch)}
            merged, problems = merge_three(base, local, remote)
            if problems:
                conflicts += [{'kind': kind, 'id': key, **p} for p in problems]
                continue
            if kind == 'asset':
                record, updates = vault._asset_updates(merged, local['revision'])
            else:
                record, updates = graph_updates(vault, local['owner']['kind'], local['owner']['id'], merged, local['revision'])
            writes.update(updates)
            if updates:
                changed.append({'kind': kind, 'id': key, 'revision': record['revision']})
        new_ids = set()
        for entry in data.get('new_assets', []):
            local_id = identifier(entry['local_id'])
            if local_id in new_ids:
                raise ValueError('重复的新资产 local_id')
            new_ids.add(local_id)
            asset = copy.deepcopy(entry['data'])
            if 'asset_id' in asset or 'revision' in asset:
                raise ValueError('新卡片使用 local_id，不接受已有资产编号')
            if asset.get('asset_type') not in KINDS:
                raise ValueError('新卡片类型无效')
            aid = KINDS[asset['asset_type']][1] + '-' + uuid.uuid5(uuid.NAMESPACE_URL, data['vault_id'] + '/' + data['bundle_id'] + '/' + local_id).hex
            asset['asset_id'] = aid
            if safe_path(vault.root, vault._asset_path(aid)).exists():
                raise ValueError('该 local_id 已被其他回收包使用，请读取已创建的卡片再修改')
            record, updates = vault._asset_updates(asset, 0)
            writes.update(updates)
            changed.append({'kind': 'asset', 'id': aid, 'local_id': local_id, 'revision': 1})
        if conflicts:
            return {'status': 'conflict', 'conflicts': conflicts, 'applied': False}
        report = {'status': 'ready', 'package_hash': package_hash, 'changes': changed, 'applied': False}
        if apply:
            report.update(status='applied', applied=True)
            writes[receipt_path] = json_text({**report, 'bundle_id': data['bundle_id'], 'applied_at': now()})
            commit(vault.root, writes)
        return report


def record_space_sync(vault, data):
    require_text(data.get('page_id'), 'page_id', 500)
    if not re.fullmatch('[0-9a-f]{64}', data.get('page_hash', '')):
        raise ValueError('page_hash 必须是页面 Markdown 的 SHA-256')
    with locked(vault.root):
        if data['kind'] == 'asset':
            base = vault._get_asset(data['id'], data['revision'])
        elif data['kind'] == 'graph':
            base = next((g for g in all_graphs(vault) if g['graph_id'] == data['id']), None)
            if base is None or base['revision'] != data['revision']:
                base = vault._read(f"history/graphs/{identifier(data['id'])}/{int(data['revision'])}.json")
        else:
            raise ValueError('Space 目标类型无效')
        if digest(base) != data['base_hash']:
            raise ValueError('Space 同步基线哈希不符')
        record = {**copy.deepcopy(data), 'synced_at': now(), 'base_record': base}
        key = hashlib.sha256(data['page_id'].encode('utf-8')).hexdigest()
        commit(vault.root, {f'exchanges/space/{key}.json': json_text(record)})
        return record


def backup_allowed(name):
    parts = name.split('/')
    if name in {'vault.json', '.gitignore', 'README.md', 'AGENTS.md'}:
        return True
    if parts[0] not in {'library', 'books', 'history', 'exchanges'}:
        return False
    return not (name.startswith('library/views/') or any(p.startswith('.') for p in parts) or name.endswith('.local.json'))


def backup(vault, zip_path):
    zip_path = Path(zip_path).resolve()
    if zip_path.exists() or zip_path.is_relative_to(vault.root):
        raise ValueError('备份必须写入资料库外的新文件')
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with locked(vault.root):
        files = {}
        for path in sorted(vault.root.rglob('*')):
            name = path.relative_to(vault.root).as_posix()
            if backup_allowed(name) and path.is_file():
                files[name] = safe_path(vault.root, name).read_bytes()
        manifest = {'schema_version': 1, 'vault_id': vault._read('vault.json')['vault_id'], 'created_at': now(),
                    'excluded': ['private-sources', '.cache', '.git', 'library/views', 'machine configuration'],
                    'files': {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}
        fd, temp = tempfile.mkstemp(prefix='.backup-', dir=zip_path.parent)
        os.close(fd)
        try:
            with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, content in files.items():
                    archive.writestr(name, content)
                archive.writestr('MANIFEST.json', json_text(manifest))
            os.replace(temp, zip_path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    return {'path': str(zip_path), 'files': len(files), 'excluded': manifest['excluded']}


def restore(zip_path, destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('恢复目标必须是尚不存在的新目录')
    with zipfile.ZipFile(zip_path) as archive:
        items = archive.infolist()
        names = [i.filename for i in items]
        if len(items) > 10000 or len(set(names)) != len(names) or sum(i.file_size for i in items) > 200 * 1024 * 1024:
            raise ValueError('备份包含重复文件或超过恢复规模限制')
        if 'MANIFEST.json' not in names:
            raise ValueError('备份缺少完整性清单')
        for item in items:
            safe_path(destination, item.filename)
            if stat.S_ISLNK(item.external_attr >> 16) or (item.filename != 'MANIFEST.json' and not backup_allowed(item.filename)):
                raise ValueError('备份包含不允许的路径或链接')
        manifest = json.loads(archive.read('MANIFEST.json'))
        if manifest.get('schema_version') != 1 or set(manifest['files']) != set(names) - {'MANIFEST.json'}:
            raise ValueError('备份清单与文件列表不符')
        contents = {}
        for name, expected in manifest['files'].items():
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError('备份文件校验失败: ' + name)
            contents[name] = content
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.restore-', dir=destination.parent) as stage:
        staging = Path(stage).resolve()
        if not staging.is_relative_to(destination.parent.resolve()):
            raise ValueError('恢复临时目录越界')
        for name, content in contents.items():
            path = safe_path(staging, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        restored = Vault(staging)
        status = restored.validate()
        if manifest.get('vault_id') != restored.info()['vault_id']:
            raise ValueError('备份资料库身份不符')
        staging.rename(destination)
    return {'directory': str(destination), 'verified_files': len(contents), **status}
