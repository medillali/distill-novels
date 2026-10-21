import copy
import hashlib
import json
import zipfile

from support import VaultCase
from fictionlib.exchange import export_bundle, import_changes, backup, restore, record_space_sync
from fictionlib.storage import digest, read_json
from fictionlib.vault import Vault
from fictionlib.graph import save_graph
from test_graph import graph_sample


class ExchangeTests(VaultCase):
    def setUp(self):
        super().setUp()
        self.asset = self.vault.put_asset(self.card())
        self.export = self.root / 'out'
        self.bundle = export_bundle(self.vault, self.export)

    def changes(self, patch):
        return {'schema_version': 1, 'vault_id': self.bundle['vault_id'], 'bundle_id': self.bundle['bundle_id'],
                'changes': [{'kind': 'asset', 'id': self.asset['asset_id'], 'base_revision': 1,
                             'base_hash': digest(self.asset), 'patch': patch}], 'new_assets': []}

    def test_roundtrip_dry_run_then_apply_and_repeat(self):
        changes = self.changes({'user_notes': 'ChatGPT 中的想法'})
        self.assertEqual(import_changes(self.vault, changes)['status'], 'ready')
        self.assertEqual(self.vault.get_asset(self.asset['asset_id'])['revision'], 1)
        self.assertEqual(import_changes(self.vault, changes, apply=True)['status'], 'applied')
        self.assertEqual(import_changes(self.vault, changes, apply=True)['status'], 'already-applied')
        self.assertEqual(self.vault.get_asset(self.asset['asset_id'])['revision'], 2)

    def test_same_field_conflict_leaves_all_assets_untouched(self):
        self.vault.put_asset({'asset_id': self.asset['asset_id'], 'title': '本地标题'}, base_revision=1)
        before = self.vault.get_asset(self.asset['asset_id'])
        report = import_changes(self.vault, self.changes({'title': '云端标题', 'user_notes': '不能部分写入'}), apply=True)
        self.assertEqual(report['status'], 'conflict')
        self.assertEqual(report['conflicts'][0]['path'], 'title')
        self.assertEqual(self.vault.get_asset(self.asset['asset_id']), before)

    def test_different_nested_fields_merge(self):
        self.vault.put_asset({'asset_id': self.asset['asset_id'], 'content': {'summary': '本地新概述', 'goal': '守住灯塔'}}, base_revision=1)
        result = import_changes(self.vault, self.changes({'content': {'summary': '守灯人隐瞒了旧信的来处。', 'goal': '寻找失踪的人'}}), apply=True)
        self.assertEqual(result['status'], 'applied')
        content = self.vault.get_asset(self.asset['asset_id'])['content']
        self.assertEqual(content, {'summary': '本地新概述', 'goal': '寻找失踪的人'})

    def test_forged_base_or_protected_field_rejected(self):
        forged = self.changes({'title': '更改'})
        forged['changes'][0]['base_hash'] = '0' * 64
        with self.assertRaises(ValueError):
            import_changes(self.vault, forged, apply=True)
        with self.assertRaises(ValueError):
            import_changes(self.vault, self.changes({'revision': 999}), apply=True)
        self.assertEqual(self.vault.get_asset(self.asset['asset_id'])['revision'], 1)

    def test_new_assets_idempotent_and_invalid_batch_atomic(self):
        changes = self.changes({'title': '旧卡变化'})
        changes['new_assets'] = [{'local_id': 'new-one', 'data': self.card(asset_type='scene', title='新场景', content={'summary': '雨夜交接信件'})}]
        report = import_changes(self.vault, changes, apply=True)
        self.assertEqual(report['status'], 'applied')
        self.assertEqual(len(self.vault.search()), 2)
        self.assertEqual(import_changes(self.vault, changes, apply=True)['status'], 'already-applied')
        invalid = self.changes({'title': '不应应用'})
        invalid['new_assets'] = [{'local_id': 'bad', 'data': self.card(title='')}]
        before = self.vault.get_asset(self.asset['asset_id'])
        with self.assertRaises(ValueError):
            import_changes(self.vault, invalid, apply=True)
        self.assertEqual(self.vault.get_asset(self.asset['asset_id']), before)

    def test_project_export_uses_pinned_revision_and_graph(self):
        project = self.vault.create_project('项目')
        self.vault.use_asset(project['project_id'], self.asset['asset_id'])
        self.vault.put_asset({'asset_id': self.asset['asset_id'], 'title': '更新后'}, base_revision=1)
        graph = save_graph(self.vault, 'project', project['project_id'], graph_sample())
        bundle = export_bundle(self.vault, self.root / 'project-export', project_id=project['project_id'])
        self.assertEqual(bundle['assets'][0]['revision'], 1)
        self.assertEqual(bundle['graphs'][0]['graph_id'], graph['graph_id'])
        self.assertTrue((self.root / 'project-export' / 'context.md').exists())

    def test_graph_roundtrip(self):
        project = self.vault.create_project('项目')
        graph = save_graph(self.vault, 'project', project['project_id'], graph_sample())
        bundle = export_bundle(self.vault, self.root / 'graph-export', project_id=project['project_id'])
        changes = {'schema_version': 1, 'vault_id': bundle['vault_id'], 'bundle_id': bundle['bundle_id'], 'new_assets': [],
                   'changes': [{'kind': 'graph', 'id': graph['graph_id'], 'base_revision': 1, 'base_hash': digest(graph), 'patch': {'title': '新结构名'}}]}
        self.assertEqual(import_changes(self.vault, changes, apply=True)['status'], 'applied')
        current = read_json(self.vault.root / 'books' / project['project_id'] / 'outline' / 'plot-graph.json')
        self.assertEqual(current['title'], '新结构名')

    def test_export_does_not_leak_machine_path_or_raw_sources(self):
        serialized = json.dumps(self.bundle, ensure_ascii=False)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn('normalized_path', serialized)
        manifest = read_json(self.export / 'manifest.json')
        self.assertIn('bundle.json', manifest['files'])

    def test_backup_restore_in_empty_directory_and_validate_history(self):
        self.vault.put_asset({'asset_id': self.asset['asset_id'], 'user_notes': '保留历史'}, base_revision=1)
        private = self.vault.root / 'private-sources'
        private.mkdir()
        (private / 'novel.txt').write_text('原文不进入备份', encoding='utf-8')
        archive = self.root / 'backup.zip'
        backup(self.vault, archive)
        restored = restore(archive, self.root / 'restored')
        restored_vault = Vault(restored['directory'])
        self.assertEqual(restored_vault.get_asset(self.asset['asset_id']), self.vault.get_asset(self.asset['asset_id']))
        self.assertEqual(restored_vault.get_asset(self.asset['asset_id'], 1), self.asset)
        self.assertFalse((restored_vault.root / 'private-sources').exists())
        self.assertTrue(restored_vault.validate()['valid'])

    def test_restore_rejects_existing_data_bad_hash_and_path_traversal(self):
        archive = self.root / 'backup.zip'
        backup(self.vault, archive)
        with self.assertRaises(ValueError):
            restore(archive, self.vault.root)
        malicious = self.root / 'malicious.zip'
        with zipfile.ZipFile(malicious, 'w') as z:
            z.writestr('../outside.txt', 'escape')
            z.writestr('MANIFEST.json', json.dumps({'schema_version': 1, 'files': {'../outside.txt': 'x'}}))
        with self.assertRaises(ValueError):
            restore(malicious, self.root / 'failed')
        self.assertFalse((self.root / 'outside.txt').exists())
        broken = self.root / 'broken.zip'
        with zipfile.ZipFile(broken, 'w') as z:
            z.writestr('vault.json', '{}')
            z.writestr('MANIFEST.json', json.dumps({'schema_version': 1, 'files': {'vault.json': '0' * 64}}))
        with self.assertRaises(ValueError):
            restore(broken, self.root / 'failed2')
        self.assertFalse((self.root / 'failed2').exists())

    def test_space_sync_records_exact_base(self):
        binding = record_space_sync(self.vault, {'page_id': 'page/example', 'kind': 'asset', 'id': self.asset['asset_id'],
                                               'revision': 1, 'base_hash': digest(self.asset), 'page_hash': 'b' * 64, 'cursor': 8})
        self.assertEqual(binding['revision'], 1)
        self.assertEqual(binding['cursor'], 8)
        with self.assertRaises(ValueError):
            record_space_sync(self.vault, {**binding, 'base_hash': '0' * 64})

    def test_card_only_export_excludes_unrelated_project_graphs(self):
        project = self.vault.create_project('不应分享的作品')
        secret = self.vault.put_asset(self.card(title='另一个项目的秘密人物'))
        graph = graph_sample()
        graph['nodes'][3]['characters'] = [secret['asset_id']]
        save_graph(self.vault, 'project', project['project_id'], graph)
        bundle = export_bundle(self.vault, self.root / 'selected', asset_ids=[self.asset['asset_id']])
        self.assertEqual(bundle['graphs'], [])
        self.assertEqual([a['asset_id'] for a in bundle['assets']], [self.asset['asset_id']])

    def test_current_and_historical_dependency_have_one_editable_baseline(self):
        self.vault.put_asset({'asset_id': self.asset['asset_id'], 'title': '第二版'}, base_revision=1)
        self.vault.put_asset(self.card(asset_type='pattern', scope='reusable-pattern', title='机制',
                                     derived_from=[{'asset_id': self.asset['asset_id'], 'revision': 1}]))
        target = self.root / 'versions'
        bundle = export_bundle(self.vault, target)
        self.assertEqual(sorted(a['revision'] for a in bundle['assets'] if a['asset_id'] == self.asset['asset_id']), [1, 2])
        template = read_json(target / 'changes-template.json')
        edits = [c for c in template['changes'] if c['id'] == self.asset['asset_id']]
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]['base_revision'], 2)
        self.assertEqual(import_changes(self.vault, template, apply=True)['status'], 'applied')
        template['changes'] = [{'kind': 'asset', 'id': self.asset['asset_id'], 'base_revision': 1,
                                'base_hash': digest(self.asset), 'patch': {'title': '改只读历史'}}]
        with self.assertRaises(ValueError):
            import_changes(self.vault, template, apply=True)

    def test_restore_rejects_graph_corruption_even_with_matching_archive_hash(self):
        project = self.vault.create_project('项目')
        graph = save_graph(self.vault, 'project', project['project_id'], graph_sample())
        valid_archive = self.root / 'valid-graph.zip'
        backup(self.vault, valid_archive)
        graph_path = f"books/{project['project_id']}/outline/plot-graph.json"
        graph['edges'][0]['to'] = 'missing'
        with zipfile.ZipFile(valid_archive) as z:
            contents = {name: z.read(name) for name in z.namelist()}
        contents[graph_path] = json.dumps(graph).encode('utf-8')
        manifest = json.loads(contents['MANIFEST.json'])
        manifest['files'][graph_path] = hashlib.sha256(contents[graph_path]).hexdigest()
        contents['MANIFEST.json'] = json.dumps(manifest).encode('utf-8')
        broken = self.root / 'corrupt-graph.zip'
        with zipfile.ZipFile(broken, 'w') as z:
            for name, content in contents.items():
                z.writestr(name, content)
        with self.assertRaises(ValueError):
            restore(broken, self.root / 'bad-restore')
        self.assertFalse((self.root / 'bad-restore').exists())
