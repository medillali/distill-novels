# Persistent fiction library

Use this reference for durable cards, plot graphs and incremental analysis. Commands run from the tool repository with Python 3.10+. The runtime needs only the standard library. On hosts without `python` on PATH, locate the host's bundled Python; do not silently install a system interpreter.

## Locate and resume

Use the existing vault path from workspace instructions. An initial setup can run:

```text
python scripts/library.py --vault ../writing-vault init
python scripts/library.py --vault ../writing-vault status
python scripts/library.py --vault ../writing-vault sources
python scripts/library.py --vault ../writing-vault projects
python scripts/library.py --vault ../writing-vault search --query 信任 --type scene
```

`--vault` precedes the subcommand. `status` validates the store. Complete JSON is authoritative; `library/views/` is a generated reading copy. The vault is separate from the tool Git repository. Global skill installation is optional; a host can read this repository's SKILL.md directly.

## Register sources before interpreting them

```text
python scripts/prepare_sources.py ./incoming/book.txt --output ../writing-vault/private-sources/normalized
python scripts/library.py --vault ../writing-vault sources-import --file ../writing-vault/private-sources/normalized/manifest.json
```

Reuse the same normalized directory for successive imports. `source_id` is stable identity, `revision` is a content hash. A changed edition should use `--source-id <existing-src-id>` with one input file. Without this explicit identity, changed content creates a separate source. Old revisions remain available. Never infer identical characters from matching names. Legacy source IDs are retained as aliases when migrating an existing manifest with its extracted files.

Read the manifest's warnings, normalized text path and chapter indexes. Select bounded chapter ranges according to context budget; read actual normalized text, then analyze. Extraction alone is not distillation. Record partial coverage rather than claiming to have analyzed a whole novel.

## Save cards and protect hand edits

Create a JSON file (e.g. `work/card.json`):

```json
{
  "asset_type": "character",
  "scope": "source-analysis",
  "title": "某人物：保护与隐瞒的矛盾",
  "origin_key": "src-REPLACE/character/keeper",
  "tags": ["信任", "秘密"],
  "content": {
    "summary": "基于实际阅读的简短人物观察。",
    "goal": "外在目标",
    "need": "内在需求",
    "conflict": "选择中暴露的矛盾",
    "arc": "已阅读章节呈现的变化"
  },
  "evidence": [{
    "source_id": "src-REPLACE",
    "revision": "REPLACE_WITH_MANIFEST_SHA256",
    "chapter_id": "ch-0001",
    "claim_kind": "inference"
  }],
  "user_notes": "",
  "favorite": false,
  "review_status": "draft"
}
```

Replace IDs/hashes with actual manifest values. These placeholders are documentation, not importable evidence. Optional `start_line` / `end_line` must both lie inside that chapter. `claim_kind`: `fact`, `inference`, `synthesis`, `plan`. Label literary interpretations as inference.

```text
python scripts/library.py --vault ../writing-vault asset-put --file work/card.json --generated
python scripts/library.py --vault ../writing-vault asset-show --id <returned-id>
python scripts/library.py --vault ../writing-vault asset-put --file work/card-update.json --base-revision 1 --generated
python scripts/library.py --vault ../writing-vault views
```

For updates, include the existing `asset_id`, or retain its stable `origin_key`, and use the current base revision. `--generated` preserves existing `user_notes`, `favorite`, `review_status`. A user-requested edit to those fields uses `asset-put` without `--generated`. Old versions are retained under `history/`. Do not bypass conflict errors by overwriting the JSON directly.

For `scene` cards, describe `goal`, `obstacle`, `choice`, `consequence`, `state_change`, `why_it_works`, `applicability`, `failure_mode` in `content`; only `summary` is structurally required. Create `pattern` + `reusable-pattern` for transferable mechanisms and retain `derived_from: [{"asset_id":"...","revision":1}]`. Create `original-project` cards with `project_id` for actual project canon. Keep distinctive reference characters separate from original adaptations.

Search supports `--type`, repeated `--tag`, `--favorite`, `--scope`, `--source` and `--project`. A project-filtered search finds referenced IDs in the global collection; read `project-show` and `asset-show --revision` when the pinned version matters.

## Reuse in a project

```text
python scripts/library.py --vault ../writing-vault project-create --title 我的新小说
python scripts/library.py --vault ../writing-vault project-use --project <project-id> --asset <asset-id> --revision 1
python scripts/library.py --vault ../writing-vault project-show --project <project-id>
```

`project-use` pins a version and hash. Repeating it with another revision explicitly upgrades that project's reference. Archiving a project does not delete global cards. Save the adaptation and its observed result with `usage-add --file`:

```json
{"project_id":"proj-REPLACE","asset_id":"scn-REPLACE","revision":1,"adaptation":"如何将机制变成原创场景","feedback":"实际使用后的观察","evidence_type":"editorial-judgment"}
```

Use `reader-observation` only for actual reader feedback, `experiment` only for a real comparison. Do not present editorial preference as measured reader response.

## Plot trees and hidden threads

Start from [../examples/plot.json](../examples/plot.json) for the structural shape, not its fictional events. `nodes[].parent_id` creates one acyclic structural tree. `edges` independently connect any nodes; allowed kinds are `cause`, `setup`, `reveal`, `misdirection`, `reversal`, `echo`, `payoff`. `threads` group overlapping node/edge sets: `main`, `subplot`, `hidden`; status is `open`, `partial`, `resolved`, `abandoned`, `unknown`. A resolved thread needs a payoff/reveal edge or a concrete resolution note.

For source analysis, add `coverage` entries with `source_id`, `revision`, `chapter_ids`, `complete`; mark complete only if every indexed chapter is covered. Source graph events and edges require evidence inside coverage. For original planning, use `claim_kind: plan` and owner `project`. Event order `narrative_order` records presentation order; optional `story_time` records fictional time. Character references use existing card IDs. Knowledge entries use `observer: reader` or a character card ID and `state: unknown|suspects|knows|misbelieves`; `belief` explains the information gap.

```text
python scripts/library.py --vault ../writing-vault graph-save --owner-kind project --owner-id <project-id> --file work/plot.json
python scripts/library.py --vault ../writing-vault graph-render --owner-kind project --owner-id <project-id> --output work/plot-view
```

Source analysis uses `--owner-kind source --owner-id <source-id>`. Existing graph updates require `--base-revision`. HTML supports tree/network switching, thread highlighting, segment filters, node details and zoom. SVG and Mermaid copies are available for documents. For very large works, process by volume/arc; all-node rendering is not a demonstrated large-corpus performance solution.

## Checkpoint a long analysis

After each committed batch, save via `checkpoint --file`:

```json
{"run_id":"run-example","source_id":"src-REPLACE","source_revision":"REPLACE_WITH_MANIFEST_SHA256","completed_chapters":["ch-0001"],"pending_chapters":["ch-0002"],"dimensions":["characters","plot"],"notes":"下一批先核对人物对信件的认知"}
```

Resume using `checkpoint-show --id run-example`, reread saved cards, and read pending text. A run cannot change source/revision. Save source changes as a new run. End by running `validate`, rebuilding views and reporting actual coverage and uncertainty.
