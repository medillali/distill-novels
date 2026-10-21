import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from fictionlib.vault import Vault


class VaultCase(unittest.TestCase):
    def setUp(self):
        parent = ROOT / 'work' / 'tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(parent.resolve()))
        self.addCleanup(self.temp.cleanup)
        self.vault = Vault.init(self.root / 'vault')
        self.source = {'source_id': 'src-sample', 'title': '原创测试来源', 'aliases': ['book-01-old'],
                       'revision': 'a' * 64, 'revisions': [{'revision': 'a' * 64, 'line_count': 10,
                        'chapters': [{'chapter_id': 'ch-0001', 'title': '第一章', 'start_line': 1, 'end_line': 10}]}]}
        self.vault.import_sources({'schema_version': 2, 'sources': [self.source]})

    def card(self, **extra):
        data = {'asset_type': 'character', 'scope': 'source-analysis', 'title': '守灯人',
                'tags': ['秘密', '守护'], 'content': {'summary': '守灯人隐瞒了旧信的来处。', 'goal': '守住灯塔'},
                'evidence': [{'source_id': 'src-sample', 'revision': 'a' * 64, 'chapter_id': 'ch-0001', 'claim_kind': 'fact'}]}
        data.update(copy.deepcopy(extra))
        return data
