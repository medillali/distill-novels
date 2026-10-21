import json
import subprocess
import sys
from support import VaultCase, ROOT
from test_graph import graph_sample


class CliTests(VaultCase):
    def cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'library.py'), '--vault', str(self.vault.root), *args], capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr.decode('utf-8', errors='replace'))
        return result

    def write(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return str(path)

    def test_cli_end_to_end(self):
        self.assertEqual(self.cli('status')['assets'], 0)
        card = self.cli('asset-put', '--file', self.write('card.json', self.card()))
        self.assertEqual(len(self.cli('search', '--query', '旧信')), 1)
        project = self.cli('project-create', '--title', '新项目')
        self.cli('project-use', '--project', project['project_id'], '--asset', card['asset_id'])
        graph = self.cli('graph-save', '--owner-kind', 'project', '--owner-id', project['project_id'], '--file', self.write('graph.json', graph_sample()))
        self.cli('graph-render', '--owner-kind', 'project', '--owner-id', project['project_id'], '--output', str(self.root / 'view'))
        self.assertTrue((self.root / 'view' / 'index.html').exists())
        exported = self.cli('export', '--project', project['project_id'], '--output', str(self.root / 'exchange'))
        template = json.loads((self.root / 'exchange' / 'changes-template.json').read_text(encoding='utf-8'))
        template['changes'][0]['patch'] = {'user_notes': '云端反馈'}
        self.cli('import', '--file', self.write('changes.json', template), '--apply')
        self.assertEqual(self.cli('asset-show', '--id', card['asset_id'])['user_notes'], '云端反馈')
        self.cli('views')
        archive = self.root / 'backup.zip'
        self.cli('backup', '--output', str(archive))
        restored = self.cli('restore', '--file', str(archive), '--output', str(self.root / 'restored'))
        self.assertTrue(restored['valid'])
        self.assertEqual(self.cli('validate')['assets'], 1)

    def test_errors_are_actionable_and_nonzero(self):
        self.cli('asset-show', '--id', '../bad', success=False)
        self.cli('asset-put', '--file', self.write('bad.json', {'title': '缺字段'}), success=False)

    def test_demo_runs_in_new_directory(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'demo.py'), '--output', str(self.root / 'demo')], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        data = json.loads(result.stdout)
        self.assertTrue((self.root / 'demo' / 'views' / 'index.html').exists())
        self.assertGreaterEqual(data['assets'], 3)
