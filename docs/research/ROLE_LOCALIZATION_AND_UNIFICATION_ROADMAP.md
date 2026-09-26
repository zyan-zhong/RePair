# Role Localization and Unification Roadmap — Corrected V2

## Canonical requirement

完整项目的最终认知系统必须由**同一个本地 Qwen2.5-3B checkpoint**通过不同 role mode 承担 Task Policy、Hierarchical Analyzer 和 Research Planner。该要求是最终系统强制目标，不是可选附件；但它不阻塞当前 π1→π2 Human Reference Round。

## Stage 0 — Current human reference round

```text
Task Policy             = local π1
Hierarchical Analyzer   = strong-model primary / audited runtime
Research Planner        = Human primary
Strong Research Planner = shadow after Human PRE freeze
Memory                  = frozen governed Failure Experience
Verifier                = independent environment authority
Promotion               = deterministic independent gate
```

目标：完成一条完整、可审计的 `evidence → research decision → repair program → experiment → training → OFF/OFF outcome` 示范轨迹。

## Stage 1 — Strong-model teacher/reference takeover

Strong Analyzer 和 Strong Research Planner 在 fresh train-side evidence 上按 Human 模板独立运行。Human 只做字段级 accept/revise/reject、安全审核和异常处理。

必须保存：

- teacher 原始输出；
- Human 修改前输出；
- 每个字段的修改；
- selected / rejected / deferred 理由；
- F0/F1 outcome；
- training outcome；
- round GO/NO-GO。

## Stage 2 — Local Analyzer and Research Planner shadow

以 Qwen2.5-3B lineage 训练：

```text
trajectory evidence → Analyzer artifacts
round evidence       → Research Planner PRE/POST
```

评价依赖下游：evidence grounding、unsupported-fact、verified-repair yield、Benefits-per-budget、Harm、single-change compliance、human field-edit rate。

## Stage 3 — Local primary roles

Local Analyzer primary；Local Research Planner primary。Strong model 降为 disagreement audit / high-risk challenge。Human 不再选择每轮 bottleneck 或 repair program。

## Stage 4 — Unified checkpoint

同一个 checkpoint identity：

```text
θk + <ROLE_POLICY>
θk + <ROLE_ANALYZER>
θk + <ROLE_RESEARCH_PLANNER>
```

三角色必须共享 architecture、tokenizer 和 checkpoint artifact identity，但使用独立：

- visibility contract；
- prompt contract；
- output schema；
- stage budget；
- Memory/Evidence view。

不能并入同一模型权限的组件：

- raw evidence store；
- task/data access control；
- environment verifier；
- F0/F1 execution harness；
- Memory governance；
- deterministic promotion/rollback gate；
- sealed evaluation release control。

## Stage 5 — Fresh autonomous round

只有同时满足以下条件，才能声称 autonomous iterative self-improvement：

- fresh `πk→πk+1` round；
- Policy/Analyzer/Planner 同 checkpoint；
- per-round human scientific decisions = 0；
- routine external-model calls = 0；
- verifier independent；
- promotion deterministic；
- sealed evaluation details 对 Planner 不可见；
- `πk+1 OFF/OFF > πk OFF/OFF`。
