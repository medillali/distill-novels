# Distill Novels：多小说蒸馏与 AI 写作知识库 Skill

> 将一本或多本小说蒸馏为可复用的世界观、人物、情节、文风、叙事、对话、节奏、主题与连续性知识库，辅助原创小说构思、写作、润色和一致性检查。

[English](README_EN.md) · [GitHub](https://github.com/CloudLiu1008/distill-novels) · [Gitee](https://gitee.com/liu-muyun/distill-novels)

`distill-novels` 是一个面向 Codex 和兼容 Agent Skills 标准的小说分析 Skill。它支持从多本小说中分别提取有出处的观察，再进行跨书比较和抽象，最终生成可供 AI 写作助手按需加载的原创写作知识库。

## 为什么使用 Distill Novels？

- **多书蒸馏**：同时处理多本小说，保留独立 `source_id`，避免人物、世界和事件串书。
- **按维度选择**：只分析需要的部分，降低成本和上下文占用。
- **适合中文小说**：支持中文章节标题及 GB18030、Big5、UTF-16 等常见 TXT 编码。
- **可增量更新**：新书可以加入已有知识库，无需从头生成。
- **面向原创写作**：将文风转为可调节写作参数，不建立原句库，也不要求模仿特定作者。
- **证据可追踪**：重要发现标注来源书籍和章节位置，并区分事实、推断与综合结论。

## 可指定的蒸馏维度

| 参数 | 提取内容 |
|---|---|
| `worldbuilding` | 世界规则、地理、势力、制度、历史、资源与魔法/技术体系 |
| `characters` | 人物目标、需求、矛盾、秘密、关系、声音与人物弧 |
| `plot` | 情节因果、转折、反转、伏笔、回收、支线与信息揭示 |
| `style` | 句法、词汇、意象密度、叙述距离、段落节奏等中性风格参数 |
| `narrative` | POV、时态、聚焦、叙述者可靠性、悬念与信息差 |
| `dialogue` | 潜台词、身份博弈、打断、沉默、角色话语差异 |
| `pacing` | 场景长度、压缩与展开、事件密度、张力曲线 |
| `themes` | 主题问题、价值冲突、意象与人物给出的不同答案 |
| `continuity` | 时间线、地点、伤势、物品、知识状态、承诺与世界规则 |
| `all` | 全部维度以及它们之间的因果联系 |

## 支持的文件格式

- 原生预处理：TXT、Markdown、EPUB、DOCX、HTML、RTF、reStructuredText、AsciiDoc
- 可通过宿主 PDF 工具接入：PDF
- 中文 TXT 编码：UTF-8、GB18030、Big5、UTF-16

## 使用示例

```text
使用 $distill-novels 蒸馏这三本小说，只分析世界观和人物，
深度选择 deep，生成供我写小说使用的 skill。
```

```text
使用 $distill-novels 比较这些小说的叙事、对话和节奏，
把共同规律和差异整理成原创写作控制面板。
```

```text
使用 $distill-novels 将新小说加入已有知识库，
只更新人物、伏笔、时间线和世界规则。
```

支持四种模式：`analyze-only`、`create`、`compare`、`update`；支持三档深度：`compact`、`standard`、`deep`。

## 安装

将本仓库克隆到 Codex skills 目录：

```bash
git clone https://github.com/CloudLiu1008/distill-novels.git ~/.codex/skills/distill-novels
```

也可以使用 Gitee 镜像：

```bash
git clone https://gitee.com/liu-muyun/distill-novels.git ~/.codex/skills/distill-novels
```

重启或重新加载 Agent Skills 后，通过 `$distill-novels` 调用。

## 本地预处理

`scripts/prepare_sources.py` 会把多本小说转换为独立 UTF-8 文本和 `manifest.json`：

```bash
python scripts/prepare_sources.py ./books --output ./work/normalized
```

每本书都会获得基于内容生成的稳定来源 ID，并记录格式、字数、章节标题和章节识别置信度。

## 生成的知识库

根据所选维度生成 `worldbuilding.md`、`characters.md`、`plot.md`、`style.md` 等文件，同时保留：

- `sources.md`：来源、格式与提取质量
- `synthesis.md`：跨书共同点、差异和新的综合结论
- `craft-controls.md`：可用于原创写作与润色的参数化控制面板
- `books/<source-id>/`：每本书独立的概览与章节证据

## 原创与版权边界

本项目用于提取叙事机制、写作规律和私人研究笔记，不应生成原作替代品。请勿保存或传播长篇原文、标志性句子库，或发布由无权再分发的小说生成的完整知识库。处理第三方小说时，请遵守来源作品的版权和许可条款。

## 搜索关键词

小说蒸馏、小说分析、AI 小说写作、AI 写作助手、世界观生成、人物设定、剧情分析、文风分析、小说润色、伏笔管理、连续性检查、Agent Skills、Codex Skill、novel analysis、fiction writing、worldbuilding、character development、plot analysis、prose style、AI writing assistant、story bible。

## License

[MIT](LICENSE)
