---
name: distill-novels
description: Distill one or many novels into a reusable writing knowledge skill, selectively extracting worldbuilding architecture, character systems, plot structure, narrative craft, prose style, dialogue, pacing, themes, or continuity constraints. Use when Codex needs to analyze TXT, Markdown, EPUB, PDF, DOCX, HTML, or RTF fiction; compare techniques across multiple books; build or update a private story-craft library; or use distilled principles to outline, draft, revise, polish, and consistency-check the user's own fiction without reproducing source prose.
---

# Distill Novels

Turn fiction sources into a private, evidence-grounded writing skill. Extract reusable mechanisms and constraints, not a compressed copy of the novels.

## Route the request

Identify:

- `SOURCES`: one or more files, folders, or globs.
- `DIMENSIONS`: any of `worldbuilding`, `characters`, `plot`, `style`, `narrative`, `dialogue`, `pacing`, `themes`, `continuity`, or `all`.
- `MODE`: `analyze-only`, `create`, `update`, or `compare`.
- `DEPTH`: `compact`, `standard`, or `deep`; default to `standard`.
- `DESTINATION`: output skill folder.

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
8. Generate files according to [references/output-schema.md](references/output-schema.md). Omit unselected dimension files.
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

Report source count, selected dimensions, warnings, generated or updated files, and example invocations. Explicitly flag weak chapter detection, uncertain metadata, extraction loss, or dimensions with insufficient evidence.
