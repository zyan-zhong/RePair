# Formal Max-10 Planner 输入接线与 POST 续接

本包复用 V1.8.7 resident、原 Analyzer/PRE/POST、H4.4 compact environment、native verifier、训练与轮次治理。

当前首轮 PRE 保持原字节；新 PRE 视图只在 owner 的下一科学轮次绑定生效，基础设施重试不会被误认成新轮。组装既有 L/G/C/P/X 输出、公开任务上下文、失败分母和原 Researcher Memory，不重新执行 Analyzer，不调整候选或数量。

当前 POST 因 `400/string_above_max_length` 被明确拒绝。原请求/响应/逻辑调用与失败终结记录永久保留。只允许登记一个不同请求哈希的内容压缩调用；模糊或部分响应不能重发。发送前按原 H4.4 policy 检查实际请求字节数。未来 POST 在首次调用前使用同一压缩逻辑。

压缩只影响 model-facing request。canonical post/projection.json 仍是原完整 verifier，callback、recipe adoption 和 resident 的科学校验继续消费同一完整投影。所有状态/配对结果、分母、效果标签和分支证据 SHA 保留；不截断文字、不抽取科学样本。原始 policy/environment 逐步证据保持在原路径。

`VERIFY.py` 本地运行 7 个针对性回归；`VERIFY.py --server` 进一步通过真实 POST worker 和下一轮 PRE 渲染路径，全部禁止模型发送及 Slurm 提交。

服务器执行 `bash RUN.sh`：验证后由单次启动登记接续原 campaign。operator shell 不开启 set -e/-u/pipefail。若外部用 tee，必须立即保存 PIPESTATUS[0]。

环境、凭据、repo 和资产位置来自 AUTHORITY.json 及已登记 predecessor，不在实现中选择版本目录或扫描服务器。package source manifest、append-only ledger/proof、Git staging cache/delta 均记录本次变更；不执行 git add/commit/push。

本包不保证 Benefit、优化器运行或晋升。Max-10、无晋升停止规则、TRAIN_SELECT 上成功数严格增加的晋升条件与最终 benchmark 隔离保持原 authority。
