# Strong-Model Reference Shared Protocol V1

## 目的

重新采集 `STRONG_MODEL_REFERENCE`，使其与本地 π0、π1、π2 使用同一任务—接口—环境协议。历史 GPT、Claude、Gemini 数字继续作为 context-only。

## 注册模型 Arm

### 主强模型上限

```text
arm = STRONG_MODEL_REFERENCE_REASONING_HIGH_V1
provider = OpenAI
model = gpt-5.6-sol
endpoint = /v1/responses
reasoning.effort = high
reasoning.context = current_turn
max_output_tokens = 32768
store = false
tools = []
structured output = OFF
previous_response_id = absent
automatic retry = 0
```

### 可选效率参考

```text
arm = STRONG_MODEL_REFERENCE_DIRECT_V1
reasoning.effort = none
max_output_tokens = 128
```

两条 arm 的任务、接口、环境与统计协议相同；它们的模型执行配置作为 `ModelExecutionProfileV1` 分别记录。

## 共享协议

- 同一 task manifest、task order 和统计单位；
- 同一公开任务目标、完整 observation、最近 8 个 executed transitions；
- 同一完整 admissible menu，原字符串、原顺序、原数量；
- 同一 strict parser、exact membership、错误反馈和 60/30/3/256 Runtime Core；
- Harness OFF、Memory OFF；
- 同一 ALFWorld/source revision 和 success definition；
- 完整记录请求/响应、returned model identity、tokens、latency、费用与失败。

不使用 Structured Outputs，因为 constrained decoding 会改变 action 生成分布。Provider 返回的原始文本仍必须通过项目现有 strict parser 和 exact-menu membership。

## 不能伪装为相同的部分

OpenAI provider 与本地 vLLM 不具有完全相同的 tokenizer、采样内核或 seed 语义。这些差异属于 `ModelExecutionProfileV1`，必须记录，不能伪造。主比较的含义是共享任务、信息、接口、预算和环境协议，不是底层模型实现相同。

## 复用约束

本项目已经有经过审计的 P2 OpenAI transport primitive。强模型 benchmark 只允许通过窄 compatibility adapter 调用该 primitive；不得新写第二套 urllib/httpx/OpenAI client。

## 并行与盲化

强模型 reference 可以在 Human reference round 期间并行收集，以节约 wall-clock time。但：

- Human PRE、Analyzer 和 Research Planner 不得读取逐任务强模型结果；
- 运行期间只暴露 operational status、完成/失败计数和 aggregate API usage；
- 逐任务结果在本地方法与 π2 评测协议冻结后解封；
- 强模型结果不得用于选择 repair、训练配方、阈值或 benchmark task。

## Batch API 边界

完整 ALFWorld episode 是 observation-dependent sequential interaction。每一步 API action 会改变下一步 observation，因此不能用一次离线 Batch job 替代完整 episode loop。Batch 只适用于相互独立的离线请求，不适用于本 benchmark 的逐步环境交互。
