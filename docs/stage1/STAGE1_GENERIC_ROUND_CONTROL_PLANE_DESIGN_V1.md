# Stage 1 Generic Round Control Plane Design V1

## Scope

Stage 1 adds only a control plane around already-existing scientific components. It does not reimplement Evidence Package, Analyzer, Failure Memory, Research Planner, F0/F1, deterministic materialization, Trainer, evaluator, promotion rules, or Strong/Local role models.

The new control plane has eight responsibilities:

1. generic round lifecycle;
2. Human → Strong → Local role authority;
3. clean train-only data access;
4. structured Human/Strong/Local trace handoff;
5. benchmark result sealing;
6. cross-round retention policy;
7. promotion/rollback orchestration;
8. automatic next-round routing.

## Reuse First

Existing repository assets remain authoritative:

- `pchsi.reference_loop.analyzer_evidence_pack` for evidence packaging;
- `pchsi.analyzer` for Analyzer;
- `pchsi.memory` for persistent failure experience;
- `pchsi.research_intelligence.role_neutral` and planner trace modules for role-neutral Research Planner artifacts;
- `pchsi.research_intelligence.takeover` for Strong/Local takeover eligibility;
- `pchsi.research_intelligence.reference_round` for human reference-round manifests;
- `pchsi.research_intelligence.distillation` for local-role supervision dataset construction;
- `pchsi.reference_loop.approved_materialization` for deterministic approved materialization;
- `pchsi.evaluation` for SELECT evaluation;
- existing Generic SELECT runtime/artifact compatibility patches from Stage 0.

External runtime components such as the schema-aware renderer, Generic Training Stage V2.1, model-init smoke, and training receipts are not duplicated in Stage 1. Their concrete runner binding is the next gate.

## Lifecycle

The frozen lifecycle is:

`ROUND_CREATED`
→ `EVIDENCE_READY`
→ `ANALYSIS_READY`
→ `PRE_PLAN_FROZEN`
→ `EXPERIMENTS_COMPLETED`
→ `POST_PLAN_FROZEN`
→ `TRAINING_DATA_READY`
→ `TRAINING_COMPLETED`
→ `INTERNAL_EVALUATION_COMPLETED`
→ `PROMOTED | ROLLED_BACK`
→ `ROUND_CLOSED`.

Every transition carries a SHA-256 evidence identity. Skipping stages is fail-closed.

## Role Authority

Three authority phases are supported:

- `HUMAN_PRIMARY_STRONG_SHADOW`
- `STRONG_PRIMARY_LOCAL_SHADOW`
- `LOCAL_PRIMARY_STRONG_AUDIT`

Strong-primary and Local-primary are not self-authorized. They require the existing `RESEARCH_PLANNER_TAKEOVER_EVALUATION_V1` gate.

Strong Analyzer / Research Planner outputs are recorded every applicable clean train-side round for future localization distillation. Provider hidden reasoning is not required or stored; structured evidence and structured decisions are the supervision target.

## Clean Data Plane

All adaptive work is train-only.

ALFWorld `train` is internally divided before any clean scientific run into:

- `TRAIN_UPDATE`: rollout, badcase, Analyzer, Memory, Research Planner, F0/F1, policy training, localization supervision;
- `TRAIN_SELECT`: internal promote / rollback only; never policy training;
- `TRAIN_AUDIT`: Human→Strong→Local takeover audit only.

`valid_seen` and `valid_unseen` are final benchmark inputs only. They cannot feed Analyzer, Memory, Research Planner, F0/F1, policy training, localization supervision, or internal promotion.

This is consistent with ALFWorld's official layout, where training data is under `train` and the seen/unseen validation splits are evaluation paths.

## Retention

Stage 0 is a contaminated engineering pilot. From that pilot only generic code, schemas, contracts, tests, and infrastructure may cross into the clean experiment.

Clean train-side Strong structured traces may be retained for localization. Clean train-side procedural failure experience may persist across rounds under the Memory contract. Benchmark results remain sealed and cannot enter the adaptive loop.

## Benchmark Sealing

A benchmark result is stored under a seal containing checkpoint identity, benchmark split, shared protocol hash, and result artifact hash.

Benchmark feedback is never authorized for adaptive decisions. Results may be revealed only after all comparison checkpoints and the analysis protocol are frozen.

## Promotion / Rollback

Stage 1 does not invent a new numerical promotion threshold. It only enforces evidence provenance:

- promotion evidence must be `TRAIN_SELECT`;
- `valid_seen` / `valid_unseen` evidence is forbidden;
- decisions are `PROMOTE`, `ROLLBACK`, or `HOLD`;
- the next parent policy is derived mechanically from the frozen decision.

## Failure Semantics

Control-plane failures fail closed and do not execute model, environment, training, or benchmark work. Artifact identity is SHA-bound. Existing scientific component semantics are not silently changed by the control plane.

## Stage 1 Control-Plane Exit

This package completes the Stage 1 control-plane foundation when:

- new control-plane tests pass;
- research-intelligence and evaluation regressions pass;
- Stage 0 closeout and Generic SELECT patch identities are revalidated;
- the control-plane dry run passes;
- existing reference-round, takeover, distillation, and benchmark registry APIs interoperate with the new control plane;
- no model, environment, training, benchmark, commit, or push occurs.

The next gate is concrete component-runner binding plus a non-scientific Human→Strong→Local orchestration dry run.
