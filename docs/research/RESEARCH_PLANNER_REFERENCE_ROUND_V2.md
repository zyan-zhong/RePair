# Research Planner Reference Round V2

## 1. 定位

本设计不是重新实现 Analyzer、Memory、F0/F1、Trainer 或 evaluator，而是在现有资产上补齐第一条完整的人工参考科研轮，并为紧随其后的强模型接管和本地统一角色训练留下稳定接口。

当前 round：

```text
π1 真实失败
→ Formal Hierarchical Analyzer
→ Persistent Failure Experience
→ Human Training Researcher PRE
→ 高价值 repair portfolio / repair program
→ same-state F0/F1
→ verified training evidence
→ π2-human
→ Memory OFF + Harness OFF
→ Human Researcher POST
```

随后必须依次进入：

```text
Human reference
→ Strong API Researcher teacher/shadow
→ Local Research Planner shadow/primary
→ Policy / Analyzer / Research Planner
   由同一个 Qwen2.5-3B checkpoint 的不同 role mode 承担
→ fresh autonomous round
```

统一 checkpoint 是完整项目的强制终态，但不阻塞当前人工参考轮。

## 2. Research Planner 的完整职责

Research Planner 不只是给已有实验排序。它负责：

1. 读取 round-level policy profile、Analyzer findings、Failure Experience、历史 GO/NO-GO、验证成本与 protected-success evidence；
2. 找出当前最关键、最可能产生高价值改善的 bottleneck；
3. 构造候选研究方向 portfolio，并记录 selected / rejected / deferred；
4. 从 Analyzer 和历史经验中发现 source-bound repair；
5. 在保持全部 lineage 的前提下，抽象或组合成可证伪的 repair program；
6. 证据不足时请求补充分析或 ABSTAIN；
7. 选择一个 principal scientific change；
8. 冻结验证预算、训练计划、stop rule 和 protected-cohort 约束；
9. round 结束后解释真实结果，记录未来不应重复的 NO-GO。

Research Planner 不能：

- 伪造机械事实；
- 偷改 Analyzer candidate 而不保留 lineage；
- 直接执行 ALFWorld action；
- 自行签发 Benefit / Harm / Neutral / Uncertain；
- 读取 sealed evaluation 的逐任务信息；
- 自己决定 promotion。

## 3. Repair portfolio 与 Repair program

`RESEARCH_REPAIR_PORTFOLIO_V1` 是 Human/API/Local Research Planner 的共同受控输出。

每条候选必须绑定：

- source state；
- source Analyzer candidate / group；
- current evidence SHA；
- 可选 historical Failure Experience；
- mechanism target；
- task-family scope；
- estimated value、harm risk、verification cost；
- selected / rejected / deferred 原因。

Research Planner 可以输出：

- `DIRECT_SOURCE_REPAIR`；
- `ABSTRACTED_REPAIR_TEMPLATE`；
- `COMPOSED_REPAIR_PROGRAM`；
- `REQUEST_FOR_ADDITIONAL_ANALYSIS`；
- `ABSTAIN`。

任何真正进入 F0/F1 的 repair 仍必须经过现有 deterministic candidate projector / source-state binding。Research Planner 的组合或抽象不能绕过执行合同。

## 4. 人工参考轮、强模型接管与本地化

### Stage R2 — Human reference

Human Researcher PRE 在所选实验 outcome 可见前冻结。Human 负责建立专业示范，包括证据引用、反证、单一主要改变、预算、stop rule 和 rejected/deferred 解释。

### Stage R3 — Strong API shadow / takeover

只有 Human PRE 冻结后，Strong API Researcher 才能在同一 evidence boundary 下输出 shadow PRE。POST 同理。强模型原始输出、人工逐字段修改、环境 outcome 和最终 round disposition 全部保留为 supervision。

强模型接管需通过：

- schema/evidence grounding；
- 单一主要改变；
- repair lineage；
- Benefits-per-budget；
- Harm；
- repeated-NO-GO；
- human field-edit rate；
- 不读取 sealed evidence。

### Stage L — Local Research Planner

本地 Qwen 先 shadow，再 primary。其质量由下游 verified-repair yield 和 round outcome 衡量，而不是文本相似度。

### Final U — Unified local checkpoint

最终同一个 Qwen2.5-3B checkpoint 通过不同 role contract 承担：

```text
<ROLE_POLICY>
<ROLE_ANALYZER>
<ROLE_RESEARCH_PLANNER>
```

统一的是模型权重，不是权限。Environment Verifier、Memory governance、data access、promotion gate 保持独立。

## 5. 本轮最小改动与资产复用

复用：

- 当前 `cognitive_runtime/researcher.py` 和 Human/API PRE/POST schemas；
- 旧 `research_intelligence` reference-round、distillation、takeover、demonstration 资产；
- Formal Analyzer canonical archive 和 result manifest；
- Failure Memory 的 Analyzer/Researcher views；
- 已有 F0/F1 source-state replay / verifier；
- 第一轮训练器和 OFF/OFF evaluator；
- generic self-improvement loop 的 rollout/identity/role-neutral/next-round-only hardening。

本轮只新增或加固：

- Research Planner 高价值 repair discovery / composition 合同；
- role-neutral PRE/POST 与 unified-Qwen final target；
- benchmark lineage/comparability registry；
- outcome-blind reference-round readiness pack。

## 6. 当前包不执行的内容

- 不调用强模型；
- 不执行 ALFWorld；
- 不执行 F0/F1；
- 不训练 π2；
- 不运行 benchmark；
- 不签发 Human PRE；
- 不改变 Formal Analyzer、Memory、Verifier、Trainer 或 evaluator 的科学语义。
