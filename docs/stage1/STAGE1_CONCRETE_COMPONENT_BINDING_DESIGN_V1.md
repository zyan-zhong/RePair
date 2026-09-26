# Stage 1 Concrete Component Binding Design V1

## Scope

This change completes the control-plane-to-runtime wiring boundary without
reimplementing scientific components or authorizing scientific execution.

The existing Stage 1 control plane remains authoritative for lifecycle, role
authority, clean data access, trace handoff, benchmark sealing, retention, and
promotion/rollback.

This change adds only:

1. a hash-bound concrete component binding registry;
2. immutable stage-attempt receipts with no-clobber publication;
3. a clean-round manifest that binds train-update/select/audit authorities;
4. an execution-plan projection from lifecycle actions to concrete bindings;
5. deterministic next-round creation from an already-frozen promotion decision.

## Reuse Boundary

Repository-native bindings are used for Evidence Package, Analyzer, Memory,
Research Planner, deterministic materialization, SELECT evaluation, promotion,
retention, and trace storage.

Historical engineering snapshots are references for the schema-aware renderer,
Generic Training Stage V2.1, model-init smoke, and training receipts.

Same-state F0/F1 remains a port contract over the existing evaluator/runtime
stack. Stage 1 does not create a second causal-verification implementation.

## Execution Boundary

All bindings are created with:

`scientific_execution_authorized = false`

The build and dry-run package performs no model call, environment execution,
training, benchmark, Slurm submission, or policy promotion.

Live execution remains a separate authority gate.

## Clean Data Boundary

Adaptive components consume only ALFWorld train-side authorities.

- analysis, memory, F0/F1, data building, rendering and training: TRAIN_UPDATE;
- internal candidate selection and promotion: TRAIN_SELECT;
- role takeover audit: TRAIN_AUDIT;
- valid_seen / valid_unseen: final benchmark only, never adaptive feedback.

## Attempt Semantics

A failed or censored stage never overwrites an earlier attempt.

Attempt 0 has no previous receipt. Attempt N>0 must bind the previous receipt
SHA. Receipt publication uses exclusive creation and therefore cannot clobber
an existing artifact.

## Role Migration

The existing role authority switch remains unchanged:

Human primary / Strong shadow
→ Strong primary / Local shadow
→ Local primary / Strong audit.

Strong and Local structured traces remain train-side supervision/audit assets.
Provider-private chain-of-thought is neither required nor stored.

## Exit Condition

Stage 1 concrete binding is complete when the feature branch passes focused and
full regressions, a synthetic Human→Strong→Local dry run closes without any
scientific execution, and the review bundle is ready for fixed-head code review.
