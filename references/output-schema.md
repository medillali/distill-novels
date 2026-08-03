# Generated skill schema

Create only files justified by selected dimensions.

```text
<generated-skill>/
├── SKILL.md
├── sources.md
├── synthesis.md
├── craft-controls.md
├── worldbuilding.md
├── characters.md
├── plot.md
├── style.md
├── narrative.md
├── dialogue.md
├── pacing.md
├── themes.md
├── continuity.md
└── books/
    └── <source-id>/
        ├── overview.md
        └── chapters/<chapter-id>.md
```

## Master SKILL.md

Keep it concise. Include scope, source index, dimension index, topic routing, downstream actions, provenance rule, originality guardrails, and links to files. Do not duplicate detailed findings.

## sources.md

For each work record source ID, title, author if known, path or filename, format, relationship to other volumes, extraction status, chapter-detection confidence, and warnings.

## Per-source overview

Include premise in paraphrase, structural map, selected-dimension highlights, uncertainty, and links to bounded chapter analyses. A chapter file should capture state before, causal events, state after, selected observations, and locators.

## Dimension files

Use entries shaped as:

```markdown
## <finding name>
- Sources: `book-a` ch12; `book-b` ch04
- Observation: <what the texts demonstrably do>
- Mechanism: <why it creates an effect>
- Transferable principle: <neutral reusable rule>
- Controls: <parameters a writer can adjust>
- Risks: <failure modes or trade-offs>
- Confidence: high | medium | low
```

## synthesis.md

Compare sources without flattening them. Include convergence, divergence, complementary techniques, incompatible assumptions, and possible original combinations. Label combinations as new synthesis rather than attributing them to a source.

## craft-controls.md

Provide a compact control panel usable during drafting and revision. Use adjustable parameters, decision rules, checklists, and trade-offs. Never name a living author as a style target.

## Scale by depth

- `compact`: overviews and high-signal findings; no per-chapter files unless essential.
- `standard`: chapter map plus selective chapter files for evidence-heavy sections.
- `deep`: bounded analysis of every chapter, fuller continuity state, and cross-dimension links.
