"""来源、人物/场景资产、项目引用与分析检查点。"""

import copy
from datetime import datetime, timezone
from pathlib import Path
import re

from .storage import commit, digest, json_text, locked, new_id, read_json, safe_path

KINDS = {'character': ('characters', 'chr'), 'scene': ('scenes', 'scn'), 'pattern': ('patterns', 'pat')}
SCOPES = {'source-analysis', 'reusable-pattern', 'original-project'}
CLAIMS = {'fact', 'inference', 'synthesis', 'plan'}
OWNED = {'user_notes', 'favorite', 'review_status'}
SERVER_FIELDS = {'asset_id', 'schema_version', 'revision', 'created_at', 'updated_at'}
ASSET_FIELDS = {'asset_type', 'scope', 'title', 'tags', 'content', 'evidence', 'derived_from', 'origin_key', 'project_id'} | OWNED


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,99}', value):
        raise ValueError('非法 ID: ' + str(value))
    return value


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def require_text(value, name, limit=100000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(name + ' 必须是非空文本且不超过 ' + str(limit) + ' 字符')


class Vault:
    def __init__(self, path):
        self.root = Path(path).resolve()
        if not (self.root / 'vault.json').is_file():
            raise ValueError('未初始化的资料库: ' + str(self.root))
        with locked(self.root):
            info = self._read('vault.json')
            if info.get('schema_version') != 1 or not str(info.get('vault_id', '')).startswith('vault-'):
                raise ValueError('不支持的资料库 schema_version 或 vault_id')

    @classmethod
    def init(cls, path):
        root = Path(path).resolve()
        if (root / 'vault.json').exists():
            return cls(root)
        if root.exists() and any(root.iterdir()):
            raise ValueError('初始化目标必须为空目录，防止混入其他项目')
        with locked(root):
            commit(root, {
                'vault.json': json_text({'schema_version': 1, 'vault_id': new_id('vault'), 'created_at': now()}),
                '.gitignore': 'private-sources/\n.cache/\n.lock\n.journal.json\n.write-*\n*.local.json\n',
                'README.md': '# 我的小说资料库\n\n人物与剧情卡位于 library，原创作品位于 books。\n完整 JSON 为主档，library/views 为生成的阅读副本。\n原始小说放 private-sources，不随默认备份上传。\n',
            })
        return cls(root)

    def _read(self, relative):
        return read_json(safe_path(self.root, relative))

    def info(self):
        with locked(self.root):
            return self._read('vault.json')

    def _sources(self):
        return [read_json(p) for p in sorted((self.root / 'library' / 'sources').glob('*.json'))]

    def sources(self):
        with locked(self.root):
            return self._sources()

    def _source(self, source_id):
        identifier(source_id)
        matches = [s for s in self._sources() if source_id == s['source_id'] or source_id in s.get('aliases', [])]
        if len(matches) != 1:
            raise ValueError('来源缺失或别名冲突: ' + source_id)
        return matches[0]

    def import_sources(self, manifest):
        if manifest.get('schema_version') != 2:
            raise ValueError('请先通过 prepare_sources 迁移为 schema_version 2 的来源清单')
        with locked(self.root):
            changes = {}
            existing = {s['source_id']: s for s in self._sources()}
            for raw in manifest['sources']:
                sid = identifier(raw['source_id'])
                previous = existing.get(sid)
                revisions = {r['revision']: r for r in previous['revisions']} if previous else {}
                for revision in raw['revisions']:
                    sha = revision['revision']
                    if not re.fullmatch('[0-9a-f]{64}', sha):
                        raise ValueError('来源修订必须是 SHA-256')
                    # 不复制 normalized_path，工作包与主档均不泄漏机器路径。
                    clean = {k: copy.deepcopy(v) for k, v in revision.items() if k in {'revision', 'characters', 'line_count', 'chapters'}}
                    chapters = clean.get('chapters', [])
                    if not chapters or len({c['chapter_id'] for c in chapters}) != len(chapters):
                        raise ValueError('来源缺少有效章节索引')
                    for chapter in chapters:
                        identifier(chapter['chapter_id'])
                        if type(chapter.get('start_line')) is not int or type(chapter.get('end_line')) is not int or not 1 <= chapter['start_line'] <= chapter['end_line']:
                            raise ValueError('章节行号无效')
                    if sha in revisions and revisions[sha] != clean:
                        raise ValueError('同一来源修订的证据索引发生冲突')
                    revisions[sha] = clean
                if raw['revision'] not in revisions:
                    raise ValueError('当前来源修订未登记')
                aliases = sorted(set(raw.get('aliases', [])) | set(previous.get('aliases', []) if previous else []))
                for alias in aliases:
                    identifier(alias)
                record = {'source_id': sid, 'title': raw.get('title', raw.get('filename', sid)),
                          'aliases': aliases, 'revision': raw['revision'], 'revisions': list(revisions.values())}
                existing[sid] = record
                changes[f'library/sources/{sid}.json'] = json_text(record)
            seen = {}
            for sid, source in existing.items():
                for alias in [sid, *source['aliases']]:
                    if alias in seen and seen[alias] != sid:
                        raise ValueError('来源别名冲突: ' + alias)
                    seen[alias] = sid
            commit(self.root, changes)
            return {'sources': len(existing), 'updated': len(changes)}

    def validate_evidence(self, evidence):
        if not isinstance(evidence, list):
            raise ValueError('evidence 必须是列表')
        clean = copy.deepcopy(evidence)
        for entry in clean:
            source = self._source(entry['source_id'])
            entry['source_id'] = source['source_id']
            revision = next((r for r in source['revisions'] if r['revision'] == entry.get('revision')), None)
            if revision is None:
                raise ValueError('证据的来源修订未登记')
            if entry.get('claim_kind') not in CLAIMS:
                raise ValueError('证据必须区分 fact/inference/synthesis/plan')
            chapter = next((c for c in revision['chapters'] if c['chapter_id'] == entry.get('chapter_id')), None)
            if chapter is None:
                raise ValueError('证据章节未登记')
            if 'start_line' in entry or 'end_line' in entry:
                start, end = entry.get('start_line'), entry.get('end_line')
                if type(start) is not int or type(end) is not int or not chapter['start_line'] <= start <= end <= chapter['end_line']:
                    raise ValueError('证据行号越出章节范围')
        return clean

    def _asset_path(self, asset_id):
        identifier(asset_id)
        for folder, prefix in KINDS.values():
            if asset_id.startswith(prefix + '-'):
                return f'library/{folder}/{asset_id}.json'
        raise ValueError('未知资产 ID 类型: ' + asset_id)

    def _get_asset(self, asset_id, revision=None):
        path = self._asset_path(asset_id)
        current = self._read(path)
        if revision is None or current['revision'] == revision:
            return current
        if type(revision) is not int or revision < 1:
            raise ValueError('非法资产版本')
        return self._read(f'history/assets/{asset_id}/{revision}.json')

    def get_asset(self, asset_id, revision=None):
        with locked(self.root):
            return self._get_asset(asset_id, revision)

    def _assets(self):
        return [read_json(p) for folder, _ in KINDS.values() for p in sorted((self.root / 'library' / folder).glob('*.json'))]

    def _validate_asset(self, record):
        if record.get('asset_type') not in KINDS or record.get('scope') not in SCOPES:
            raise ValueError('资产类型或 scope 无效')
        require_text(record.get('title'), 'title', 500)
        if not isinstance(record.get('content'), dict):
            raise ValueError('content 必须是对象')
        require_text(record['content'].get('summary'), 'content.summary')
        if len(json_text(record)) > 1024 * 1024:
            raise ValueError('单张卡片超过 1 MiB，请拆分')
        if not isinstance(record.get('tags'), list) or len(record['tags']) > 100 or any(not isinstance(t, str) or not t.strip() or len(t) > 100 for t in record['tags']):
            raise ValueError('tags 必须是简短文本列表')
        if type(record.get('favorite')) is not bool or not isinstance(record.get('user_notes'), str):
            raise ValueError('favorite/user_notes 类型无效')
        if record.get('review_status') not in {'draft', 'selected', 'archived'}:
            raise ValueError('review_status 无效')
        if 'origin_key' in record:
            require_text(record['origin_key'], 'origin_key', 500)
        record['evidence'] = self.validate_evidence(record.get('evidence', []))
        if record['scope'] == 'source-analysis' and not record['evidence']:
            raise ValueError('来源研究卡必须有证据')
        if not isinstance(record.get('derived_from'), list):
            raise ValueError('derived_from 必须是列表')
        for ref in record['derived_from']:
            if ref['asset_id'] == record['asset_id']:
                raise ValueError('资产不能派生自自身')
            self._get_asset(ref['asset_id'], ref['revision'])
        if record['scope'] == 'original-project':
            self._project(record.get('project_id'))
        return record

    def _asset_updates(self, data, base_revision=None, generated=False):
        data = copy.deepcopy(data)
        if set(data) - ASSET_FIELDS - SERVER_FIELDS:
            raise ValueError('未知资产字段: ' + ', '.join(sorted(set(data) - ASSET_FIELDS - SERVER_FIELDS)))
        current = None
        if data.get('asset_id'):
            path = self._asset_path(data['asset_id'])
            if safe_path(self.root, path).exists():
                current = self._read(path)
        elif data.get('origin_key'):
            candidates = [a for a in self._assets() if a.get('origin_key') == data['origin_key']]
            if len(candidates) > 1:
                raise ValueError('origin_key 冲突')
            current = candidates[0] if candidates else None
        kind = data.get('asset_type', current['asset_type'] if current else None)
        if kind not in KINDS:
            raise ValueError('asset_type 必须是 character/scene/pattern')
        if current and kind != current['asset_type']:
            raise ValueError('不能更改已有资产类型')
        record = copy.deepcopy(current) if current else {
            'schema_version': 1, 'asset_id': data.get('asset_id') or new_id(KINDS[kind][1]),
            'asset_type': kind, 'tags': [], 'evidence': [], 'derived_from': [],
            'user_notes': '', 'favorite': False, 'review_status': 'draft', 'created_at': now()}
        for key, value in data.items():
            if key not in SERVER_FIELDS and not (generated and current and key in OWNED):
                record[key] = value
        if not record['asset_id'].startswith(KINDS[kind][1] + '-'):
            raise ValueError('资产 ID 与类型不匹配')
        self._validate_asset(record)
        comparable = lambda a: {k: v for k, v in a.items() if k not in SERVER_FIELDS}
        if current and comparable(current) == comparable(record):
            return current, {}
        if not current and not data.get('asset_id'):
            # 相同分析重跑不产生新卡，不把标题相同视为同一个人物。
            core = lambda a: {k: v for k, v in comparable(a).items() if k not in OWNED}
            identical = next((a for a in self._assets() if core(a) == core(record)), None)
            if identical:
                return identical, {}
        if current and (type(base_revision) is not int or current['revision'] != base_revision):
            raise ValueError('资产版本冲突；请读取当前版本后再修改')
        if not current and base_revision not in (None, 0):
            raise ValueError('新资产不能声称已有版本')
        record['revision'] = current['revision'] + 1 if current else 1
        record['updated_at'] = now()
        changes = {self._asset_path(record['asset_id']): json_text(record)}
        if current:
            changes[f"history/assets/{current['asset_id']}/{current['revision']}.json"] = json_text(current)
        return record, changes

    def put_asset(self, data, base_revision=None, generated=False):
        with locked(self.root):
            record, changes = self._asset_updates(data, base_revision, generated)
            commit(self.root, changes)
            return record

    def search(self, query='', asset_type=None, tags=None, favorite=False, scope=None, source_id=None, project_id=None):
        with locked(self.root):
            assets = self._assets()
            refs = {r['asset_id'] for r in self._project(project_id)['assets']} if project_id else None
            source_id = self._source(source_id)['source_id'] if source_id else None
            return [a for a in assets if
                    (not query or query.casefold() in json_text(a).casefold()) and
                    (not asset_type or a['asset_type'] == asset_type) and
                    (not tags or set(tags).issubset(a['tags'])) and
                    (not favorite or a['favorite']) and (not scope or a['scope'] == scope) and
                    (not source_id or any(e['source_id'] == source_id for e in a['evidence'])) and
                    (refs is None or a['asset_id'] in refs)]

    def _project(self, project_id):
        identifier(project_id)
        return self._read(f'books/{project_id}/project.json')

    def get_project(self, project_id):
        with locked(self.root):
            return self._project(project_id)

    def create_project(self, title):
        require_text(title, 'title', 500)
        record = {'schema_version': 1, 'project_id': new_id('proj'), 'title': title, 'status': 'active', 'assets': [], 'created_at': now()}
        with locked(self.root):
            commit(self.root, {f"books/{record['project_id']}/project.json": json_text(record)})
        return record

    def use_asset(self, project_id, asset_id, revision=None):
        with locked(self.root):
            project = self._project(project_id)
            asset = self._get_asset(asset_id, revision)
            ref = {'asset_id': asset_id, 'revision': asset['revision'], 'hash': digest(asset)}
            project['assets'] = [r for r in project['assets'] if r['asset_id'] != asset_id] + [ref]
            commit(self.root, {f'books/{project_id}/project.json': json_text(project)})
            return project

    def archive_project(self, project_id):
        with locked(self.root):
            project = self._project(project_id)
            project['status'] = 'archived'
            commit(self.root, {f'books/{project_id}/project.json': json_text(project)})
            return project

    def record_usage(self, project_id, asset_id, revision, adaptation, feedback='', evidence_type='editorial-judgment'):
        require_text(adaptation, 'adaptation')
        if evidence_type not in {'editorial-judgment', 'reader-observation', 'experiment'}:
            raise ValueError('反馈证据类型无效')
        with locked(self.root):
            self._project(project_id)
            self._get_asset(asset_id, revision)
            record = {'usage_id': new_id('use'), 'project_id': project_id, 'asset_id': asset_id, 'revision': revision,
                      'adaptation': adaptation, 'feedback': feedback, 'evidence_type': evidence_type, 'created_at': now()}
            commit(self.root, {f"books/{project_id}/usage/{record['usage_id']}.json": json_text(record)})
            return record

    def checkpoint(self, data):
        identifier(data['run_id'])
        with locked(self.root):
            source = self._source(data['source_id'])
            revision = next((r for r in source['revisions'] if r['revision'] == data['source_revision']), None)
            if revision is None:
                raise ValueError('检查点的来源修订不存在')
            completed, pending = data['completed_chapters'], data['pending_chapters']
            chapters = {c['chapter_id'] for c in revision['chapters']}
            if set(completed) & set(pending) or not set(completed + pending).issubset(chapters):
                raise ValueError('检查点章节范围无效')
            record = {**copy.deepcopy(data), 'source_id': source['source_id'], 'updated_at': now()}
            path = f"exchanges/runs/{data['run_id']}.json"
            if safe_path(self.root, path).exists():
                old = self._read(path)
                if (old['source_id'], old['source_revision']) != (record['source_id'], record['source_revision']):
                    raise ValueError('同一运行不能切换来源或修订')
            commit(self.root, {path: json_text(record)})
            return record

    def get_checkpoint(self, run_id):
        identifier(run_id)
        with locked(self.root):
            return self._read(f'exchanges/runs/{run_id}.json')

    def build_views(self):
        with locked(self.root):
            assets = self._assets()
            lines = ['# 人物与剧情资料目录', '', '> 自动生成的阅读副本。修改请通过主档或工作包回收。', '']
            changes = {}
            for asset in assets:
                aid = asset['asset_id']
                title = asset['title'].replace('\n', ' ').replace('[', '［').replace(']', '］')
                lines.append(f"- [{title}]({aid}.md) · {asset['asset_type']} · v{asset['revision']}")
                body = [f'# {title}', '', f"ID: `{aid}` · 版本: {asset['revision']} · 范围: {asset['scope']}", '',
                        asset['content']['summary'], '', '## 完整卡片', '', '```json', json_text(asset).replace('```', '\\u0060\\u0060\\u0060'), '```', '']
                changes[f'library/views/{aid}.md'] = '\n'.join(body)
            changes['library/views/index.md'] = '\n'.join(lines) + '\n'
            commit(self.root, changes)
            return {'assets': len(assets), 'index': str(self.root / 'library' / 'views' / 'index.md')}

    def validate(self):
        with locked(self.root):
            assets = self._assets()
            for asset in assets:
                self._validate_asset(copy.deepcopy(asset))
            projects = [read_json(p) for p in (self.root / 'books').glob('*/project.json')]
            for project in projects:
                for ref in project['assets']:
                    if digest(self._get_asset(ref['asset_id'], ref['revision'])) != ref['hash']:
                        raise ValueError('项目采用的资产哈希不符')
            return {'valid': True, 'assets': len(assets), 'sources': len(self._sources()), 'projects': len(projects)}
