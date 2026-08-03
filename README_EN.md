# Distill Novels — Multi-book Fiction Distillation Skill

Distill one or many novels into an evidence-grounded writing knowledge base for worldbuilding, characters, plot, prose style, narrative technique, dialogue, pacing, themes, and continuity.

`distill-novels` is an Agent Skill for Codex and compatible hosts. It analyzes each novel separately, preserves source provenance, compares techniques across books, and converts findings into neutral craft controls for original fiction outlining, drafting, revision, and consistency checking.

## Highlights

- Distill and compare multiple novels without mixing their canons.
- Select `worldbuilding`, `characters`, `plot`, `style`, `narrative`, `dialogue`, `pacing`, `themes`, `continuity`, or `all`.
- Use `analyze-only`, `create`, `compare`, and `update` modes.
- Choose `compact`, `standard`, or `deep` analysis.
- Process TXT, Markdown, EPUB, DOCX, HTML, RTF, reStructuredText, and AsciiDoc locally; connect PDFs through the host PDF workflow.
- Detect Chinese and English chapter headings and common Chinese TXT encodings.
- Generate reusable, original writing controls instead of quote collections or author-imitation prompts.

## Example

```text
Use $distill-novels to compare the worldbuilding, character arcs, and pacing
of these novels at deep depth, then create a reusable fiction-writing skill.
```

## Install

```bash
git clone https://github.com/CloudLiu1008/distill-novels.git ~/.codex/skills/distill-novels
```

Gitee mirror:

```bash
git clone https://gitee.com/liu-muyun/distill-novels.git ~/.codex/skills/distill-novels
```

See the [Chinese README](README.md) for dimensions, workflow, local preprocessing, and output structure.

## Keywords

AI fiction writing, novel analysis, story bible, worldbuilding, character development, plot structure, prose style analysis, dialogue analysis, narrative craft, pacing, continuity checker, multi-book knowledge base, Codex skill, Agent Skills.

## License

[MIT](LICENSE)
