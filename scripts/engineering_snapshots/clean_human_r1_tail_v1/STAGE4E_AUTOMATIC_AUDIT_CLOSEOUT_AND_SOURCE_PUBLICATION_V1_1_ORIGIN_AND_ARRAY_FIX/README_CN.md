# Stage4E V1.1：origin 恢复 + 四个独立单卡作业 + 原收尾发布

## 当前唯一推荐入口
在原 pchsi_scripts 下解压本包，在现有 tmux 中运行：

```bash
bash ./RUN_MIGRATE_SINGLE_GPU_ARRAY_AND_FOLLOW.sh 156834
```

不要先手工取消 156834，不要并发运行旧 Stage4E driver，也不要同时重提旧四卡包。
本入口会确认 156834 属于当前用户、原 V1.3 package、仍为 PENDING、未 requeue，
然后使用 `scancel --state=PENDING 156834` 精确取消；必须获得“未启动即取消”的 accounting
证据才会提交新 array。如果此时已经 RUNNING，停止迁移，不杀正在执行的科研任务。

## 实际执行顺序
1. 校验本包、原 Stage4D 源码与上游冻结身份。
2. 校验 active checkout 的 fetch 和 push 地址，支持固定目标仓库的官方 SSH 443 URL。
3. 原独立 clone 若仅停在旧 origin gate 后，则核验精确 HEAD/tree/branch/clean 状态，
   完成原 clone 的 remote/anchor 初始化；不 reset、不删除、不修改 active checkout。
4. 取消未启动旧作业；冻结原 receipt prefix 与 ordinal % 4 分片计划。
5. 一次 sbatch 提交 array 0–3，**四个独立单卡 allocation，最多四个并发**，不要求同节点同时空出四卡。
6. 原生 Stage4D V1.3 shard_worker / execute_shard / vLLM command builder 原样复用。
7. 在服务器控制会话同步执行独立 clone 的源码整合和原全仓回归，同时数组作业自行排队/执行。
8. 逐个确认 array element COMPLETED 0:0 和对应原 shard status；不把 array master 的状态当成四个结果。
9. 仅对正常 graceful partial 的未完成 shard 允许最多一次自动补提交；失败/超时/缺记录不自动重跑。
10. 四个完整 shard 的精确序列、覆盖、重复检查通过，调用原 consolidate_shards。
11. 原 Stage4E 审计、描述性配对统计、诊断候选保留 parent、下一轮交接、原子发布。

## 不变的科学内容
授权 978ab393…、binding 4ab794…、readiness 3958cacc… 不变；355 tasks × 5 seeds × T0/T2 = 3550 cells。
已完成的 prefix 由原 hash-chain loader 与冻结 schedule 自动核验，不硬编码 102。
T0 和 T2 仍在同一个 shard、同一个单卡 server 上依次执行；不同 pair 才跨 GPU 并行。
不改变环境步预算、模型、adapter、I1、完整菜单、Memory OFF 或 Harness OFF。
不新增新的 evaluator、训练器、memory 或判胜逻辑。

## 路径
既有执行、结果、control、日志和原运行包路径全部保留。
新调度记录写在原 execution root 下 `parallel_v1/independent_jobs_v1/`；
shard 数据继续是 `parallel_v1/shard_0` 至 `shard_3`；
日志继续位于 `new_human_pi1/logs/stage4d_existing_select_live_execution_v1/`，
数组日志命名为 `full_select_array_<array_id>_<shard_id>.out/.err`。
最终归并后仍是 `execution/t0` 与 `execution/t2`。
缓存仍位于原 `runtime_cache/stage4d_existing_select_live_execution_v1/<job>/shard_<id>/`。

## Slurm / 环境
每个 job 使用 `gpu_a800`、1 GPU、03:30:00；没有显式 CPU 数量或内存申请。
保持 `--export=NIL`，显式 PATH、禁用 usage stats、run 分区缓存、短 TMPDIR。
package 路径通过脚本参数传递，不再从 Slurm spool 中 `$0` 的目录猜测。
不自动使用未核实权限的 hp_a800，不新增节点黑名单，不调低显存阈值。

## 断线恢复与不确定性
整个控制入口在服务器同步运行；应保留在 tmux 中。聊天助手不进行后台监控。
重新运行同一入口会读取已保存 plan / submission receipts，不重复提交已知 job。
若 sbatch 返回不确定，且只存在 intent、没有 job-id receipt，则停止，绝不猜测后重投。
如果原生全仓测试失败，已提交的单卡 jobs 不会被误杀；日志与 submission receipt 保留。
原单作业跟进入口保留兼容，但当前数组迁移不要使用它。

## 发布和科研结论边界
只有完整原生回归和 3550-cell 审计都通过，才会自动进行原有 FF-only atomic push。
不 force-push，不绕过 origin 白名单，不改活动工作树。
T2 仍为 diagnostic_only / promotion_eligible=false，正的描述性差值不改变冻结资格。
Strong-primary 交接仍受已注册 takeover metrics、预算和 actor/model binding 约束；本包不制造缺失数据。
完整源码地图 != 已验证整个自主循环。过滤导出缺少的 schema、历史外部依赖和全量数据，仍必须在服务器验证。
