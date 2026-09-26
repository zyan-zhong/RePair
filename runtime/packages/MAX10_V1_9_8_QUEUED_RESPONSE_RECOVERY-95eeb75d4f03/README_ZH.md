# V1.9.8 已知排队响应自动恢复

修复登记 X 调用在后台持续 queued、600秒上限触发全局停止。沿用原输入、模型、证据、校验及全部已完成调用。每次读取/取消都指向已登记 response ID。

只有队列等待超时、仍queued且供应商确认cancelled、output为空且output_tokens为0或usage=null，才启用原campaign基础设施重试预算。取消请求响应丢失可以幂等重试取消；没有确认绝不重生成。取消与完成竞态优先接纳原始完成结果。有输出、未知发送、ID不符、校验失败不会触发额外生成。in_progress只继续读取，最多使用P2响应等待时间×(1+campaign基础设施重试次数)，不主动取消模型计算。

本次旧logical terminal保持不变，登记相同科学输入的恢复目录和映射；原已耗1次与恢复最多2次合计不超过既有3次基础设施尝试。本次恢复中的首个尝试只处理旧响应，不新增生成；随后若收到取消确认才可有一次新生成。新轮次同类故障直接由原orchestrator在原预算内自动恢复，无需人工裁决。

VERIFY.py --server: 单元测试、真实P2无联网边界校验、原请求和SHA核验。RUN.sh: 验证后启动唯一resident，已在运行时禁止重复点火。operator shell使用set +euo pipefail；若tee须紧接读取PIPESTATUS[0]。所有凭证append-only，Git staging only，无git add/commit/push。统一监视入口不变。

当前R3科学请求保持冻结；继承V1.9.7的下一轮Local提示/输出上限修复。外层进程崩溃形成partial logical call仍fail-closed，不宣称已实现通用崩溃恢复。
