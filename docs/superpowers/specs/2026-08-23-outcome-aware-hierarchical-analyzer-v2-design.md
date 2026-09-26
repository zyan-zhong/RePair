# Outcome-Aware Hierarchical Analyzer V2 Design — Scientific Hardening V3 Specification

## Goal

Upgrade the unmerged Hierarchical Analyzer V2 design into an outcome-aware,
failure-priority system that analyzes both failed and successful trajectories,
keeps A0–A3 scientifically clean, decomposes verified repair effects, preserves
external strong-model traces for local distillation, and preregisters a complete
claim-aligned metric system.

## Existing assets retained

- sealed `ANALYZER_EVIDENCE_PACK_V1` foundation;
- existing Runtime Core, ActionTrace, PublicTransition and bundle reader;
- P2 strong offline proposer transport/provenance patterns;
- hierarchical post-hoc decomposition;
- governed `ANALYZER_MEMORY_PACK_V1` and `RESEARCHER_MEMORY_PACK_V1`;
- exact-state/same-state F0/F1 Harness;
- existing task-access and historical-access manifests;
- first-round training and OFF/OFF evaluation assets.

No replacement collector, runtime, Memory system, verifier, trainer, or evaluator
is created.

## Required architecture

```text
mechanical outcome router
→ L local outcome lifecycle
→ G cross-trajectory grouping
→ C capability attribution
→ P behavior profile
→ X independent cross-check
→ deterministic projector
→ Human Training Researcher
```

Failure and success lanes have different outputs and effect labels. Failure
analysis remains the majority of every analysis-budget regime:

```text
FAILURE_CRITICAL        85/15
MIXED_PERFORMANCE       70/30
HIGH_SUCCESS_REFINEMENT 55/45
```

## Required experiments

1. failure-only A0–A3 main repair-discovery experiment;
2. separate 12-success-episode optimization pilot;
3. 8–12 Benefit repair-effect decomposition using D0–D4;
4. external strong-model trace and local supervision materialization;
5. no formal calls or environment execution in the design/plan package.

## Required metrics

Use `ANALYZER_METRIC_REGISTRY_V1` together with
`ANALYZER_METRIC_LITERATURE_AUDIT_V1`. Retain standard localization,
classification, agreement, grounding, repair, process-efficiency, and final-task
metrics for comparability.

The main C1 endpoint is the project-proposed `Eligible-State Verified Repair
Yield (EVRY)`. It reports the fraction of all eligible source states for which a
condition discovers at least one Environment-verified Benefit. ABSTAIN,
no-candidate, invalid, unsupported, non-executable, Harm, Neutral, Uncertain, and
registered infrastructure-unavailable cases remain in the frozen denominator
handling.

EVRY must be reported with failure-cohort Harm, protected-baseline-cohort
Harm, `ProposalCoverage`, candidate-level `Verified Benefit Precision (VBP)`,
formal verifier environment steps per repaired unique `U_reg` unit, and
`EVRY@B`. These quantities remain separate; no arbitrary weighted composite is
used as the headline score.

The D0–D4 cohort reports the secondary `specificity-confirmed repair yield`
(internal compatibility ID `CSVRY`). It requires full-repair Benefit retention,
a registered matched-control result, and a `shortest tested sufficient prefix`.
`Minimal sufficient` wording is permitted only after every shorter prefix is
definitively non-Benefit. Task/gamefile is the independent unit. Missing and
infrastructure outcomes remain visible.

## Authority constraints

- Analyzer and Researcher produce hypotheses/proposals only;
- Environment Verifier owns Benefit/Harm/Neutral/Uncertain;
- Training evidence builder owns training-label eligibility;
- independent gate owns promotion/rollback;
- strong model never chooses outcome lane or analysis regime;
- successful-step redundancy is never accepted without success-preserving test;
- no plan or design branch is merged into `main` by this package.

## Acceptance

The design revision is review-ready when all required documents pass static
scope/marker/placeholder audits, the repository regression suite passes, the
revision is one single-purpose commit on the design branch, and local/remote
branch heads match.


## Metric hardening after independent review

The formal A0–A3 comparison freezes one common exact-state universe (`U_reg`)
and K=1 candidate-or-ABSTAIN before outcomes. EVRY is the repair-discovery
primary endpoint, jointly reported with failure/protected-cohort Harm,
ProposalCoverage, VBP, verifier environment steps per repaired unit, and EVRY@B.
Operational and execution-complete EVRY are both reported with infrastructure
reason census. D0–D4 is a secondary specificity analysis; paper-facing language
is specificity-confirmed repair yield and it does not gate formal Benefit
training eligibility. Final paper authority remains π2 vs π1 with Memory OFF
and Harness OFF.


## Normative review disposition

The accepted/partial/rejected review items are frozen in
`docs/analyzer/ANALYZER_PLAN_REVIEW_DISPOSITION_HARDENING_V1.md`. Runtime model
activation is separately governed by
`docs/analyzer/ANALYZER_V2_STRONG_MODEL_RUNTIME_ACTIVATION_V1.md`. Tasks 1–16
close deterministic scientific infrastructure and do not authorize model calls.
