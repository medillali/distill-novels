# 长期小说资料库实施计划

> **执行方式：** 本会话使用 executing-plans，逐项完成测试与实现；结束时做一次独立全分支审查。用户已在 2026-10-22 回复“请你开始”，无需再次确认设计。

**目标：** 提供可实际运行的持久人物/场景库、剧情树与暗线图、版本化双端交换和备份恢复。

**架构：** Python 标准库负责数据与命令行，宿主 Skill 负责文学分析。JSON 是主档，Markdown/SVG/离线 HTML 是派生视图；私人资料独立于代码仓库。

**技术：** Python 3.10+、unittest、JSON、SVG、原生 HTML/JavaScript；不引入服务器或付费 API。

## 全局约束

- 设计依据：`../specs/2026-10-22-persistent-fiction-library-design.md`。
- 开发目录为本任务独立克隆，分支 `codex/persistent-fiction-library`；不修改既有 Novel 框架文件。
- 稳定身份与内容版本分开；人工笔记、旧版本和项目引用不可静默丢失。
- 更新先校验、加锁、记录事务，再原子替换；恢复可重放回滚日志。
- 原文、缓存、机器配置不进入代码仓库或默认备份。
- Windows 命令使用 `python`；本环境验证使用已发现的 Python 3.12.14 绝对路径。
- 新模块注释和用户说明中文；既有 Skill/参考英文规范保持一致并增加中文操作指南。

## 文件与接口

| 文件 | 职责 |
|---|---|
| `scripts/prepare_sources.py` | 兼容旧入口；稳定来源、修订、章节定位和 EPUB spine |
| `scripts/fictionlib/storage.py` | 安全路径、文件锁、事务、历史版本、JSON 编码 |
| `scripts/fictionlib/vault.py` | 来源、资产、项目、检索、使用反馈、运行检查点 |
| `scripts/fictionlib/graph.py` | 图校验、保存、Mermaid/SVG/HTML 渲染 |
| `scripts/fictionlib/exchange.py` | 工作包、三方合并、备份恢复、Space 同步映射 |
| `scripts/library.py` | 自说明 CLI，JSON 输出与非零错误码 |
| `tests/test_*.py` | 上述模块的行为回归与端到端测试 |
| `examples/` | 完全原创的小型来源、资产、剧情图与演示命令 |
| `references/library-workflow.md` | 宿主分析、数据格式、调用与双端操作 |
| `docs/使用指南.md`、`docs/module-status.md` | 用户入口、模块证据与未接入项 |

### Task 1：来源与修订

接口：`prepare(inputs, output, source_id=None) -> dict`；`extract_epub(path) -> str`；结果 sources 含稳定 source_id、aliases、revision、revisions、chapters。

- [x] 先写 `tests/test_sources.py`，覆盖重排/追加/重复导入、指定修订、旧 manifest、章节偏移、UTF-16 BOM、EPUB spine 与缺失成员。
- [x] RED：`python -m unittest discover -s tests -p test_sources.py -v`。
- [x] 实现内容 SHA-256、登记型 ID、追加 manifest 与版本文本；EPUB 使用 container→OPF→spine 定位。
- [x] GREEN：执行同一命令，旧来源必须满足 `before['source_id'] == after['source_id']`，旧修订可回读。
- [x] 提交来源修复和测试，记录结果。

### Task 2：持久资料库

接口：`Vault(path)`；`Vault.init(path)`；`import_sources(manifest)`；`put_asset(data, base_revision=None, generated=False)`；`get_asset(id, revision=None)`；`search(...)`；`create_project(title)`；`use_asset(project_id, asset_id)`；`record_usage(...)`；`checkpoint(...)`。

- [x] 先写 `tests/test_vault.py`，覆盖重复素材、同名不同书、证据校验、人工笔记、并发旧版本、跨项目采用、归档项目后资产仍在、事务中断恢复。
- [x] RED：`python -m unittest discover -s tests -p test_vault.py -v`。
- [x] 实现锁、日志回滚、原子文件替换；资产写入时复制旧版本到 history，保护用户字段。
- [x] 检索按关键词、类型、标签、收藏、来源和项目组合筛选；使用记录固定资产版本，工作检查点固定来源修订。
- [x] GREEN：运行测试，验证 `get_asset(id, 1)` 保留旧内容，项目 A/B 的采用独立。
- [x] 提交资产基础与测试。

### Task 3：剧情图与离线视图

接口：`validate_graph(graph, vault=None)`；`save_graph(vault, owner_kind, owner_id, data, base_revision=None)`；`render_graph(graph, destination)`。

- [x] 先写 `tests/test_graph.py`，覆盖父子环、悬空边、叙述时间、暗线多对多、引用错误、缺失证据、特殊字符。
- [x] RED：`python -m unittest discover -s tests -p test_graph.py -v`。
- [x] 实现结构父子与关系边分离，验证 threads 和 coverage；版本保存沿用事务层。
- [x] 实现树/关系网、暗线筛选、节点详情、章节段筛选、缩放；输出独立 HTML、SVG 和 Markdown，无外部 CDN。
- [x] GREEN：运行测试并实际打开原创示例，确认筛选和节点详情可用。
- [x] 提交图模块与测试。

### Task 4：双端交换、备份与恢复

接口：`export_bundle(vault, destination, asset_ids=None, project_id=None)`；`import_changes(vault, changes, apply=False)`；`backup(vault, zip_path)`；`restore(zip_path, destination)`。

- [x] 先写 `tests/test_exchange.py`，覆盖往返、同字段冲突、不同字段合并、过期哈希、重复回收、新卡片、损坏备份、路径穿越和空目录恢复。
- [x] RED：`python -m unittest discover -s tests -p test_exchange.py -v`。
- [x] 输出有版本/哈希的 bundle/context/changes 模板；回收比较共同版本、本地、远端，冲突时整包不应用。
- [x] 用清单与 SHA-256 校验备份；恢复仅接受新目录，完成验证后再发布恢复结果。
- [x] 记录 Space 页面 ID、同步基线、页面哈希和变更游标；宿主使用真实 Pages 工具读写，不在 Python 中伪造平台接口。
- [x] GREEN：运行测试，要求恢复后主档哈希一致，并验证原始小说未进入默认备份。
- [x] 提交交换模块与测试。

### Task 5：CLI、Skill、示例与验收

- [x] 先写 `tests/test_cli.py`：从空目录初始化→来源登记→素材保存→项目采用→图渲染→导出→回收→备份→恢复。
- [x] RED：`python -m unittest discover -s tests -p test_cli.py -v`。
- [x] CLI 用 argparse 子命令映射前述接口，错误写 stderr 并返回非零；dry-run 明确报告未应用。
- [x] 更新 SKILL 的入口路由与渐进式参考，增加真实可运行的原创样例和中英文说明。
- [x] GREEN：`python -m unittest discover -s tests -v`，运行 Skill 验证器与 `git diff --check`。
- [x] 初始化用户空资料库，不填入虚构的蒸馏成果；演示资料留在独立演示目录。
- [x] 独立代码审查与必要修复；记录设计/本地验证/GitHub/Space/真实小说质量的分层状态。

## Review Focus

重点审查事务中断、历史修订、输入路径、证据跨书污染、生成更新对人工字段的保护、双端冲突的原子性、备份完整性及图渲染内容注入。不要把结构测试当作文学分析质量验证。

## 执行记录

记录位于 `docs/implementation-log.md`；每个任务完成后写入测试命令、结果及有证据的决策。
