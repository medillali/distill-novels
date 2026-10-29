# Distill Novels — Multi-book Fiction Distillation Skill

Distill one or many novels into an evidence-grounded writing knowledge base for worldbuilding, characters, plot, prose style, narrative technique, dialogue, pacing, themes, and continuity.

`distill-novels` is an Agent Skill for Codex and compatible hosts. It analyzes each novel separately, preserves source provenance, compares techniques across books, and converts findings into neutral craft controls for original fiction outlining, drafting, revision, and consistency checking.

## Persistent library extension

This local development branch adds a separate personal vault with versioned character/scene/pattern cards, project-pinned references, provenance, favorites, user notes, usage feedback and resumable analysis checkpoints. Plot data combines a structural tree with overlapping hidden-thread relations and reader/character knowledge states. Offline HTML, SVG and Mermaid views are generated from the JSON records.

Versioned working bundles support a Codex–ChatGPT file round trip with three-way conflict detection. Backup archives preserve portable records and history, excluding source novels and machine configuration. GitHub and Space connections are deferred; local Space metadata is not a remote synchronization service or ChatGPT memory write.

Python 3.10+ and its standard library are sufficient. The host model performs literary analysis; the scripts do not call an LLM API.

```text
python scripts/demo.py --output work/demo
python scripts/library.py --vault ../writing-vault init
python scripts/library.py --vault ../writing-vault status
python -m unittest discover -s tests -v
```

Open `work/demo/views/index.html`; the demo directory must be empty. See [library workflow](references/library-workflow.md), [ChatGPT handoff](references/chatgpt-handoff.md), and the [Chinese user guide](docs/使用指南.md).

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

## Use locally

Ask Codex to read this checkout's `SKILL.md`. Global installation is optional. To install later, use this enhanced checkout in the host's skill directory and reload skills. The upstream repository does not contain these unpublished local changes. Keep the private vault outside the tool checkout.

See the [Chinese README](README.md) for dimensions, workflow, local preprocessing, and output structure.

## Keywords

AI fiction writing, novel analysis, story bible, worldbuilding, character development, plot structure, prose style analysis, dialogue analysis, narrative craft, pacing, continuity checker, multi-book knowledge base, Codex skill, Agent Skills.

## License

[MIT](LICENSE)
