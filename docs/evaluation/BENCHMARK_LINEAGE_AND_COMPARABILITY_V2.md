# Benchmark Lineage and Comparability V2

## 核心修正

主比较不能要求不同模型具有相同权重、tokenizer 或 adapter。否则任何跨模型 benchmark 都不可能成立。

因此 benchmark identity 拆成：

```text
SharedEvaluationProtocolV1
ModelExecutionProfileV1
```

### SharedEvaluationProtocolV1：主比较必须一致

- task panel、任务顺序和统计单位；
- 公开目标、observation、最近 executed history；
- 完整 admissible menu 的原字符串、原顺序、原数量；
- strict parser、exact membership 与固定接口反馈；
- controller / Harness / Memory 条件；
- action budget 与 policy-call budget；
- environment/source revision 与 success definition；
- round/seed schedule；
- sequential interaction 和完整 denominator census。

### ModelExecutionProfileV1：必须记录，但允许不同

- provider、endpoint、requested/returned model identity；
- local weight/tokenizer/adapter hash（若可得）；
- generation/reasoning contract；
- tool policy、statefulness、retry policy；
- provider seed availability；
- max output、tokens、latency 与费用。

因此：

```text
同 shared protocol + 不同 model profile
→ PRIMARY_COMPARABLE

不同 prompt/menu/parser/budget/Harness/task panel
→ 不能 PRIMARY_COMPARABLE
```

历史 GPT/Claude/Gemini 数字继续为 `PENDING_PROTOCOL_AUDIT`。只有共享协议重跑后才进入主表。
