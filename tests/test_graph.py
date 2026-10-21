import copy
import json
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

from support import VaultCase
from fictionlib.graph import save_graph, validate_graph, render_graph
from fictionlib.render import positions


def graph_sample():
    return {'title': '灯塔的旧信', 'coverage': [],
            'nodes': [
                {'id': 'root', 'title': '故事', 'kind': 'story', 'parent_id': None, 'claim_kind': 'plan'},
                {'id': 'act1', 'title': '第一段', 'kind': 'arc', 'parent_id': 'root', 'claim_kind': 'plan'},
                {'id': 'act2', 'title': '第二段', 'kind': 'arc', 'parent_id': 'root', 'claim_kind': 'plan'},
                {'id': 'letter', 'title': '发现旧信', 'kind': 'scene', 'parent_id': 'act1', 'narrative_order': 1, 'claim_kind': 'plan', 'summary': '信封有两次封口的痕迹。'},
                {'id': 'refusal', 'title': '盟友拒绝解释', 'kind': 'scene', 'parent_id': 'act2', 'narrative_order': 2, 'claim_kind': 'plan'},
                {'id': 'reveal', 'title': '公开真相', 'kind': 'scene', 'parent_id': 'act2', 'narrative_order': 3, 'story_time': '十年前的倒叙', 'claim_kind': 'plan'}],
            'edges': [
                {'id': 'e1', 'from': 'letter', 'to': 'refusal', 'kind': 'setup', 'label': '信件暗线', 'claim_kind': 'plan'},
                {'id': 'e2', 'from': 'refusal', 'to': 'reveal', 'kind': 'payoff', 'label': '身份揭示', 'claim_kind': 'plan'}],
            'threads': [{'id': 'secret', 'title': '寄信人身份', 'kind': 'hidden', 'status': 'resolved',
                         'node_ids': ['letter', 'refusal', 'reveal'], 'edge_ids': ['e1', 'e2']}]}


class GraphTests(VaultCase):
    def setUp(self):
        super().setUp()
        self.project = self.vault.create_project('灯塔')

    def test_save_versions_and_preserve_nonchronological_time(self):
        first = save_graph(self.vault, 'project', self.project['project_id'], graph_sample())
        modified = graph_sample()
        modified['title'] = '修订结构'
        second = save_graph(self.vault, 'project', self.project['project_id'], modified, base_revision=1)
        self.assertEqual(second['graph_id'], first['graph_id'])
        self.assertEqual(second['revision'], 2)
        self.assertEqual(second['nodes'][-1]['story_time'], '十年前的倒叙')
        with self.assertRaisesRegex(ValueError, '版本'):
            save_graph(self.vault, 'project', self.project['project_id'], graph_sample(), base_revision=1)

    def test_tree_cycle_and_dangling_edges_rejected(self):
        cycle = graph_sample()
        cycle['nodes'][1]['parent_id'] = 'letter'
        with self.assertRaises(ValueError):
            validate_graph(cycle)
        dangling = graph_sample()
        dangling['edges'][0]['to'] = 'missing'
        with self.assertRaises(ValueError):
            validate_graph(dangling)

    def test_duplicate_nodes_and_thread_members_are_rejected(self):
        data = graph_sample()
        data['nodes'].append(copy.deepcopy(data['nodes'][1]))
        with self.assertRaises(ValueError):
            validate_graph(data)
        data = graph_sample()
        data['threads'][0]['edge_ids'].append('missing')
        with self.assertRaises(ValueError):
            validate_graph(data)

    def test_source_graph_needs_evidence_and_valid_coverage(self):
        data = graph_sample()
        data['coverage'] = [{'source_id': 'src-sample', 'revision': 'a' * 64, 'chapter_ids': ['ch-0001'], 'complete': False}]
        with self.assertRaises(ValueError):
            save_graph(self.vault, 'source', 'src-sample', data)
        evidence = [{'source_id': 'src-sample', 'revision': 'a' * 64, 'chapter_id': 'ch-0001', 'claim_kind': 'inference'}]
        for item in data['nodes'] + data['edges']:
            item['claim_kind'] = 'inference'
            item['evidence'] = evidence
        data['threads'][0]['status'] = 'unknown'
        result = save_graph(self.vault, 'source', 'src-sample', data)
        self.assertEqual(result['threads'][0]['status'], 'unknown')
        data['coverage'][0]['chapter_ids'] = ['ch-404']
        with self.assertRaises(ValueError):
            save_graph(self.vault, 'source', 'src-sample', data, base_revision=1)

    def test_thread_cannot_claim_payoff_without_resolution_basis(self):
        data = graph_sample()
        data['edges'][1]['kind'] = 'echo'
        with self.assertRaises(ValueError):
            validate_graph(data)
        data['threads'][0]['resolution_note'] = '主题意象在结尾形成完整呼应'
        self.assertTrue(validate_graph(data))

    def test_reader_and_character_knowledge_remain_distinct(self):
        character = self.vault.put_asset(self.card())
        data = graph_sample()
        data['nodes'][3]['knowledge'] = [{'observer': 'reader', 'state': 'suspects', 'belief': '信被修改'},
                                       {'observer': character['asset_id'], 'state': 'misbelieves', 'belief': '信是真的'}]
        stored = save_graph(self.vault, 'project', self.project['project_id'], data)
        self.assertNotEqual(stored['nodes'][3]['knowledge'][0]['state'], stored['nodes'][3]['knowledge'][1]['state'])

    def test_render_is_offline_and_escapes_untrusted_labels(self):
        data = graph_sample()
        data['nodes'][3]['title'] = '<script>alert(1)</script> & "旧信"'
        saved = save_graph(self.vault, 'project', self.project['project_id'], data)
        result = render_graph(saved, self.root / 'view')
        html = (self.root / 'view' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('src="http', html)
        self.assertIn('plot-network.svg', result['files'])
        svg = ET.parse(self.root / 'view' / 'plot-tree.svg')
        self.assertIn('<script>alert(1)</script>', ''.join(svg.getroot().itertext()))

    def test_template_tokens_in_labels_cannot_create_html_attributes(self):
        data = graph_sample()
        data['nodes'][0]['title'] = '@@DATA@@'
        data['nodes'][1]['title'] = ' onmouseover=alert(1) '
        render_graph(data, self.root / 'tokens')
        class Inspector(HTMLParser):
            def __init__(self):
                super().__init__()
                self.handlers = []
            def handle_starttag(self, tag, attrs):
                self.handlers.extend((tag, name) for name, _ in attrs if name.lower().startswith('on'))
        inspector = Inspector()
        inspector.feed((self.root / 'tokens' / 'index.html').read_text(encoding='utf-8'))
        self.assertEqual(inspector.handlers, [])

    def test_validate_rejects_graph_owner_mismatch_and_invalid_history(self):
        original = save_graph(self.vault, 'project', self.project['project_id'], graph_sample())
        path = self.vault.root / 'books' / self.project['project_id'] / 'outline' / 'plot-graph.json'
        other = self.vault.create_project('其他作品')
        mismatched = copy.deepcopy(original)
        mismatched['owner']['id'] = other['project_id']
        path.write_text(json.dumps(mismatched), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.vault.validate()
        path.write_text(json.dumps(original), encoding='utf-8')
        modified = graph_sample()
        modified['title'] = '第二版'
        save_graph(self.vault, 'project', self.project['project_id'], modified, base_revision=1)
        original['edges'][0]['to'] = 'missing'
        history = self.vault.root / 'history' / 'graphs' / original['graph_id'] / '1.json'
        history.write_text(json.dumps(original), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.vault.validate()

    def test_network_nodes_do_not_overlap(self):
        data = graph_sample()
        pos, _, _ = positions(data, network=True)
        points = list(pos.items())
        for i, (left_id, (lx, ly)) in enumerate(points):
            for right_id, (rx, ry) in points[i + 1:]:
                self.assertTrue(abs(lx - rx) >= 208 or abs(ly - ry) >= 64, f'{left_id} overlaps {right_id}')
