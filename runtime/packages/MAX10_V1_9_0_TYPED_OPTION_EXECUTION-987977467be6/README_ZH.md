# Formal Max-10：Planner 短动作契约与执行索引续接

本包修复 R2 的 FROZEN_SELECTED_PORTFOLIO_SEMANTICS_MATERIALIZATION_INCOMPLETE。冻结 PRE 选中6状态/60分支，旧窄句式适配器只接好40分支；未提交任何 F0/F1 作业。当前两个契约在 FROZEN_OPTION_REGISTRATION.json 作为显式数据登记；代码不选择状态、任务、路径或候选。

后续轮在原同次 PRE 响应增加 execution_contracts 结构化附件，由强 Planner 声明完整终止语义。保留原动作序列、逐步 live menu、预算和 return-to-policy。不能表达的语义精确拒绝，不允许部分覆盖冒充完整覆盖。无需额外强模型调用、人工 parser 或新科研闭环。

原计划及回执全部保留。REGISTERED_H44_EXECUTION_INDEX.json 唯一指向新增执行目录；控制器、GPU、resident 证据读取、TRAIN 路径及监视窗口均跟随同一登记。原 SBATCH/分支意图存在即禁止材料恢复，避免重复执行。

VERIFY.py 运行契约和恢复测试；--server 复用真实当前 capture 生成完整60分支计划并装载实际 GPU dispatcher，但不提交、不调用环境或 provider。pre_checks.py 另验后续同次 PRE 的真实 schema/render。RUN.sh 使用已加载的项目 Python，验证后续接原 resident；已启动时请观察统一窗口，不重复启动。

外部使用 tee 时立即读取 PIPESTATUS[0]。shell 不启用 set -e/-u/pipefail。环境、服务、数据、模型、预算由原登记 authority 读取。Git 仅 staging cache，不执行 add/commit/push；Max10 是有效轮上限，既定连续不晋升停止规则保留。TRAIN_SELECT 用既定训练时评估切分；134 unseen/140 seen 最终 benchmark 不进入自适应闭环。
