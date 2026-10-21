#!/usr/bin/env python3
"""小说资料库命令入口：所有数据操作返回 JSON。"""

import argparse
import json
from pathlib import Path
import sys
import zipfile

from fictionlib.exchange import backup, export_bundle, import_changes, record_space_sync, restore
from fictionlib.graph import graph_path, render_graph, save_graph
from fictionlib.storage import locked, read_json
from fictionlib.vault import Vault


def parser():
    result = argparse.ArgumentParser(description='持久人物/剧情资料库；Python 3.10+，无第三方依赖')
    result.add_argument('--vault', help='个人资料库目录，放在工具代码仓库之外')
    commands = result.add_subparsers(dest='command', required=True)
    for name, help_text in [('init', '初始化空资料库'), ('status', '显示资料数量'), ('validate', '校验证据和引用'),
                            ('sources', '列出来源'), ('projects', '列出创作项目'), ('views', '重建 Markdown 阅读目录'),
                            ('space-list', '列出已登记的 Space 同步基线')]:
        commands.add_parser(name, help=help_text)
    for name in ['sources-import', 'checkpoint', 'usage-add', 'space-bind']:
        commands.add_parser(name).add_argument('--file', required=True)
    asset = commands.add_parser('asset-put', help='保存或更新卡片；已有卡片需要基线版本')
    asset.add_argument('--file', required=True)
    asset.add_argument('--base-revision', type=int)
    asset.add_argument('--generated', action='store_true', help='模型重蒸馏：保护人工笔记、收藏与审阅状态')
    show = commands.add_parser('asset-show')
    show.add_argument('--id', required=True)
    show.add_argument('--revision', type=int)
    search = commands.add_parser('search')
    search.add_argument('--query', default='')
    search.add_argument('--type', choices=['character', 'scene', 'pattern'])
    search.add_argument('--tag', action='append')
    search.add_argument('--favorite', action='store_true')
    search.add_argument('--scope', choices=['source-analysis', 'reusable-pattern', 'original-project'])
    search.add_argument('--source')
    search.add_argument('--project')
    commands.add_parser('project-create').add_argument('--title', required=True)
    use = commands.add_parser('project-use')
    use.add_argument('--project', required=True)
    use.add_argument('--asset', required=True)
    use.add_argument('--revision', type=int)
    for name in ['project-show', 'project-archive']:
        commands.add_parser(name).add_argument('--project', required=True)
    commands.add_parser('checkpoint-show').add_argument('--id', required=True)
    for name in ['graph-save', 'graph-show', 'graph-render']:
        command = commands.add_parser(name)
        command.add_argument('--owner-kind', choices=['project', 'source'], required=True)
        command.add_argument('--owner-id', required=True)
        if name == 'graph-save':
            command.add_argument('--file', required=True)
            command.add_argument('--base-revision', type=int)
        if name == 'graph-render':
            command.add_argument('--output', required=True)
    export = commands.add_parser('export')
    export.add_argument('--output', required=True)
    export.add_argument('--asset', action='append')
    export.add_argument('--project')
    export.add_argument('--max-chars', type=int, default=30000)
    importing = commands.add_parser('import')
    importing.add_argument('--file', required=True)
    importing.add_argument('--apply', action='store_true', help='无冲突时实际应用；默认仅预检')
    commands.add_parser('backup').add_argument('--output', required=True)
    restoring = commands.add_parser('restore')
    restoring.add_argument('--file', required=True)
    restoring.add_argument('--output', required=True)
    return result


def execute(args):
    command = args.command
    if command == 'restore':
        return restore(args.file, args.output)
    if not args.vault:
        raise ValueError('需要 --vault 指定个人资料库目录')
    if command == 'init':
        return Vault.init(args.vault).info()
    vault = Vault(args.vault)
    if command in {'status', 'validate'}:
        return {**vault.info(), **vault.validate()}
    if command == 'sources':
        return vault.sources()
    if command in {'projects', 'space-list'}:
        pattern = 'books/*/project.json' if command == 'projects' else 'exchanges/space/*.json'
        with locked(vault.root):
            return [record for _, record in vault._records(pattern)]
    if command == 'sources-import':
        return vault.import_sources(read_json(args.file))
    if command == 'asset-put':
        return vault.put_asset(read_json(args.file), args.base_revision, args.generated)
    if command == 'asset-show':
        return vault.get_asset(args.id, args.revision)
    if command == 'search':
        return vault.search(args.query, args.type, args.tag, args.favorite, args.scope, args.source, args.project)
    if command == 'project-create':
        return vault.create_project(args.title)
    if command == 'project-use':
        return vault.use_asset(args.project, args.asset, args.revision)
    if command == 'project-show':
        return vault.get_project(args.project)
    if command == 'project-archive':
        return vault.archive_project(args.project)
    if command == 'checkpoint':
        return vault.checkpoint(read_json(args.file))
    if command == 'checkpoint-show':
        return vault.get_checkpoint(args.id)
    if command == 'usage-add':
        data = read_json(args.file)
        return vault.record_usage(data['project_id'], data['asset_id'], data['revision'], data['adaptation'], data.get('feedback', ''), data.get('evidence_type', 'editorial-judgment'))
    if command == 'views':
        return vault.build_views()
    if command == 'graph-save':
        return save_graph(vault, args.owner_kind, args.owner_id, read_json(args.file), args.base_revision)
    if command in {'graph-show', 'graph-render'}:
        with locked(vault.root):
            graph = vault._read(graph_path(args.owner_kind, args.owner_id))
        return graph if command == 'graph-show' else render_graph(graph, args.output)
    if command == 'export':
        return export_bundle(vault, args.output, args.asset, args.project, args.max_chars)
    if command == 'import':
        return import_changes(vault, read_json(args.file), args.apply)
    if command == 'backup':
        return backup(vault, args.output)
    if command == 'space-bind':
        return record_space_sync(vault, read_json(args.file))
    raise ValueError('未知命令')


def main():
    args = parser().parse_args()
    try:
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 3 if isinstance(result, dict) and result.get('status') == 'conflict' else 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps({'error': str(exc), 'command': args.command}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
