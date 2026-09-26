# Stage 1 Concrete Component Binding Implementation Plan V1

**Goal:** Connect the already-built Stage 1 control plane to existing concrete
component implementations and runtime source families without duplicating
scientific logic.

## Task 1 — TDD concrete binding registry

- Add tests first and require RED because `concrete_bindings` does not exist.
- Bind all Stage 1 component IDs.
- Reuse repo-native components directly.
- Bind renderer/trainer/model-init/receipt source families by frozen snapshots.
- Keep same-state F0/F1 as an adapter port over the existing evaluator stack.
- Never authorize execution from the registry.

## Task 2 — Immutable stage-attempt receipts

- Add `StageAttemptReceiptV1`.
- Enforce ordinal and previous-receipt linkage.
- Publish with exclusive create.
- Never overwrite failed or completed artifacts.

## Task 3 — Clean round manifest

- Bind parent policy artifact identity.
- Bind authority phase.
- Bind three distinct train-side data-plane manifest SHAs.
- Keep benchmark feedback and scientific execution false.

## Task 4 — Lifecycle-to-runtime execution plans

- Reuse the existing `next_action_for()` orchestrator.
- Project component IDs to concrete bindings.
- Enforce TRAIN_UPDATE for adaptive work.
- Enforce TRAIN_SELECT for internal evaluation/promotion.
- Do not execute components.

## Task 5 — Automatic next-round creation

- Reuse the existing promotion decision.
- PROMOTE selects the candidate as next parent.
- ROLLBACK keeps the current parent.
- HOLD blocks automatic next-round creation.

## Task 6 — Synthetic role and lifecycle dry run

Exercise:

- Human primary / Strong shadow;
- Strong primary / Local shadow using synthetic takeover approval;
- Local primary / Strong audit;
- lifecycle from ROUND_CREATED to ROUND_CLOSED;
- strong/local trace retention;
- benchmark feedback denial;
- PROMOTE and ROLLBACK next-parent derivation.

No provider, model, environment, trainer, evaluator or benchmark execution is
allowed.

## Task 7 — Verification and publication

- focused round-control tests;
- research-intelligence tests;
- evaluation tests;
- native security build prerequisite;
- full repository tests;
- compile/static source-language audit;
- commit to feature branch;
- push feature branch only;
- no main update;
- export fixed-head review bundle.
