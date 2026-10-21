import copy
import json
from unittest.mock import patch

from support import VaultCase
from fictionlib.storage import commit, json_text, locked, read_json
from fictionlib.vault import Vault


class VaultTests(VaultCase):
    def test_create_search_and_reopen_preserve_assets(self):
        asset = self.vault.put_asset(self.card(favorite=True, user_notes='保留这个矛盾'))
        reopened = Vault(self.vault.root)
        self.assertEqual(reopened.get_asset(asset['asset_id'])['user_notes'], '保留这个矛盾')
        self.assertEqual(len(reopened.search(query='旧信', tags=['秘密'], favorite=True)), 1)
        self.assertEqual(reopened.search(query='不存在'), [])

    def test_repeat_extraction_deduplicates_and_preserves_notes(self):
        original = self.card(origin_key='src-sample/character/keeper')
        asset = self.vault.put_asset(original)
        edited = self.vault.put_asset({'asset_id': asset['asset_id'], 'user_notes': '人工笔记', 'favorite': True}, base_revision=1)
        repeated = self.vault.put_asset(original, generated=True)
        self.assertEqual(repeated['asset_id'], asset['asset_id'])
        self.assertEqual(repeated['revision'], edited['revision'])
        self.assertEqual(repeated['user_notes'], '人工笔记')
        self.assertEqual(len(self.vault.search()), 1)

    def test_generated_update_cannot_erase_owned_fields(self):
        asset = self.vault.put_asset(self.card(user_notes='不能删', favorite=True, review_status='selected'))
        updated = self.vault.put_asset({'asset_id': asset['asset_id'], 'content': {'summary': '补充观察'},
                                       'user_notes': '', 'favorite': False, 'review_status': 'draft'}, base_revision=1, generated=True)
        self.assertEqual(updated['user_notes'], '不能删')
        self.assertTrue(updated['favorite'])
        self.assertEqual(updated['review_status'], 'selected')
        self.assertEqual(self.vault.get_asset(asset['asset_id'], 1)['content']['goal'], '守住灯塔')

    def test_stale_update_is_rejected(self):
        asset = self.vault.put_asset(self.card())
        self.vault.put_asset({'asset_id': asset['asset_id'], 'title': '新标题'}, base_revision=1)
        with self.assertRaisesRegex(ValueError, '版本'):
            self.vault.put_asset({'asset_id': asset['asset_id'], 'title': '旧会话覆盖'}, base_revision=1)
        self.assertEqual(self.vault.get_asset(asset['asset_id'])['title'], '新标题')

    def test_evidence_requires_known_source_revision_and_chapter(self):
        for key, value in [('source_id', 'src-missing'), ('revision', 'b' * 64), ('chapter_id', 'ch-9999')]:
            card = self.card()
            card['evidence'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.vault.put_asset(card)
        with self.assertRaises(ValueError):
            self.vault.put_asset(self.card(evidence=[]))

    def test_legacy_alias_resolves_without_same_name_merge(self):
        second = copy.deepcopy(self.source)
        second.update(source_id='src-other', aliases=[])
        second['revision'] = 'b' * 64
        second['revisions'][0]['revision'] = 'b' * 64
        self.vault.import_sources({'schema_version': 2, 'sources': [second]})
        data = self.card()
        data['evidence'][0]['source_id'] = 'book-01-old'
        asset = self.vault.put_asset(data)
        self.assertEqual(asset['evidence'][0]['source_id'], 'src-sample')
        self.assertEqual(len(self.vault.sources()), 2)

    def test_two_projects_pin_independent_versions_and_archive_keeps_library(self):
        card = self.vault.put_asset(self.card())
        a = self.vault.create_project('项目甲')
        b = self.vault.create_project('项目乙')
        self.vault.use_asset(a['project_id'], card['asset_id'])
        self.vault.put_asset({'asset_id': card['asset_id'], 'title': '修订'}, base_revision=1)
        self.vault.use_asset(b['project_id'], card['asset_id'])
        self.assertEqual(self.vault.get_project(a['project_id'])['assets'][0]['revision'], 1)
        self.assertEqual(self.vault.get_project(b['project_id'])['assets'][0]['revision'], 2)
        self.vault.archive_project(a['project_id'])
        self.assertEqual(len(self.vault.search()), 1)
        self.assertEqual(len(self.vault.search(project_id=b['project_id'])), 1)

    def test_usage_and_original_instance_keep_derivation(self):
        card = self.vault.put_asset(self.card())
        project = self.vault.create_project('新故事')
        instance = self.vault.put_asset(self.card(scope='original-project', project_id=project['project_id'],
                                        title='新人物', evidence=[], derived_from=[{'asset_id': card['asset_id'], 'revision': 1}]))
        usage = self.vault.record_usage(project['project_id'], card['asset_id'], 1, '改为车站管理员', '需要更强的动机')
        self.assertEqual(instance['derived_from'][0]['revision'], 1)
        self.assertEqual(usage['asset_id'], card['asset_id'])
        self.assertEqual(self.vault.get_asset(card['asset_id'])['title'], '守灯人')

    def test_write_failure_rolls_back_all_records(self):
        import fictionlib.storage as storage
        before = (self.vault.root / 'vault.json').read_bytes()
        real_write = storage.atomic_write
        def failing(path, text):
            if str(path).endswith('fail.json'):
                raise OSError('模拟断电前写失败')
            real_write(path, text)
        with locked(self.vault.root):
            with patch.object(storage, 'atomic_write', side_effect=failing), self.assertRaises(OSError):
                commit(self.vault.root, {'vault.json': '{}', 'fail.json': '{}'})
        self.assertEqual((self.vault.root / 'vault.json').read_bytes(), before)
        self.assertFalse((self.vault.root / '.journal.json').exists())

    def test_reopen_recovers_interrupted_transaction(self):
        original = (self.vault.root / 'vault.json').read_text(encoding='utf-8')
        (self.vault.root / '.journal.json').write_text(json_text({'before': {'vault.json': original, 'partial.json': None}}), encoding='utf-8')
        (self.vault.root / 'vault.json').write_text('{}', encoding='utf-8')
        (self.vault.root / 'partial.json').write_text('{}', encoding='utf-8')
        recovered = Vault(self.vault.root)
        self.assertEqual(recovered.info()['schema_version'], 1)
        self.assertFalse((self.vault.root / 'partial.json').exists())

    def test_paths_and_unknown_schema_are_rejected(self):
        with self.assertRaises(ValueError):
            self.vault.get_asset('../vault')
        info = self.vault.info()
        info['schema_version'] = 999
        (self.vault.root / 'vault.json').write_text(json_text(info), encoding='utf-8')
        with self.assertRaises(ValueError):
            Vault(self.vault.root)

    def test_checkpoint_resume_and_catalog(self):
        run = self.vault.checkpoint({'run_id': 'run-demo', 'source_id': 'src-sample', 'source_revision': 'a' * 64,
                                     'completed_chapters': ['ch-0001'], 'pending_chapters': [], 'notes': '分析待复核'})
        self.assertEqual(self.vault.get_checkpoint('run-demo')['completed_chapters'], ['ch-0001'])
        self.vault.put_asset(self.card())
        result = self.vault.build_views()
        self.assertEqual(result['assets'], 1)
        self.assertIn('守灯人', (self.vault.root / 'library' / 'views' / 'index.md').read_text(encoding='utf-8'))
