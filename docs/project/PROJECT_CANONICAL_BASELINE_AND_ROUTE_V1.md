# Project Canonical Baseline and Route V1

生效日期：2026-08-28

除非项目负责人明确修改，本文件是后续设计、代码、实验、论文和项目对话的基础背景。

## 主研究问题

一个 research-guided self-improvement system 能否从本地长程策略的真实失败中，通过层次化分析、历史 Failure Experience 和 Research Planner 的高价值修复发现，更高效地找到值得验证的修复；再由同状态环境实验筛掉无效或有害修复，只训练 verified evidence，使下一版策略在 Memory OFF、Harness OFF 时仍然真正变强？

## 角色边界

- Policy：执行任务动作。
- Hierarchical Analyzer：轨迹诊断、跨轨迹机制、候选 repair；没有效果签发权。
- Persistent Failure Experience Library：受治理的历史经验 substrate；不是 reasoning agent。
- Training Researcher / Research Planner：识别整轮 bottleneck，发现或组合关键 repair，选择一个 principal change，冻结预算和实验；没有 Benefit/Harm 或 promotion 权。
- Training Harness：Researcher 的实验执行臂。
- Environment Verifier：Benefit/Harm/Neutral/Uncertain 的唯一因果 authority。
- Promotion/Rollback Gate：独立、程序化，不得由 Planner 自我批准。

## 固定迁移路线

```text
Human reference
→ Strong API Analyzer / Research Planner teacher/reference
→ Local Qwen Analyzer / Planner shadow
→ Local primary
→ one Qwen2.5-3B checkpoint with three role-conditioned modes
→ fresh autonomous round
```

最终 routine：每轮人工科研决定数为 0，强模型例行调用数为 0。

## Benchmark

正式谱系：

```text
RAW_BASE_PI0
PILOT_DISTILLED_PI1
PI2_HUMAN_REFERENCE
PI_STAR_AUTONOMOUS_FINAL
RELATED_WORK_REPRODUCED
STRONG_MODEL_REFERENCE
```

强模型历史数字只作 context；必须按共享任务、接口、预算、环境协议重跑后才能进入主比较。

## 工程规则

先查历史资产；不重做 Analyzer、Memory、F0/F1、Trainer、Evaluator；优先适配与复用；默认 focused tests；全量回归只在 integration/merge gate 运行。
