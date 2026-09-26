# Stage 1 Framework Closeout V1

## Status

`CLOSED_FRAMEWORK_READY_FOR_CLEAN_HUMAN_ROUND`

Stage 1 is closed as a framework/integration milestone. It does not authorize a
scientific ALFWorld round by itself.

## What Stage 1 now contains

The system has one lifecycle, one clean-data gate, one authority switch, one
retention/promotion layer, and one concrete binding registry.

Existing scientific components remain authoritative:

- Evidence Package
- Hierarchical Analyzer
- Persistent Failure Experience / Memory
- Research Planner PRE / POST
- same-state F0/F1 port
- deterministic training-data materialization
- schema-aware renderer
- Generic Training Stage V2.1
- SELECT evaluator and Generic SELECT binding
- promotion / rollback
- Strong/Local structured trace storage

No second Analyzer, Memory, Trainer, evaluator, or meta-orchestrator is added.

## Final runner-port adjudication

### Generic Training

Use the existing `run_training_stage` from the frozen Generic Training Stage
V2.1 snapshot.

### SELECT evaluation

Use the existing repository-native `run_single_episode` evaluator together with
the Generic SELECT policy binding.

### Same-state F0/F1

Keep `SAME_STATE_F0F1` as the already-defined port contract over the evaluation
stack. Do not select a historical server-package candidate merely because a
heuristic census score is high.

The thin exact-state adapter is bound only when the next clean train-only Human
round supplies the frozen source-state authority.

### Human / Strong / Local invocation

Keep the existing role-neutral, reference-trace, role-authority and trace
handoff contracts. Do not promote a one-off Human adjudication runner into a
generic actor runtime.

Thin actor adapters are supplied by the clean-round execution gate:

- Human primary / Strong shadow
- Strong primary / Local shadow
- Local primary / Strong audit

## Clean-data boundary

All adaptive work remains ALFWorld train-only.

`TRAIN_UPDATE` feeds evidence, Analyzer, Memory, Research Planner, F0/F1 and
training. `TRAIN_SELECT` is only for internal promotion/rollback. `TRAIN_AUDIT`
is only for role-takeover audit.

`valid_seen` and `valid_unseen` are benchmark-only and cannot feed the adaptive
loop.

## Next gate

`CLEAN_TRAIN_ONLY_HUMAN_REFERENCE_ROUND_BOOTSTRAP`

The next round should provide only the execution-specific inputs that Stage 1
intentionally does not hard-code:

- fresh train-only manifests;
- parent policy artifact;
- round ID;
- authority phase;
- registered budgets;
- exact-state F0/F1 source-state adapter;
- Human / Strong actor adapters.

No new lifecycle or orchestration layer is needed.
