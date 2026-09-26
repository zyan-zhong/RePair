# 训练结果与既有 SELECT 接入核查

## 1. 真实训练包

输入 `/mnt/data/TRAINING_REVIEW.zip` 的 SHA-256：
`3be7c71c9e8dc71d0271e542d3074a9b24a211f89b5f44f51b6160b0146e3822`。

已使用原训练合同、阶段回执、artifact index、native-row loader、样本顺序与
formal run-plan/ledger 函数核对：13 个 optimizer steps、176 个目标 loss tokens，
所有 loss 与梯度范数有限。首末可训练参数哈希不同。候选仍是
`PI1_HUMAN_T2_DIAGNOSTIC_CANDIDATE`，promotion_eligible=false；归档 provenance
未完整的状态继续保留。本地未读取候选权重 tensor，也没有重新训练。

候选 adapter bundle：
`d1785b530043a1314d873bdfadd2c889bd1c073067d91a31a8429f52f6b60593`。

## 2. 既有 SELECT 不是空白

当前固定头 `629895d8ca9a7e5be2c9f2991c5e8c71d9ca3df3` 已有：

- `select_policy_runtime.py`：base/static LoRA 的具体服务身份；通用训练候选已受支持。
- `select_execution_identity.py`：condition/cell/runtime/request/response 身份链。
- `condition_run_schedule.py`：配对任务与 seed 网格；任务级统计单位。
- `episode_evaluator.py`：原环境调用、RAW prompt、严格 parser、预算与轨迹写出。
- `select_result_audit.py`：配对 schedule 一致性和每个 cell 的结果身份核查。
- `round_control/clean_execution_binding.py`：clean train-pool 的任务文件身份读取。
- 既有 Stage0 SELECT worker/server/retry/closeout 代码：其工程逻辑可以复用，
  但旧 pilot 的 task/adapter/服务名预设不能当作 clean 轮的新权威。

## 3. 找到的具体接入问题

旧 `build_select_execution_profile()` 固定返回 R0，验证器也要求 R0。
直接只换 adapter 路径不能保住本轮 I1。

这次保留旧工厂与全部旧 R0 行为，增加显式 I1 opt-in：

1. SELECT identity 与 I1 request-contract hash 必须同时绑定。
2. 请求仍由原 bound continuation factory 构造；不复制 schema 或生成 transport。
3. 仍由原 evaluator 构造 RAW prompt 并执行 strict-menu Runtime Core。
4. 原 result audit 增加 I1 wire / RAW prompt 复核。
5. 任意 I2、缺失 I1 authority、错误模型、seed 或解码参数均拒绝。

原核心工作树不改。独立 detached 工作树中只覆盖 3 个生产文件，另加 1 个测试文件。
不 commit/push；这是待固定头审核的补丁，不是已经发布的新执行版本。

## 4. 本轮 SELECT 协议提案

已冻结的是 TRAIN_SELECT pool 和 I1/RAW OFF/OFF 边界。训练计划没有给出完整
SELECT task×seed schedule，因此不能声称该 schedule 早已批准。

提案：全部 TRAIN_SELECT 条目、原顺序、原 E1 seeds (17,31,47,73,101)。
上游已冻结计数为 UPDATE2843、SELECT355、AUDIT355；若服务器 exact metadata
核验一致，将推导 1775 个 task-seed 配对、3550 个 condition episodes。
统计单位为 355 个唯一 task，不把五次重复当作五倍独立样本。

本包只生成 proposal，不启动评测。也不利用训练效果选择子集，不重划分数据。
元数据来自原 plan artifact index；不扫描“最新文件”。真实数据文件内容不在本地
附件内，服务器仍须核验这些 metadata 文件和候选 adapter 的实际字节。

## 5. 不能提前声称完成的部分

实际 LoRA 服务启动、完整 typed task/runtime/condition manifests、live driver
绑定和执行授权尚未完成。补丁本身尚未固定为提交。SELECT 明细不能进入研究
修复/训练数据面；诊断候选即使评测更好也不自动晋升。

## 6. 本地测试边界

本次修改后的 evaluation 子集 631 项通过；全仓运行 1925 项通过、5 项失败。
5 项都属于本地缺少外部 B0 snapshot 或未构建 native probe binary；在未修改的
629895d8 基线上逐项重跑，得到相同 5 项失败。没有删除断言、跳过测试或伪造
这些依赖。故不能把本次写成“全仓全过”。正式合并前仍需完整部署环境回归。

适配器的 actual-archive、metadata 正反路径与隔离工作树测试另外 15 项通过。
