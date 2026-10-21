"""生成无外部依赖的 SVG、Mermaid 与 HTML 阅读视图。"""

import html
import json
import math
from pathlib import Path

from .storage import atomic_write

COLORS = ['#945f26', '#627745', '#805d83', '#407e8a', '#b45b4a', '#5763a2']


def positions(graph, network=False):
    nodes = graph['nodes']
    lookup = {n['id']: n for n in nodes}
    if network:
        leaves = [n for n in nodes if n['kind'] in {'scene', 'event'}]
        radius = max(260, len(leaves) * 42)
        center = radius + 220
        pos = {n['id']: (center + radius * math.cos(2 * math.pi * i / max(1, len(leaves))),
                         center + radius * math.sin(2 * math.pi * i / max(1, len(leaves)))) for i, n in enumerate(leaves)}
        for i, node in enumerate(n for n in nodes if n not in leaves):
            pos[node['id']] = (center, 90 + i * 90)
        return pos, center * 2, center * 2
    levels = {}
    for node in nodes:
        depth, parent = 0, node.get('parent_id')
        while parent is not None:
            depth += 1
            parent = lookup[parent].get('parent_id')
        levels.setdefault(depth, []).append(node)
    width = max(920, max(len(v) for v in levels.values()) * 240 + 60)
    pos = {}
    for depth, group in levels.items():
        # 按父节点的横坐标排列，保证同一分段的节点相邻。
        group.sort(key=lambda n: (pos.get(n.get('parent_id'), (0, 0))[0], n.get('narrative_order', 0)))
        for i, node in enumerate(group):
            pos[node['id']] = ((i + .5) * width / len(group), 90 + depth * 170)
    return pos, width, 180 + max(levels) * 170


def svg(graph, network=False):
    pos, width, height = positions(graph, network)
    esc = lambda text: html.escape(str(text), quote=True)
    edge_threads = {e['id']: [t['id'] for t in graph['threads'] if e['id'] in t.get('edge_ids', [])] for e in graph['edges']}
    colors = {t['id']: COLORS[i % len(COLORS)] for i, t in enumerate(graph['threads'])}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="剧情结构图">',
             '<style>text{font-family:system-ui,Arial,sans-serif}.node{cursor:pointer}.node:focus rect{stroke:#111;stroke-width:3}</style>',
             '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8b8177"/></marker></defs>']
    for node in graph['nodes']:
        if node.get('parent_id') and not network:
            x1, y1 = pos[node['parent_id']]
            x2, y2 = pos[node['id']]
            parts.append(f'<path class="structure" data-from="{node["parent_id"]}" data-to="{node["id"]}" d="M{x1},{y1 + 32} C{x1},{y1 + 85} {x2},{y2 - 85} {x2},{y2 - 32}" fill="none" stroke="#c7c0b5" stroke-width="2"/>')
    for index, edge in enumerate(graph['edges']):
        x1, y1 = pos[edge['from']]
        x2, y2 = pos[edge['to']]
        tids = edge_threads[edge['id']]
        color = colors.get(tids[0], '#6f7470') if tids else '#6f7470'
        bend = 55 + (index % 4) * 22
        midx, midy = (x1 + x2) / 2, min(y1, y2) - bend
        label = edge.get('label', edge['kind'])
        parts.append(f'<g class="relation" data-from="{edge["from"]}" data-to="{edge["to"]}" data-threads="{esc(" ".join(tids))}"><path d="M{x1},{y1 - 28} Q{midx},{midy - 65} {x2},{y2 - 28}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="7 5" marker-end="url(#arrow)"/><text x="{midx}" y="{midy}" text-anchor="middle" fill="{color}" font-size="12">{esc(label[:28])}</text></g>')
    for node in graph['nodes']:
        x, y = pos[node['id']]
        title = node['title']
        shown = title[:15] + ('…' if len(title) > 15 else '')
        parts.append(f'<g class="node" tabindex="0" role="button" aria-label="{esc(title)}" data-node="{node["id"]}"><title>{esc(title)}</title><rect x="{x - 104}" y="{y - 32}" width="208" height="64" rx="10" fill="#fffdf8" stroke="#b3a797"/><text x="{x}" y="{y - 1}" text-anchor="middle" fill="#292d29" font-size="14">{esc(shown)}</text><text x="{x}" y="{y + 20}" text-anchor="middle" fill="#83796e" font-size="10">{esc(node["kind"])} · {esc(node["claim_kind"])}</text></g>')
    parts.append('</svg>')
    return '\n'.join(parts)


def mermaid(graph):
    names = {n['id']: f'n{i}' for i, n in enumerate(graph['nodes'])}
    # Mermaid 使用实体编码，防止标签闭合语法并注入图指令。
    label = lambda text: ''.join(f'#{ord(c)};' if c in '"[]{}<>`\\\n' else c for c in str(text))
    lines = [f'# {graph["title"]}', '', '实线表示结构归属，虚线表示跨节点关系；依据类型详见节点数据。', '', '```mermaid', 'flowchart TD']
    for node in graph['nodes']:
        lines.append(f'  {names[node["id"]]}["{label(node["title"])}"]')
        if node.get('parent_id'):
            lines.append(f'  {names[node["parent_id"]]} --> {names[node["id"]]}')
    for edge in graph['edges']:
        lines.append(f'  {names[edge["from"]]} -. "{label(edge.get("label", edge["kind"]))}" .-> {names[edge["to"]]}')
    lines.extend(['```', '', '## 剧情线', ''])
    lines.extend(f'- {t["title"]}：{t["kind"]} / {t["status"]}' for t in graph['threads'])
    return '\n'.join(lines) + '\n'


def render(graph, destination):
    destination.mkdir(parents=True, exist_ok=True)
    tree, network = svg(graph), svg(graph, True)
    template = Path(__file__).with_name('viewer.html').read_text(encoding='utf-8')
    payload = json.dumps(graph, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    document = template.replace('@@TITLE@@', html.escape(graph['title'])).replace('@@TREE@@', tree).replace('@@NETWORK@@', network).replace('@@DATA@@', payload)
    files = {'index.html': document, 'plot-tree.svg': tree, 'plot-network.svg': network, 'plot.md': mermaid(graph)}
    for name, text in files.items():
        atomic_write(destination / name, text)
    return {'directory': str(destination.resolve()), 'files': list(files)}
