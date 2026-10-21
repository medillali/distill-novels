# GitHub 保存与换机恢复

工具代码和私人创作资料使用独立仓库。小说原文不随资料库推送；源文件需另行保存。完整来源索引、研究卡、图、检查点和历史仍可从Git取回，无原文也能读取已完成的分析。

- 工具：[medillali/distill-novels](https://github.com/medillali/distill-novels)，私有。
- 个人资料：[medillali/writing-vault](https://github.com/medillali/writing-vault)，私有。
- [远程验收记录](testing/2026-10-22-github-acceptance.md)：GitHub重新克隆、资料恢复与双平台自动测试。

## 换到新电脑

登录有访问权限的GitHub账号，将两个仓库放在同一层目录，例如 `C:\Novel\distill-novels` 与 `C:\Novel\writing-vault`。使用Python 3.10或以上版本；工具核心只需标准库。

在选定的短目录中运行：

```text
git clone https://github.com/medillali/distill-novels.git
git clone https://github.com/medillali/writing-vault.git
cd distill-novels
```

两个仓库都需要授权账号登录。根工作区的 `novel.cmd` 是本机便利入口，未包含在上述仓库中；换机可直接使用下列Python命令。

从工具目录执行：

```text
python -X utf8 -m unittest discover -s tests -v
python scripts/library.py --vault ../writing-vault status
python scripts/library.py --vault ../writing-vault search --type character
python scripts/library.py --vault ../writing-vault views
```

打开 `writing-vault/library/views/四书实测.html` 可查看已保存的开篇研究快照。日后有新卡或修改，以JSON主档与新生成目录为准。不要把这个快照当作持续自动更新的页面。

Windows未启用长路径支持时，过深目录可能使来源的SHA-256文件名超出系统路径限制。本机235字符路径写入成功、275字符路径失败；应把克隆和资料库放在较短目录，不要层层嵌套测试副本。本次没有修改系统长路径设置，也不宣称已实现任意长路径支持。

## 继续阅读原书

读取 `writing-vault/exchanges/runs/` 中的检查点，保留原有来源ID、修订和已读章节。四本当前已读16段，其余待读范围已经登记。重新找回原书后，先核对版本与哈希，再将原文件放入本地 `private-sources` 并恢复规范化文本；不要用不同版本悄悄替换已有证据，也不要重新初始化资料库。

## 日常保存

保存卡片会写本地JSON与版本历史；不会自动提交或推送Git。完成一批工作后，先校验和查看diff，再提交并推送。两台设备应先拉取再修改，避免同时写同一主档；遇到Git冲突要核对两边资料，不能整库覆盖。

```text
python scripts/library.py --vault ../writing-vault status
git -C ../writing-vault status
git -C ../writing-vault diff --stat
```

本机工具仍在 `codex/persistent-fiction-library` 分支，上游保留为 `origin`，个人仓库为 `personal`。工具提交后明确运行 `git push personal HEAD:main`；不要向上游推送私人改造。资料库使用 `main` 分支和 `origin`，提交后运行 `git -C ../writing-vault push origin main`。从上述个人仓库新克隆的工具则直接使用 `main` / `origin`。

提交时明确选择资料文件；不要强制加入 `.gitignore` 排除的原书、缓存或机器配置。GitHub版本快照和ZIP备份互相补充，仍可运行：

```text
python scripts/library.py --vault ../writing-vault backup --output ../backups/library-new.zip
python scripts/library.py restore --file ../backups/library-new.zip --output ../restored-writing-vault
```

ZIP只写入库外的新文件，恢复到不存在的新目录。默认不含原文、Git目录与生成视图；视图可重建。

## 自动测试与双端衔接

工具仓库的GitHub Actions会在代码推送或PR时运行Windows、Linux两组标准库测试，也可手动触发。它只测试合成样本，不下载私人资料库。工作流基于GitHub官方 [checkout](https://github.com/actions/checkout) 与 [setup-python](https://github.com/actions/setup-python)，固定已核实的提交版本。

GitHub保存不代表ChatGPT记忆或Space已经同步。双端仍使用带基线的工作包导出与修改回收；Space接入需要单独完成。本次本机GitHub CLI已验证两个私有仓库可读写；当前GitHub插件读取新私库返回404，尚未验证其权限。后续在ChatGPT直接读取仓库时，需要为所用连接开放这两个私有仓库的访问权限；文件式工作包不依赖该连接。
