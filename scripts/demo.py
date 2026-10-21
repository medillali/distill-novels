#!/usr/bin/env python3
"""创建独立原创演示，不向真实资料库填入示例卡片。"""

import argparse
import json
from pathlib import Path
import sys

from prepare_sources import prepare
from fictionlib.exchange import export_bundle, backup, restore
from fictionlib.graph import save_graph, render_graph
from fictionlib.storage import json_text, read_json
from fictionlib.vault import Vault


def create_demo(output):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('演示输出目录必须为空')
    repo = Path(__file__).resolve().parents[1]
    vault = Vault.init(output / 'vault')
    manifest = prepare([repo / 'examples' / 'lighthouse.txt'], vault.root / 'private-sources' / 'normalized')
    vault.import_sources(manifest)
    source = manifest['sources'][0]
    evidence = lambda chapter: [{'source_id': source['source_id'], 'revision': source['revision'], 'chapter_id': f'ch-{chapter:04d}', 'claim_kind': 'inference'}]
    common = {'scope': 'source-analysis', 'tags': ['秘密', '信任'], 'favorite': True}
    keeper = vault.put_asset({**common, 'asset_type': 'character', 'title': '罗岚：用行动表达关心的守灯人',
        'origin_key': source['source_id'] + '/character/luolan', 'content': {'summary': '拒绝透露秘密，却用实际帮助保护阿桥；承诺与关心之间的矛盾推动行动。',
        'goal': '履行对姑姑的承诺', 'need': '取得阿桥的信任', 'conflict': '保护对方与隐瞒真相相冲突', 'arc': '从回避解释到主动带阿桥见寄信人'}, 'evidence': evidence(2)})
    courier = vault.put_asset({**common, 'asset_type': 'character', 'title': '阿桥：从索要答案到自主选择',
        'origin_key': source['source_id'] + '/character/aqiao', 'content': {'summary': '他需要父亲的答案，最后发现自己可以决定何时回应。',
        'goal': '弄清父亲的去向', 'need': '取得自己的选择权', 'arc': '追问—合作—揭密后的主动停步'}, 'evidence': evidence(3)})
    scene = vault.put_asset({**common, 'asset_type': 'scene', 'title': '拒绝解释，却给对方灯油',
        'origin_key': source['source_id'] + '/scene/refusal', 'content': {'summary': '在一次拒绝中加入付出代价的帮助，让人物关系不因隐瞒停滞。',
        'goal': '要求交信', 'obstacle': '守灯人遵守承诺', 'choice': '阿桥放弃抢夺，选择合作', 'consequence': '获得次日见面承诺',
        'why_it_works': '语言和行动形成张力，信息被延迟，关系却在推进', 'failure_mode': '若帮助毫无成本，容易显得只是拖延揭密'}, 'evidence': evidence(2)})
    project = vault.create_project('原创结构演示（不是真实创作项目）')
    for asset in [keeper, courier, scene]:
        vault.use_asset(project['project_id'], asset['asset_id'])
    graph = read_json(repo / 'examples' / 'plot.json')
    graph['nodes'][5]['knowledge'] = [{'observer': 'reader', 'state': 'suspects', 'belief': '父亲可能活着'}, {'observer': courier['asset_id'], 'state': 'misbelieves', 'belief': '父亲已经死去'}]
    saved = save_graph(vault, 'project', project['project_id'], graph)
    render_graph(saved, output / 'views')
    vault.build_views()
    export_bundle(vault, output / 'chatgpt-pack', project_id=project['project_id'])
    backup(vault, output / 'demo-backup.zip')
    restored = restore(output / 'demo-backup.zip', output / 'restored-vault')
    summary = {**vault.validate(), 'project_id': project['project_id'], 'graph_id': saved['graph_id'],
               'directory': str(output), 'restore_verified': restored['valid']}
    (output / 'demo-result.json').write_text(json_text(summary), encoding='utf-8')
    (output / 'START-HERE.md').write_text('# 原创演示\n\n此目录全部内容用于功能演示。\n\n- [剧情图](views/index.html)\n- [卡片目录](vault/library/views/index.md)\n- [ChatGPT 工作包](chatgpt-pack/context.md)\n- [验证结果](demo-result.json)\n\n真实个人资料库位于独立的 writing-vault，不包含这些示例卡片。\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='生成独立原创演示与可离线剧情图')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(create_demo(args.output), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
