"""剧情组织树与跨节点暗线；结构校验不代替文学判断。"""

import copy
from pathlib import Path

from .storage import commit, json_text, locked, new_id, read_json, safe_path
from .vault import CLAIMS, identifier, now, require_text

EDGE_KINDS = {'cause', 'setup', 'reveal', 'misdirection', 'reversal', 'echo', 'payoff'}
THREAD_STATES = {'open', 'partial', 'resolved', 'abandoned', 'unknown'}


def graph_path(owner_kind, owner_id):
    identifier(owner_id)
    if owner_kind == 'project':
        return f'books/{owner_id}/outline/plot-graph.json'
    if owner_kind == 'source':
        return f'library/sources/{owner_id}/plot-graph.json'
    raise ValueError('图归属必须是 project 或 source')


def all_graphs(vault):
    return [record for pattern in ('books/*/outline/plot-graph.json', 'library/sources/*/plot-graph.json')
            for _, record in vault._records(pattern)]


def validate_graph(graph, vault=None):
    require_text(graph.get('title'), 'graph.title', 500)
    nodes, edges, threads = graph.get('nodes'), graph.get('edges'), graph.get('threads')
    if not isinstance(nodes, list) or not nodes or not isinstance(edges, list) or not isinstance(threads, list):
        raise ValueError('图必须包含 nodes、edges 和 threads 列表')
    lookup = {}
    for node in nodes:
        key = identifier(node['id'])
        if key in lookup:
            raise ValueError('重复图节点: ' + key)
        lookup[key] = node
        require_text(node.get('title'), 'node.title', 500)
        if node.get('kind') not in {'story', 'volume', 'arc', 'scene', 'event'}:
            raise ValueError('图节点 kind 无效')
        if node.get('claim_kind') not in CLAIMS:
            raise ValueError('节点必须声明事实、推断、综合或计划')
        if 'narrative_order' in node and (type(node['narrative_order']) is not int or node['narrative_order'] < 0):
            raise ValueError('叙述顺序必须是非负整数')
        if vault:
            vault.validate_evidence(node.get('evidence', []))
            for aid in node.get('characters', []):
                if vault._get_asset(aid)['asset_type'] != 'character':
                    raise ValueError('节点人物引用不是人物卡')
        for knowledge in node.get('knowledge', []):
            if knowledge.get('state') not in {'unknown', 'suspects', 'knows', 'misbelieves'}:
                raise ValueError('认知状态无效')
            if knowledge.get('state') == 'misbelieves':
                require_text(knowledge.get('belief'), '错误信念')
            observer = knowledge.get('observer')
            if observer != 'reader':
                identifier(observer)
                if vault and vault._get_asset(observer)['asset_type'] != 'character':
                    raise ValueError('认知主体不是人物')
    roots = [n for n in nodes if n.get('parent_id') is None]
    if len(roots) != 1:
        raise ValueError('结构树必须恰有一个根节点')
    for node in nodes:
        chain, current = set(), node['id']
        while current is not None:
            if current not in lookup:
                raise ValueError('结构父节点不存在: ' + current)
            if current in chain:
                raise ValueError('结构树存在循环')
            chain.add(current)
            current = lookup[current].get('parent_id')
    edge_map = {}
    for edge in edges:
        eid = identifier(edge['id'])
        if eid in edge_map or edge.get('from') not in lookup or edge.get('to') not in lookup:
            raise ValueError('重复关系或关系端点不存在')
        if edge.get('kind') not in EDGE_KINDS or edge.get('claim_kind') not in CLAIMS:
            raise ValueError('关系类型或依据类型无效')
        if vault:
            vault.validate_evidence(edge.get('evidence', []))
        edge_map[eid] = edge
    tids = set()
    for thread in threads:
        tid = identifier(thread['id'])
        if tid in tids:
            raise ValueError('重复剧情线 ID')
        tids.add(tid)
        require_text(thread.get('title'), 'thread.title', 500)
        if thread.get('kind') not in {'main', 'subplot', 'hidden'} or thread.get('status') not in THREAD_STATES:
            raise ValueError('剧情线类别或状态无效')
        members, relations = thread.get('node_ids', []), thread.get('edge_ids', [])
        if not members or len(set(members)) != len(members) or not set(members).issubset(lookup) or not set(relations).issubset(edge_map):
            raise ValueError('剧情线成员或关系无效')
        if any(edge_map[e]['from'] not in members or edge_map[e]['to'] not in members for e in relations):
            raise ValueError('剧情线关系越出成员范围')
        if thread['status'] == 'resolved' and not any(edge_map[e]['kind'] in {'payoff', 'reveal'} for e in relations) and not thread.get('resolution_note'):
            raise ValueError('已回收剧情线必须提供回收/揭示关系或明确的完成依据')
    owner = graph.get('owner', {})
    coverage = graph.get('coverage', [])
    if not isinstance(coverage, list):
        raise ValueError('coverage 必须是列表')
    if vault:
        for item in coverage:
            source = vault._source(item['source_id'])
            revision = next((r for r in source['revisions'] if r['revision'] == item.get('revision')), None)
            if revision is None or not set(item['chapter_ids']).issubset(c['chapter_id'] for c in revision['chapters']):
                raise ValueError('分析覆盖范围无效')
            if type(item.get('complete')) is not bool:
                raise ValueError('coverage.complete 必须是布尔值')
            if item['complete'] and set(item['chapter_ids']) != {c['chapter_id'] for c in revision['chapters']}:
                raise ValueError('未读完整来源，不能标为完整覆盖')
        if owner.get('kind') == 'source':
            if not coverage or not any(c['source_id'] == owner['id'] for c in coverage):
                raise ValueError('来源剧情图必须注明已读范围')
            for item in [n for n in nodes if n['kind'] in {'scene', 'event'}] + edges:
                if item['claim_kind'] == 'plan' or not item.get('evidence'):
                    raise ValueError('来源剧情图的事件和关系必须有证据，不能填入原创计划')
                covered = {(c['source_id'], c['revision'], ch) for c in coverage for ch in c['chapter_ids']}
                if any((e['source_id'], e['revision'], e['chapter_id']) not in covered for e in item['evidence']):
                    raise ValueError('图证据超出已读范围')
    return True


def graph_updates(vault, owner_kind, owner_id, data, base_revision=None):
    if owner_kind == 'project':
        vault._project(owner_id)
    elif owner_kind == 'source':
        owner_id = vault._source(owner_id)['source_id']
    path = graph_path(owner_kind, owner_id)
    current = vault._read(path) if safe_path(vault.root, path).exists() else None
    record = copy.deepcopy(data)
    record.update(schema_version=1, owner={'kind': owner_kind, 'id': owner_id})
    record['graph_id'] = current['graph_id'] if current else new_id('graph')
    validate_graph(record, vault)
    compare = lambda value: {k: v for k, v in value.items() if k not in {'revision', 'updated_at'}}
    if current and compare(record) == compare(current):
        return current, {}
    if current and (type(base_revision) is not int or base_revision != current['revision']):
        raise ValueError('剧情图版本冲突')
    if not current and base_revision not in (None, 0):
        raise ValueError('新剧情图不能声称已有版本')
    record['revision'] = current['revision'] + 1 if current else 1
    record['updated_at'] = now()
    changes = {path: json_text(record)}
    if current:
        changes[f"history/graphs/{current['graph_id']}/{current['revision']}.json"] = json_text(current)
    return record, changes


def save_graph(vault, owner_kind, owner_id, data, base_revision=None):
    with locked(vault.root):
        record, changes = graph_updates(vault, owner_kind, owner_id, data, base_revision)
        commit(vault.root, changes)
        return record


def render_graph(graph, destination):
    from .render import render
    validate_graph(graph)
    return render(graph, Path(destination))
