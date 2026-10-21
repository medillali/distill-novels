---
name: distill-novels
description: Analyze fiction with chapter evidence, preserve reusable character and scene cards across writing projects, map plot trees and hidden threads, and exchange versioned writing context with ChatGPT. Use for novel distillation, private fiction libraries, original outlining, revision, and continuity checks.
---

# Distill Novels

Turn fiction sources into a private, evidence-grounded writing skill. Extract reusable mechanisms and constraints, not a compressed copy of the novels.

## Persistent library route

For long-term storage, cross-project reuse, plot graphs, or resuming an earlier analysis, read [references/library-workflow.md](references/library-workflow.md). Use the existing personal vault outside this tool repository; locate it from workspace instructions or the user's chosen path. Do not create a new vault per novel or per conversation.

For ChatGPT handoff, returned changes, backups, or a requested Space connection, read [references/chatgpt-handoff.md](references/chatgpt-handoff.md). Files are the authoritative store. Local synchronization metadata is not evidence of a successful remote write.

The scripts handle extraction, storage and validation. The host model must read bounded source chapters and perform the literary analysis. Do not invent observations from filenames, snippets, or an unread full book. Continue from saved checkpoints and report the chapters actually covered.

Keep three layers separate: `source-analysis` (observations about a source), `reusable-pattern` (abstract craft), and `original-project` (the user's project canon). Project references pin card revisions; upgrading a reference is an explicit operation. Use `--generated` for repeated distillation to preserve user notes, favorites and review choices.

Cards and graphs live in versioned JSON. Generate Markdown and offline HTML views for reading. A selected scene stores a paraphrased causal mechanism, source locator, applicability and failure conditions; it is not a long excerpt archive. Build a structural parent tree plus independent relation edges and threads for concealed motives, misdirection, echoes and payoffs.

## Route the request

Identify:

- `SOURCES`: one or more files, folders, or globs.
- `DIMENSIONS`: any of `worldbuilding`, `characters`, `plot`, `style`, `narrative`, `dialogue`, `pacing`, `themes`, `continuity`, or `all`.
- `MODE`: `analyze-only`, `create`, `update`, or `compare`.
- `DEPTH`: `compact`, `standard`, or `deep`; default to `standard`.
- `DESTINATION`: existing vault for durable work, or output skill folder for a standalone analysis artifact.

Infer these from the request when clear. Ask only for a choice that materially changes the result. If dimensions are omitted, show the dimension menu from [references/dimensions.md](references/dimensions.md) and recommend `all` for a general-purpose writing assistant.

Treat multiple sources as separate works unless the user explicitly says they are volumes in one continuity. Never merge similarly named characters, locations, events, or rules without evidence.

## Workflow

1. Validate that sources exist and identify format, encoding, size, and likely chapter boundaries.
2. For TXT/Markdown/HTML/RTF/EPUB/DOCX, run `scripts/prepare_sources.py` when possible. For PDF, use the host's PDF extraction workflow first, then feed normalized text to this workflow.
3. Create a source manifest with a stable `source_id` for every work. Record title, author when evident, filename, format, and extraction warnings.
4. Estimate scope before expensive analysis. For large corpora, index headings and process bounded chapter slices; never load every book into context repeatedly.
5. Read [references/dimensions.md](references/dimensions.md) for the selected dimensions only.
6. Extract observations per source and attach evidence locators such as chapter, heading, or line range. Mark interpretations as inference, not fact.
7. Build cross-book synthesis only after per-source extraction. Separate:
   - shared techniques;
   - contrasting implementations;
   - source-specific signatures;
   - transferable principles for the user's work.
8. For durable work, persist cards, graphs and checkpoints through `scripts/library.py` following the library reference. For standalone reports, generate files according to [references/output-schema.md](references/output-schema.md). Omit unselected dimension files.
9. Run contradiction, provenance, and leakage checks from [references/safety-quality.md](references/safety-quality.md).
10. In `update` mode, preserve source IDs and existing user-authored notes; append or revise only affected indexes and dimension files.

## Extraction rules

- Preserve causal structure: desire → obstacle → choice → consequence → state change.
- Separate textual fact, strong inference, and speculative interpretation.
- Attribute every source-specific claim to its `source_id` and locator.
- Abstract style into measurable or operational traits: sentence-length variation, syntax, imagery density, narrative distance, information timing, dialogue ratio, paragraph rhythm, and scene-transition patterns.
- Do not store long excerpts or assemble a quote bank. Use short evidence fragments only when essential and permitted; prefer paraphrase plus locator.
- Do not instruct the downstream agent to imitate a living author. Convert observations into neutral craft controls that can be combined into an original voice.
- Keep the user's manuscript, preferences, and canon separate from reference novels. Reference material may suggest options but must not silently become canon.

## Using the generated skill

The generated skill must support four downstream actions:

1. `analyze`: explain a source-backed technique or comparison.
2. `design`: propose original characters, settings, plots, or scenes from abstract principles.
3. `revise`: polish the user's prose against selected craft controls while preserving meaning and voice.
4. `check`: detect continuity, motivation, timeline, POV, or world-rule conflicts.

When drafting, offer original alternatives rather than transferring distinctive names, settings, characters, scenes, or phrasing from sources. When revising, state which controls were applied if that helps the user evaluate the edit.

## Completion report

Report source count, covered chapters, selected dimensions, warnings, saved card IDs/revisions, graph and reading-view paths, and example invocations. Separate local persistence, exported handoff files and actual cloud synchronization. Explicitly flag weak chapter detection, uncertain metadata, extraction loss, or dimensions with insufficient evidence.
