# 当前已训练候选到 TRAIN_SELECT 的服务标识修复

V1.9.1已解决POST契约并完成原生Dual-View训练3步；本包修复随后评估入口的服务标签长度不兼容。原科学policy_id为80字符，而既有原生Select schema仅允许64字符。新logical_condition_id/checkpoint_instance_id是完整policy_id+adapter SHA规范JSON的完整SHA256，不截断身份，不改权重、训练产物或科学policy_id。

通过REGISTERED_OFFOFF_EXECUTION_INDEX.json登记新的候选/评估绑定位置，保留原发布资料和失败证据。当前仅使用已成功训练产物，训练job原回执直接接纳，POST不重发、F0/F1不重跑。后续候选发布也应用同一确定性服务标签。VERIFY验证真实原生candidate -> protocol -> server manifest ->3550 cells/4 shards材料化，在Slurm提交前拦截；RUN验证后续接原resident自动评估和晋升。全部科研决策、Max10治理、TRAIN_SELECT与最终benchmark隔离保持不变。

未来父模型与候选同为LoRA时，保留原生冻结的max_loras=1（单批活动适配器数），仅根据注册适配器数量扩展max_cpu_loras缓存。原生Select schema对两适配器前瞻用例验证，不修改任何科研阈值。

本包不启用set -e/-u/pipefail；外接tee后显式读取PIPESTATUS[0]。所有路径来自本包authority和前驱registered index。Git staging only；无add/commit/push。
