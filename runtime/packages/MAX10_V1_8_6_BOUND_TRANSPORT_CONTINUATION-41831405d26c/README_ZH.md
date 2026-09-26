# G-A2 连接故障与下游预算接线修复

复用当前 resident、rollout、本地分析登记及已有 G 结果。沿 campaign authority 读取 transport 重试预算；G/C/X/PRE 与独立 POST 使用同一预算。显式更小限制保留。当前 G-A2 原始 NOT_SENT 收据不修改；只登记一个确定性的后继请求，扣除已消耗尝试。模糊发送、部分请求绝不重发。

在登记的 resident host 上，`bash RUN.sh` 完成校验并后台续行；`bash STATUS.sh --watch` 查看状态。入口只读取 AUTHORITY.json 指定的注册资产。不要在已运行时重复启动。

如需保存操作输出：`bash RUN.sh 2>&1 | tee run.log`，下一行立即 `rc=${PIPESTATUS[0]}`，然后 `printf 'RUN_RC=%s\n' "$rc"`。operator shell 不开启 errexit/nounset/pipefail。

VERIFY 的 server 模式不发送 provider 请求，不提交 Slurm。保留 Max-10、既有停止规则、TRAIN_SELECT 晋升准则、Memory 与最终 benchmark 隔离。当前 local 60 项冻结不变。未来轮次的 local budget producer 尚有单独审计缺口，本补丁不新增科研决策算法。

Git 内容仅生成 staging cache/delta；不执行生产 Git 修改、commit 或 push。完整总账、append-only proof 与实际执行结果在同批交付记录中提供。
