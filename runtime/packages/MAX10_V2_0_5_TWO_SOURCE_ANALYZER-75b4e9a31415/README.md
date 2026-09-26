# Analyzer two-source execution

本轮 R5 保持已有串行运行，不重启、不重复采集。用户批准的两路并行从登记的 activation_round_index 起适用。

并发数由 AUTHORITY.json 的 parallel_policy.max_concurrent_sources 登记为 2。L 的同源 A0/A1 串行；G 的同组 A2/A3 串行；C/X 的同组条件顺序不变。G 完成后才 C，再 X，再现有 PRE/F0F1/POST/条件训练和轮次交接。原请求字节、logical id、模型、token预算、retry预算、结果校验、隔离、选拔和记忆闭环均沿用已封存 V2.0.4。

每个来源在独立 Linux fork 进程中运行。一个 resident 协调器限制并发、按原序合并、维护统一进度。global stop 停止新准入，已发请求完整收尾，Local 保留 typed terminal manifest；未知 partial 不盲重发。

VERIFY_PARALLEL.py --server：包 SHA、新测试、历史真实 Local/G/C/X 零发送等价重放、现有固定接口校验。Linux 服务器验证是必须项。
RUN_PARALLEL.sh：先验证，再登记后台一次性切换器；当前轮继续不变。只有后续轮完整 Local terminal、registered PID/argv/round/binding 一致、无子进程、无未完成文件写入时，才安全交接给新入口。若 campaign 按原规则结束，记录无需激活，不强制创建下一轮。已有任务无需重新上传、重复运行或手动介入。

统一观察口保持原路径。parallel_status.py 在原窗口基础上显示 pending/active、两路 source/stage/等待时长。配置已登记不等于已经启用，实际状态以 ACTIVATION_STATUS、HANDOFF_RECEIPT 和 ANALYZER_PARALLEL_PROGRESS 为证。

Git staging only；无 commit/push。科研数据划分、BENEFIT-only、OFF/OFF、1 paired TRAIN_SELECT seed、5 paired causal seeds、Max10/已有早停均不改变。
