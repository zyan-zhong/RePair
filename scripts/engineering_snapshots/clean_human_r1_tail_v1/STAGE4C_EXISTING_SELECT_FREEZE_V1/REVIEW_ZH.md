# 当前 SELECT 审核与冻结说明

## 实际上传材料

已读取 `SELECT_PREFLIGHT_REVIEW.zip`，SHA-256 为 `e8263e5a9604a85d831187938b6938f721f76e9163da6f5025398d1c32d4db27`。9 个 ZIP 文件中，8 个被文件索引引用的成员均与 SHA-256 一致。网格、模型、训练回执与 metadata 引用交叉一致。详细数值保存在 `UPLOAD_REVIEW_FINDINGS.json`。

当前训练候选仍是 `PI1_HUMAN_T2_DIAGNOSTIC_CANDIDATE`，adapter bundle 为 `d1785b530043a1314d873bdfadd2c889bd1c073067d91a31a8429f52f6b60593`。本地未读取服务器权重；上传的服务器回执记录了真实文件核验。本包在服务器执行时继续调用既有字节校验器，不加载模型。

## 代码范围

当前四文件 overlay 已经应用并在服务器运行 631 项 evaluation 测试。本包不重新打补丁、不增加第五个生产改动。只核验并提交已有 overlay：

- `src/pchsi/evaluation/select_execution_identity.py`
- `src/pchsi/evaluation/episode_evaluator.py`
- `src/pchsi/evaluation/select_result_audit.py`
- `tests/evaluation/test_select_i1_explicit_binding.py`

本地恢复代码后核对 1,431 个源码树路径，复现的文件内容闭包为 `7416e538d99df0960da60a964ea142117f791e5e4b21f4e13a97511c07c80a4c`，与上传回执一致。父提交始终是 `629895d8ca9a7e5be2c9f2991c5e8c71d9ca3df3`。旧 R0 SELECT factory、历史代码、训练结果和原工作树保留，不再次合并或 cherry-pick 历史资产。

全仓回归通过后，在原已存在的独立 detached worktree 创建提交，并创建由源码闭包推导的本地 review ref。Git bundle 从该实际 ref 创建并验证，避免裸 SHA 不能作为 bundle ref 的旧错误。此包没有任何 push 操作，main 不更新。

## 本次待批准协议

完全采用上传提案中的 355 个 TRAIN_SELECT tasks、原 metadata 顺序、5 个 seeds（17、31、47、73、101），两个条件 T0 与 T2。因此有 1,775 个 task-seed 配对、3,550 个 condition episodes。

保留 I1、RAW、Memory OFF、Harness OFF、静态模型身份、30 个环境步、60 个 policy attempts、3 个连续未执行尝试上限。TRAIN_UPDATE/SELECT/AUDIT 的 metadata 身份不改变。

在本次决策文件中补充明确的统计解释（不是声称旧提案已有完整统计计划）：每个 task 内先平均 5 个配对 seed 的终局成功差，再对 355 个 task 等权汇总。种子重复不是独立任务。终局成功、成对胜负平、动作合法性与格式错误、步数/调用数和终止原因作为描述性指标。这里不新增显著性检验、置信区间实现或确认性结论。

基础设施缺失保留缺失，不能按任务失败计分；完整结果要求完整网格。本协议批准不授权改策略、自动重跑、不完整结果隐藏、候选晋升或资源执行。诊断候选即使得分更好也没有自动晋升资格。

## 原组件继续使用

固定头的 Stage1 runner 裁决已要求使用 `run_single_episode(config, dependencies)`。本包调用原训练/数据核验与 artifact index，不复制 evaluator、PolicyClient、I1 builder、LoRA server 或结果审计。

已有 live source 位于 `scripts/engineering_snapshots/stage0/human_pilot_stage0_offoff_execution_and_closeout_v1_9/stage0/`，包括 live_runner/runtime_server/receipts/attempt_recovery 等。旧 server 的模型数量和旧任务常量带有 pilot 假设，不能把文件照原默认值直接执行。本包把这些确切源码及其哈希随交接输出保存；后续只做 clean 输入适配。

## 回归验证边界

本地对同一 overlay 执行全部仓库测试得到 1,929 passed、1 failed。唯一失败是 `test_b0_exact_dependency_binding_is_rehashable`，因为容器没有用户服务器上冻结的 B0 外部快照。未修改的原始父提交执行同一测试也因相同目录不存在而失败。相关原始日志保留，不把此结果写成全仓 PASS。

四个与原 native 默认 binary 缺失有关的旧失败，在使用原 Makefile 的 `all` 目标构建后已消除。只编译默认 fail-closed binary，不构建/执行真实 adversarial probe payload。全仓测试自身会执行原有 describe/denied-execute 断言。

服务器入口先检查原 B0 快照和 A9 文件，再运行完整 pytest；任何失败都阻止提交与协议冻结，不跳过断言、不重建或替换科学依赖。此处依赖读取仅为测试，不把 pilot Memory 暴露给当前评测策略。

## 自动循环接口与尚未完成内容

`NEXT_STAGE_BINDING.json` 携带固定头/tree、本地 ref、协议文件/domain 哈希、候选 adapter、池 metadata、artifact index 和代码 bundle 身份。后续控制器应读这些机器引用，不按目录时间选文件、不人工抄哈希。ZIP 是审核副本，不是 Strong 主循环必须等待人工上传的接口。

本包没有调用 Strong Planner；当前精确决策批准来自 Human Primary。未来角色切换应经原 authority resolver 和接管条件，不能自行把 shadow 提升为 primary。本包支持读取决策文件，但没有声称完整 Strong 计划生成、执行授权及跨轮调度已部署。

本次成功后的真实下一步为 `EXISTING_SELECT_LIVE_BINDING_AND_EXECUTION_AUTHORIZATION`。仍需生成 typed server/policy/condition/schedule manifests、绑定 clean 环境，以及独立资源授权；这不是本包已经完成的 live execution。归档 provenance 仍不完整，训练/晋升都不授权。
