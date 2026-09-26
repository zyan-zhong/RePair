# STAGE4C_EXISTING_SELECT_FREEZE_V1

Continue the successful Stage4B output; do not rerun scientific stages or apply another code patch.

## Inputs

`current_request.json` binds the exact uploaded preflight ZIP, original repository head/tree, existing preflight helper bytes, authority context, and existing isolated worktree. `decisions/current_protocol_decision.json` is a separate explicit approval target. It preserves the proposal's task order, seeds, conditions, and per-episode budget. It adds the measurement interpretation and missingness rule to be approved before evaluation.

## Entry

`python -B RUN_ALL.py --approve-decision <SHA256 of exact decision file bytes>`

Without approval, the entry returns 20 and does not commit or freeze a protocol. The supplied approval is for local code fixation and protocol recording only, not live execution. A successful authorized run returns 0. A failed identity, dependency, regression or publication check returns 21. No shell options are set by this package.

## Effects

1. Reuse original archive, training-contract, ledger, candidate-file, base-file, and pool checks.
2. Verify all source bytes, including the previously applied three-file I1 extension and its test.
3. Require existing B0/A9 dependency artifacts. Compile only the original native default target for full-test prerequisites. Do not recreate missing scientific dependencies.
4. Run unfiltered full repository pytest with no deselection or skips. Record exact inputs and reuse an exact successful regression receipt on re-entry, while revalidating the original B0 audit.
5. Commit the existing overlay in the existing detached code worktree. Create a local review ref and a verified Git bundle. The original worktree stays at its exact parent. Nothing is pushed.
6. Write an immutable protocol, decision approval receipt, original artifact index, and NEXT_STAGE_BINDING.
7. Capture the already-existing pilot live source for subsequent thin clean binding. Its historical task/model constants are not authorized.

The nested `grid` and `model_binding` objects in the frozen protocol are preserved copies of the source proposals. Their old `protocol_frozen=false` flags remain provenance, not current top-level authority. Only the outer protocol receipt and explicit downstream execution authorization determine readiness. Do not use the old proposal as a live override.

## Not implemented or authorized here

No model server, model inference, ALFWorld execution, training, scheduler submission, checkpoint promotion, or final round archival closure. No remote Git publication. Typed live server/policy/schedule/environment manifests and the live execution authorization remain a subsequent binding step. This is not a claim that the complete Strong-primary loop has been deployed.

## Outputs

- SELECT_EVALUATION_PROTOCOL_V1.json
- PRIMARY_DECISION_APPROVAL.json
- FIXED_CODE.json and FIXED_CODE.patch
- FULL_REGRESSION_PASS.json and its full logs
- INPUT_ARTIFACT_INDEX.json using the original round-training index builder
- NEXT_STAGE_BINDING.json
- SELECT_CODE_PROTOCOL_REVIEW.zip
- SELECT_CODE_HISTORY.bundle (local full code history; kept separate from the review ZIP)

A repeat run with identical inputs reuses exact bytes/ref/receipt. A mismatch is rejected; there is no reset, checkout rollback, force push, automatic retry or silent replacement.
