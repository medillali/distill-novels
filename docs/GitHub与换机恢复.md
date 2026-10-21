# GitHub 保存与换机恢复

工具代码和私人创作资料使用独立仓库。小说原文不随资料库推送；源文件需另行保存。完整来源索引、研究卡、图、检查点和历史仍可从Git取回，无原文也能读取已完成的分析。

## 换到新电脑

登录有访问权限的GitHub账号，将两个仓库放在同一层目录，例如 `C:\Novel\distill-novels` 与 `C:\Novel\writing-vault`。使用Python 3.10或以上版本；工具核心只需标准库。

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

提交时明确选择资料文件；不要强制加入 `.gitignore` 排除的原书、缓存或机器配置。GitHub版本快照和ZIP备份互相补充，仍可运行：

```text
python scripts/library.py --vault ../writing-vault backup --output ../backups/library-new.zip
python scripts/library.py restore --file ../backups/library-new.zip --output ../restored-writing-vault
```

ZIP只写入库外的新文件，恢复到不存在的新目录。默认不含原文、Git目录与生成视图；视图可重建。

## 自动测试与双端衔接

工具仓库的GitHub Actions会在代码推送或PR时运行Windows、Linux两组标准库测试，也可手动触发。它只测试合成样本，不下载私人资料库。工作流基于GitHub官方 [checkout](https://github.com/actions/checkout) 与 [setup-python](https://github.com/actions/setup-python)，固定已核实的提交版本。

GitHub保存不代表ChatGPT记忆或Space已经同步。双端仍使用带基线的工作包导出与修改回收；Space接入需要单独完成。实际远程仓库地址和验收结果见本机工作台及后续远程验收记录。
