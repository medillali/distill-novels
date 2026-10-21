# Distill Novels：多小说蒸馏与 AI 写作知识库 Skill

> 将一本或多本小说蒸馏为可复用的世界观、人物、情节、文风、叙事、对话、节奏、主题与连续性知识库，辅助原创小说构思、写作、润色和一致性检查。

[English](README_EN.md) · [GitHub](https://github.com/CloudLiu1008/distill-novels) · [Gitee](https://gitee.com/liu-muyun/distill-novels)

`distill-novels` 是一个面向 Codex 和兼容 Agent Skills 标准的小说分析 Skill。它支持从多本小说中分别提取有出处的观察，再进行跨书比较和抽象，最终生成可供 AI 写作助手按需加载的原创写作知识库。

## 本地增强版：长期小说资料库

本分支在上游 Skill 基础上增加持久存储和本地工具；上面的链接保留上游出处，不代表此分支已远程发布。

- **长期人物卡与剧情素材**：资料存入独立 `writing-vault`，保留来源、标签、收藏、人工笔记、历史版本；多个作品引用同一张卡的指定版本。
- **主线树与暗线网络**：卷、篇章、场景构成结构树；伏笔、误导、揭示、回收使用独立关系线，可交叉、多对多，记录读者和人物的认知差异。
- **Codex / ChatGPT 衔接**：导出带版本基线的工作包，回收修改时检测冲突；支持完整结构资料备份和恢复。
- **创作积累**：分别存来源研究、可复用机制、原创项目设定，并记录每次采用后的改写与反馈。

先看 [中文使用指南](docs/使用指南.md) 和 [模块验收状态](docs/module-status.md)。Python 3.10+，核心工具无第三方依赖；小说分析由宿主模型完成，脚本本身不会调用模型 API。

```text
python scripts/demo.py --output work/demo
python scripts/library.py --vault ../writing-vault init
python scripts/library.py --vault ../writing-vault status
```

打开 `work/demo/views/index.html` 体验离线剧情图。演示输出要求空目录，重复演示可改用 `work/demo-2`。真实资料库与示例分开保存。GitHub / Space 实际接入按用户选择留待后续；当前支持文件交接和本地同步基线登记，不会自动写入 ChatGPT 记忆。

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

## 在本地使用

在当前项目中，让 Codex 读取本仓库的 `SKILL.md` 即可按流程工作。无需先修改全局技能目录。本地工作区的 `AGENTS.md` 已指向工具和私人库。

如果以后希望在所有项目中通过 `$distill-novels` 调用，可将本增强版目录安装到宿主技能目录，再按宿主方式重新加载。不要用上游主分支覆盖尚未发布的本地增强版。工具代码与 `writing-vault` 始终分开。

## 本地预处理

`scripts/prepare_sources.py` 会把多本小说转换为独立 UTF-8 文本和 `manifest.json`：

```bash
python scripts/prepare_sources.py ./books --output ./work/normalized
```

每本书获得持久来源 ID，内容 SHA-256 单独表示修订，并记录格式、字数、章节标题和章节识别置信度。复用同一输出目录可增量登记；用 `--source-id <已有ID>` 明确添加同一作品的新修订，旧版本不会被覆盖。

## 生成的知识库

根据所选维度生成 `worldbuilding.md`、`characters.md`、`plot.md`、`style.md` 等文件，同时保留：

- `sources.md`：来源、格式与提取质量
- `synthesis.md`：跨书共同点、差异和新的综合结论
- `craft-controls.md`：可用于原创写作与润色的参数化控制面板
- `books/<source-id>/`：每本书独立的概览与章节证据

以上是原有独立报告模式。长期模式的 JSON 主档存放在私人库的 `library/`、`books/`、`history/` 和 `exchanges/`，详细格式见 [持久库工作流](references/library-workflow.md)。两种模式都保留来源证据；报告文件不替代持久主档。

## 开发验证

```text
python -m unittest discover -s tests -v
```

可选浏览器验收：安装有 Playwright 的开发环境运行 `node tests/browser_smoke.cjs`，使用本机 Edge 检查已生成演示。产品本身不需要 Node、Playwright 或网络服务。

## 原创与版权边界

本项目用于提取叙事机制、写作规律和私人研究笔记，不应生成原作替代品。请勿保存或传播长篇原文、标志性句子库，或发布由无权再分发的小说生成的完整知识库。处理第三方小说时，请遵守来源作品的版权和许可条款。

## 搜索关键词

小说蒸馏、小说分析、AI 小说写作、AI 写作助手、世界观生成、人物设定、剧情分析、文风分析、小说润色、伏笔管理、连续性检查、Agent Skills、Codex Skill、novel analysis、fiction writing、worldbuilding、character development、plot analysis、prose style、AI writing assistant、story bible。

## License

[MIT](LICENSE)
