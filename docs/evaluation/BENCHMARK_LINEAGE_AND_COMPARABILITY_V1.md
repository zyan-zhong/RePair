# Benchmark Lineage and Comparability V1

## 1. 必须进入最终 benchmark 叙事的模型节点

| Stage ID | 论文显示名 | 当前意义 |
|---|---|---|
| `RAW_BASE_PI0` | Raw base policy | Qwen2.5-3B 原始科研基线 |
| `PILOT_DISTILLED_PI1` | Pilot-distilled policy | 第一轮局部修复蒸馏后的 NO-GO parent |
| `PI2_HUMAN_REFERENCE` | Human-reference-round policy | 当前完整人工参考轮的输出 |
| `PI_STAR_AUTONOMOUS_FINAL` | Final self-improvement-system policy | 完整系统在 fresh autonomous round 后的最终模型 |
| `RELATED_WORK_REPRODUCED` | Reproduced related baselines | 在本仓库/同协议下复现的相关工作 |
| `STRONG_MODEL_REFERENCE` | Strong-model reference | GPT/Claude/Gemini 等强模型上限/参考 |

## 2. 比较资格

### PRIMARY_COMPARABLE

所有 protocol fingerprint 字段完全一致：

- model/tokenizer/adapter identity；
- prompt/history；
- menu/action interface；
- parser/controllers/harness；
- task panel；
- action/model-call budget；
- decoding/seed；
- ALFWorld/source revision；
- success definition。

### SECONDARY_REPRODUCED

相关工作已在当前环境重新实现，但存在预先说明的非主接口差异；只能作为次级比较。

### CONTEXT_ONLY_INCOMPARABLE

来自论文或历史运行，协议不一致或字段不完整。不得放进主差值、显著性或“超过”结论。

### PENDING_PROTOCOL_AUDIT

已有数字但尚未完成 fingerprint 审计。历史 GPT 强模型结果默认处于此类，直到在共享协议下重跑或完成完整可比性核验。

## 3. 指标层级

### 最终 policy authority

- task success；
- task-family success；
- protected-success regression；
- task-level paired interval；
- Memory OFF + Harness OFF。

### Repair discovery / verification

- EVRY registered universe；
- proposal coverage；
- Benefit/Harm/Neutral/Uncertain；
- Benefit precision；
- environment calls/tokens/cost per Benefit；
- time-to-first-Benefit；
- task-family coverage。

### Analyzer validity

- failure-onset exact / ±1；
- critical-window IoU；
- evidence citation precision；
- unsupported-fact rate；
- counterevidence coverage；
- abstention calibration。

### Research Planner quality

- Benefits per verification budget；
- task-family coverage；
- duplicate mechanism rate；
- repeated-NO-GO rate；
- single-change compliance；
- Human field-edit rate。

### Behavior / efficiency explanation

- invalid action；
- no-effect；
- loops/revisits；
- steps；
- tokens；
- latency。

Final policy success 不能被上述机制指标替代。
