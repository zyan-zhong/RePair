# Generic SELECT Policy-Artifact Binding Implementation Plan

Goal: make P4 Harness-OFF SELECT accept generic frozen LoRA policy artifacts without changing evaluator semantics.

1. Create a detached worktree at exact Human Reference HEAD.
2. Add RED tests first for parent+candidate same-seed registration, generic candidate runtime/identity, legacy pi1 compatibility and registry-capacity validation.
3. Run the new test and require a pi1-only failure.
4. Minimally generalize `select_policy_runtime.py`, `select_execution_identity.py`, `select_result_audit.py` and the two SELECT runtime JSON schemas.
5. Run the new test GREEN.
6. Run `test_p4_select_execution_compat_v1.py` and then `tests/evaluation`.
7. Verify the frozen task-access manifest SHA and count `DEV_VISIBLE`, `SELECT_SUMMARY_ONLY`, `CONFIRMATORY_SEALED`, and `HISTORICALLY_EXPOSED` without reclassification.
8. Build a fixed-head review bundle containing RED/GREEN logs, evaluation regression log, diff, task-access census, source HEAD and after-change hashes.
9. Do not commit, push, load a model, start vLLM, run ALFWorld, submit Slurm or execute evaluation.
