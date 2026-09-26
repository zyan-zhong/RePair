# Round-1 autonomy binding gap ledger V1

This ledger is intentionally a control-plane inventory. It does **not** replace any scientific module or authority contract.

## Already reusable / bound assets

- Frozen integration branch: `integration/strong-primary-takeover-prep-v1`.
- Frozen head: `61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a`.
- Analyzer tail closeout: `STRONG_PRIMARY_ROUND1_ANALYZER_TAIL_AUTORUN_V1_1`.
- Analyzer-tail terminal receipt: `/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/strong_primary_round1_analyzer_tail_autorun_v1/61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a/STRONG_PRIMARY_ROUND1_ANALYZER_TAIL_AUTORUN_RESULT_V1.json`.
- Existing unified cognitive runtime already registers `R-PRE-PRIMARY-V1` and `R-POST-PRIMARY-V1`; therefore no new Strong Planner actor/runtime should be invented.
- Existing `src/pchsi/cognitive_runtime/researcher_primary.py` enforces that Strong PRE cannot assign environment effects and that promotion authority stays deterministic/independent.
- Existing research-intelligence assets include evidence hydration and F0/F1 handoff/reference machinery. They are historical assets to reuse/adapt only after exact Round-1 authority/data-binding review.

## Remaining exact bindings before the *full* one-command Round-1 continuation can be certified

1. Materialize one exact `STRONG_RESEARCHER_BLIND_PRE_INPUT_V2` from the **new frozen Analyzer-tail closeout**, preserving current evidence/X/Memory authorities and without Human-PRE visibility.
2. Bind that projection to existing `R-PRE-PRIMARY-V1` through the existing cognitive runtime; do not create another Planner model caller.
3. Bind selected PRE states/candidates to the existing same-state F0/F1 environment executor and independent verifier under fixed budgets.
4. Bind verified environment-result package + exact PRE record into existing `R-POST-PRIMARY-V1`.
5. Bind POST disposition into existing Failure Memory round-maintenance contract; only verified evidence may become authoritative next-round memory.
6. Bind deterministic train/no-train gate to the already-built training entry point. A no-train branch must also produce a terminal receipt so the driver can advance automatically.
7. Bind candidate training output into existing TRAIN_SELECT / Memory-OFF + Harness-OFF acceptance path.
8. Bind deterministic promote/rollback receipt.
9. Bind the previously frozen Strong-primary outer-loop stop governance before any next-round launch. It must distinguish clean scientific STOP/CONTINUE from fail-closed protocol/infra invalidity, preserve the 10-attempt cap and 3-valid-no-promotion patience, and never use sealed paper benchmark feedback.
10. Bind a conditional next-round transition: launch only on CONTINUE; on scientific STOP emit a terminal no-launch receipt; on invalidity remain fail-closed.
11. Freeze bounded infrastructure retry policy separately after Round 1; never auto-retry ambiguous post-send calls.

Until these exact bindings are closed, `CANONICAL_PI_K_TO_NEXT_ROUND_STANDARD_V1.json` deliberately marks them `UNBOUND`, and the driver fails closed before side effects. This prevents a generic orchestrator from silently inventing scientific semantics.
