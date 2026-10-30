# 每周总结调度

用户已选定每周日北京时间 21:00，只总结已经收集的论文。收集和删除始终由用户手动触发。

自动安装尝试返回 Windows Access is denied，尚未创建任务。
请右键项目根目录 install-weekly.cmd，以管理员身份运行一次；安装脚本遇到已有同名任务会停止，不覆盖。
安装完成后可在 Windows 任务计划程序查看 AI Paper Agent Weekly 的下次运行时间。

本机时区已核验为 China Standard Time。任务触发时间携带 +08:00，允许错过计划后补跑，
同一资料库不并行执行；使用当前账户 InteractiveToken，仅该账户已登录时可运行。
程序与日志、缓存和临时文件均指向 D:/codex/projects/ai-paper-agent。
需先通过 start.cmd 的配置菜单保存自己的 DeepSeek API Key。

任务执行 docs/run-weekly.ps1，隐藏窗口，调用本地应用 catch-up，并保存日志到 library/logs。
周日 21:00 汇总当前自然周到该时刻的已有材料。之后新增的同周材料会在下次任务中补充报告并保留旧版。
已有报告会去重；最新周报主动删除后不自动重建，手动 weekly --force 可以恢复。
删除旧版周报不会影响现存新版或后续补充。

可手动运行 start.cmd catch-up；若没有待总结材料，不调用模型。
关机时不会运行；恢复后任务计划补跑。停用或删除该任务即可停止自动总结。
