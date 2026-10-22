"""为浏览器可读性回归生成独立大图，不接触用户资料库。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fictionlib.render import render


def large_graph():
    nodes = [{'id': 'root', 'title': '长篇测试作品', 'kind': 'story',
              'parent_id': None, 'claim_kind': 'plan'}]
    for volume in range(1, 19):
        parent = f'vol-{volume:02}'
        nodes.append({'id': parent, 'title': f'第{volume}集', 'kind': 'volume',
                      'parent_id': 'root', 'claim_kind': 'plan'})
        for event in range(1, 11 if volume == 18 else 10):
            nodes.append({'id': f'{parent}-e{event}', 'title': f'第{volume}集事件{event}的可读标题',
                          'kind': 'event', 'parent_id': parent, 'claim_kind': 'plan',
                          'narrative_order': volume * 100 + event, 'summary': '独立测试节点。'})
    members = ['vol-01-e1', 'vol-09-e1', 'vol-18-e1']
    return {'title': '182节点可读性回归', 'nodes': nodes,
            'edges': [{'id': f'cross-{i}', 'from': a, 'to': b, 'kind': 'payoff',
                       'label': '跨阶段回收', 'claim_kind': 'plan'}
                      for i, (a, b) in enumerate(zip(members, members[1:]))],
            'threads': [{'id': 'narrow', 'title': '三个相隔阶段的事件', 'kind': 'hidden',
                         'status': 'resolved', 'node_ids': members,
                         'edge_ids': ['cross-0', 'cross-1'], 'resolution_note': '测试已回收。'}]}


if __name__ == '__main__':
    render(large_graph(), Path(sys.argv[1]))
