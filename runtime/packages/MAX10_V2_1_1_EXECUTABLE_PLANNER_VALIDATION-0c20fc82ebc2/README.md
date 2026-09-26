# V211：公共持有判据与 Planner 执行覆盖修订

沿用 V208 的单轮验证入口、PRE/F0F1/POST、条件训练、Dual-View、OFF/OFF、记忆与论文导出接口。修正公共菜单 move 命令的持有判断，澄清 Planner 后续阶段可以依新观测执行，在最终 PRE 中披露实际阶段覆盖。没有新增 DSL、任务求解器或运行时强模型 agent。

复用 V210 已验证的 json_object 生成与严格本地校验、等价归一化和每来源一次格式纠正；恢复读取持久化的具体错误，使纠正 request identity 在首次失败和缓存恢复时一致。完整原始证据、历史结果和 immutable 包不改写。

VERIFY.py 校验包 SHA 并运行全部回归。RUN.sh --preflight 在登记环境内检验真实 native PRE/worker/training 接口，且不发送模型请求；RUN.sh --run 执行一轮。默认 --preflight-and-run。操作者 shell 不启用 set -e/-u/pipefail，tee 后显式读取 PIPESTATUS[0]。服务器启动使用按已登记环境生成的 RUN_REGISTERED_ENVIRONMENT.sh。

本轮 reuse R5 rollout/Analyzer，最多一次独立验证，formal round 增量为 0。父模型和来源先由 authority/SHA 校验；不重跑 Analyzer/rollout，不把 reused seeds 当作新独立样本，不人工选择任务或候选。所有来源由 Planner 审核并冻结新 PRE，之后按新计划运行因果验证。

终局稳定 4/5 和 B/H/N/U 不变；P+ research-only；仅稳定 Benefit 可进入现有训练链。OFF/OFF 使用登记 TRAIN_SELECT 1 个配对 seed，成功数优先、持平比较既有目标条件比例。最终 134 unseen / 140 seen benchmark 保持封存。没有强制训练或晋升，也没有启动额外正式轮次。

使用已有统一状态入口观察本轮。Git 交付只有 staging cache/delta，无 add/commit/push。新方案的任务收益以真实 verifier 回执为准，代码和预检通过不等于已获得 Benefit、训练或晋升。
