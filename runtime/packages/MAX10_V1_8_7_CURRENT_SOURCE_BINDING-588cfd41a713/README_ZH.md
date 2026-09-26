# V1.8.7 本轮 source condition 与 actor provenance 接线修复

仅复用已登记 V1.8.6/V1.8.5/V1.8.2。原包和科研 receipt 保持原字节，不复制科研框架。

总账 V123 已规定：旧 episode 未重复存储 policy_condition_id 时，从当前父模型与唯一 continuation profile 推导 source_policy_condition。用本轮 request 的 execution_profile_sha256 定位 producer 的 ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json，再核对 accepted PRE、父模型、round、actor runtime 和原始 request wire。保留 Analyzer state ID，以既有桥接关联 native replay fingerprint。原五文件 attempt bundle 不改写。

H4.4 的历史 actor commit 核对改用已登记的 current source reconciliation：按原 manifest 有限读取全部 native Python 文件，与登记的 commit blob 和实际 checkout 逐一核对；仅允许 authority 中已登记的非 actor 源码差异。旧 H4.4 provenance 文件不变，当前 proof 写到本轮 plan/authority。Memory overlay 与原 replay/预算/游戏文件校验保留。

当前 11 个选中候选都是 EXECUTABLE_EXACT_ACTION。原 H4.4 只接了短序列，导致全体 NOT_A_REGISTERED_SHORT_OPTION。现在复用 native validate_executable_exact_candidate_v1：保留 candidate 原文和 SHA，验证完整 live menu SHA，执行一个已登记动作且扣一步环境预算，然后冻结父策略续跑。精确动作不套用搜索目标可见即停的逻辑。短序列执行保持原样；整个冻结 portfolio 有未支持项则在环境执行前停止，不替换候选。GPU entry 显式带入相同 adapter，并以原生分支流程做无真实环境/模型调用回归。

VERIFY.py --server 走真实续跑调用链，禁止 provider 调用，复用全部已接受阶段，运行隔离 H44 child 完成所有选中源的 capture、TRAIN_UPDATE 资产校验、replay registration 和 branch plan。TESTS.py 验证不同父模型/profile 及冲突拒绝。fresh-unzip 日志随交付记录。

在 AUTHORITY.host 上运行 bash RUN.sh；服务器 Python 和所有路径由登记 authority 读取。正常情况下无需再次上传或手动启动，任务会完成验证后直接部署续跑。若使用 tee，必须紧接读取 PIPESTATUS[0]。观察窗沿用已有 FORMAL_MAX10_STAGE_STATUS.sh，Ctrl+C 仅关闭观察窗。

不改变晋升规则、样本选择、TRAIN_SELECT、最终 benchmark 隔离、Max-10 或停止规则。不重发 ambiguous/partial 请求，不重置预算。VERIFY 无模型发送、无 Slurm 提交、无 Git mutation；RUN 经原 resident 接续原 attempt。

这不是十轮完成证明。真实进展、job、有效轮次、训练和论文数据状态以当前 runtime receipt 为准。未来 local 资源预算 producer 的已知审计缺口继续保留，未在本修复中虚称解决。
