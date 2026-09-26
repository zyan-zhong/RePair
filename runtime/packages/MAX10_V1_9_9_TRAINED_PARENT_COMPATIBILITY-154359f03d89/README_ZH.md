# V1.9.9 晋升父模型跨轮接线修复

补齐原 source-condition 与 H44 runtime reader 对既有 CURRENT_TRAINED_POLICY_RUNTIME_BINDING_V1 的支持。保持严格字段、文件SHA、当前parent/model、continuation contract与真实LoRA权重校验；返回原完整runtime，不改写schema或原文件。复用原LoRA服务启动器。worker_startup继承到控制进程、GPU分支及其子进程。

每轮开始Analyzer前精确预检本轮request/profile/runtime，提前发现不兼容。父模型、轮次、模型别名、权重均从本轮authority取得。复用V1.9.8运行入口和cache身份，当前R3全部已接受结果不重新生成。

PRE策略receipt中的sha256引用沿用原training_binding.materializer._read_ref读取，修正动态option注册误用file_sha256读取器的接线；不修改receipt或降低SHA检查。FULL_PREPARATION_CHECK使用真实accepted PRE及capture，在本轮authority输出范围内的独立registered_verification目录完整走H44准备至执行计划，execute=False，不提交作业。

VERIFY.py --server进行本地回归、真实权重/当前接线、旧clean reader、新解释器继承和完整H44准备验证；无API、Slurm或训练调用。完整准备包含原历史资产核验，可能耗时数分钟。RUN.sh验证后启动唯一resident；先激活登记环境。operator shell不用set -e/-u/pipefail；如果tee日志，紧接读取PIPESTATUS[0]。Git仅staging，不add/commit/push。

仅两种已登记schema合法；未知类型/权重或身份冲突仍停止，不能把失败伪装为科学结果。所有科研分割、晋升、BENEFIT-only训练和Memory/证据链保持原协议。当前部署完成后无需再次运行RUN。观察入口沿用FORMAL_MAX10_STAGE_STATUS.sh --watch。
