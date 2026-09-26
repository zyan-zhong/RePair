# N.4 源码核验与状态纠偏

## 本次实际收到的材料

`R2_EXACT_PRODUCER_EVIDENCE.zip`：117,869 bytes，58 members，SHA-256 `6e78778d47e4fbc37fb3d0bd7a7b70ca494854ad25070e07601c4e5a1ab433ae`。
57 个导出项均为 EXPORTED_EXACT、无脱敏替换，逐项 export SHA 验证通过；其中 26 项另有 expected source SHA，也全部匹配。原输入 capsule 的 ZIP 字节没有包含在此导出中；包含其 33-member inventory 和源码投影。恢复前必须在服务器重新验证登记的 capsule ZIP 原字节及目录清单。

## 与原源码逐项对照后的四个修正

1. **此前“异常路径已经丢失”的判断不成立。** 原 `shard_worker.py` 的外层异常处理会写 `shards/<id>/PCHSI_V1232S_SHARD_FATAL_V1.json`，包含 `error_message`、完整 `traceback`、`assigned_global_ordinals`、`scientific_environment_execution_finished`。此前只看 gate failure reason，漏读了该文件。隔离执行原 worker 的 missing-capsule 分支，已直接重现其完整 filename publication。真实服务器 fatal 尚需 N.4 启动时读取；不把本地重现当服务器现场。

2. **不能直接把 K 的同轮恢复 producer 当 fresh-round producer。** 原 `submit_v1232k.py` 在 sbatch 前写出已登记 capsule；后来 V1233K 重建的 current runner 指向 current root 的同名 capsule，却未复用该生成步骤。N.4 不复制旧目录，直接引用先前 SHA-bound 的原输入 ZIP。仅当真实 fatal 的 filename 精确匹配当前 runner 的缺失 capsule、且仍未产生任何 allocation/科学输出时才允许执行。

3. **此前“ordinal=0 自动兼容原 worker/finalizer”的表述错误。** 原 worker 明确拒绝 `fresh_attempt_ordinal<=0`；原 finalizer 还用 capsule 的旧 `round_id` 构造 request，而且没有同步重绑正号 attempt 的 schedule。原代码的零号拒绝、旧 round request 冲突已本地复现。N.4 增加共享 request/schedule binder：原 capsule 不改，worker/finalizer 都消费当前独立 request，并使用同一个 native execution-attempt identity builder。

4. **此前把 Q completion 等同完整 Analyzer/campaign completion 的说法过强。** `vendor/V1232Q/v1232q_driver.py` 的真实终点是 local-wave + canonical ACT3 group prep；censored 情况可返回 20；它发布下一阶段指针，但不调用完整 G-A2/G-A3/C/P/X、PRE/POST 或 trainer。N.4 明确不把该终点写成完整层级分析或 max-10 release。

## 总账复核方式及对应历史资产

本轮保留并机械读取最新完整账本全部 4,286,346 bytes、159,380 行；生成完整标题索引（5,525 项），按版本顺序核对直接关联段落和当前源码。这里不声称对每条无关历史训练日志逐字完成新的独立科学审核。

重点回溯：V1231 的 Memory-aware rollout 原生接口；V1232K/L/M 的正号 attempt 和 finalizer identity 修复；V1232Q/R 的 local-wave censoring、ACT3 grouping 及下游职责；V1233I 的 NO_TRAIN 与 Memory carry-forward；M/N/N3 的诊断器字段错误、错误 input closure 与撤回记录；Stage6AL/AN 的 verified strategy/native-label gate 和部署 action-only 边界。

历史资产复用保持：原 episode evaluator、policy Memory adapter、source capsule、runtime/service launch、registered TRAIN_UPDATE schedule、native universe/cohort/handoff、原 V1232Q。没有新 trainer、没有新 Analyzer、没有重跑 F0/F1/PRE/POST。

## N.4 修改范围

原 producer 只改两个文件：worker 和 finalizer。新增 `fresh_round_contract.py` 为两者共用的 native request/schedule 边界。

控制面 `recover.py` 消费 exact current authority、原 fatal、原 capsule/source hashes；`native_preflight.py` 调原 native request/task/schedule/allocation builder；`analyzer_preflight.py` 调原 Q 的 discovery/API preflight；`supervise.py` 只监督一次 array + 至多一次原 Q entry；状态文件和日志不需要人工触发才能推进。详细 unified diff 在 `EXACT_PRODUCER_DELTA.patch`。

不恢复 N.2 的 41 个候选，不把 old cell terminal/readiness/probe/attempts 变成当前输入。当前 request 原字节不变。当前 policy/Memory/train manifest/seed/token budget/profile 均与 capsule 严格匹配；以后 policy 或 Memory 变化时应使用原生 fresh builder，而非永久套用本次同 parent/snapshot 的兼容桥。

## 新旧执行身份分开

- 原 R1、失败的 R2 array 及所有诊断证据：保留。
- 科学 R2 request/attempt ordinal：保持原 authority，不另造 R3，也不偷偷加一次 valid round。
- infrastructure recovery root：以 request/fatal/capsule/source/settings 摘要派生，与旧运行输出分开。
- submission intent/receipt：一次提交；模糊发送状态不能再次发送。
- 新 allocation/readiness/episode terminal：只能由新执行自行产生。

## 测试证据与限制

原代码回归 RED：3 failed / 1 passed（ordinal0、共享 schedule、新 round binding）。
新增控制生命周期 RED：3 failed / 3 passed（启动失败 containment、handoff publication race、失败 release 的重启处理）。
真实原 finalizer 使用新 request 时的 `GLOBAL_REQUEST_BYTES_CHANGED` 已在隔离 fixture 中重现。
修正后的 native request、manifest loader、schedule、finalizer 联合测试支持零号和正号 attempt，产出当前 NEW_ROUND handoff，并保持旧 binding bytes 不变。

这些都是隔离的合成测试任务，不是 ALFWorld 科学效果数据。调度器/进程发送边界在测试中 mock，模型和 Provider 未调用。完整真实服务器仓库回归与 GPU live recovery 尚未执行。

## 当前完整系统状态（不能向上夸大）

R1 分段科学链及 typed NO_TRAIN 有既有记录；R1 close/R2 request/首次 array 提交有既有记录；R2 有效全量 rollout 和完整层级 Analyzer re-entry 尚未证明。当前 Memory 是 carry-forward，不是负面/Neutral 证据治理更新已完成。Stage6AN 表示存在，但真实 strategy loss → task-policy optimizer → OFF/OFF 增益仍未证明。

N.4 只推进 R2 producer 与原 Q local entry；正式一次启动循环仍需把已有 group/Planner/Memory/TRAIN/NO_TRAIN/stop/recovery 组件接入同一 resident、完成隔离集成测试、正式版本冻结与服务器/远端一致性核验。不是三套新科研 loop，也不能把“没有询问人工 retry”当作“已经成功自主恢复”。

## Git 边界

本轮只读查询 remote integration ref 为 `61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a`。导出 producer 登记的 execution worktree 使用 `ea091bcdc2a9bcd239ec57d40dec423003ff68a8`。二者是不同来源/执行身份，不声称整个服务器与 GitHub 已对齐。N.4 不修改这些 worktree 或 remote ref；后续需要明确整合 durable source delta，而非把大量 runtime outputs 塞入 Git。
