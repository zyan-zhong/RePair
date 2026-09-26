# P1 Interface Isolation I2 V1 Implementation Plan

> **For agentic workers:** execute this plan task-by-task with TDD. No GPU, vLLM server, ALFWorld rollout, external strong-model call, or sbatch is permitted during implementation/materialization.

**Goal:** Implement `ADMISSIBLE_ACTION_CONSTRAINT_V1`, freeze an execution-ready 12-cell I2 package, and verify that the already-collected R0 DEV evidence preserves complete raw policy text for later DEV-only strong-model diagnosis.

**Architecture:** I2 is a narrow extension of the approved I1 path. The only scientific change is generation-time JSON-schema constrained decoding whose `action.enum` is the exact current admissible-command sequence. Runtime Core, strict parser, prompt/history, ALFWorld adapter, budget, artifact publication, task set, seed, model, tokenizer, chat template, and server structured-output backend remain unchanged.

**Tech Stack:** Python 3.12, pytest, vLLM 0.11.0, xgrammar, ALFWorld evaluator contracts, Slurm (execution package only; no submission in this batch).

## Global Constraints

- Base code head: `1c9993796b52159202a2aae1c17a407e978a230f`.
- New branch: `implementation/p1-interface-isolation-i2-v1`.
- R0 and I1 wire behavior must remain byte-identical.
- I1 schema SHA-256 remains `ddca85be85528f1720614e9bfad1fd599f975737a43c51da130a402b312cce6a`.
- I2 uses the same frozen 12 DEV tasks and seed 17 as I1.
- I2 menu enum must preserve original command strings, order, and count.
- I2 must reject an empty menu or duplicate menu values rather than deduplicate or repair.
- Do not sort, deduplicate, lowercase, casefold, fuzzily match, or substitute menu actions when constructing the enum.
- Runtime Core exact membership and strict parser remain active as defense in depth.
- Structured-output server configuration remains `backend=xgrammar`, `disable_fallback=true`.
- `runtime_core.py`, `raw_policy_parser.py`, `raw_policy_prompt.py`, `budget.py`, `alfworld_adapter.py`, and `artifact_publisher.py` must have zero diff from the I1 base.
- Raw R0 policy response text is preserved as diagnostic evidence for later teacher analysis; it is not ground-truth chain-of-thought and is not directly accepted as an SFT target.
- This batch may build/freeze packages and evidence only. It may not run I2 or contact closed models.

## Task 1 — Freeze plan
Write this plan to `docs/superpowers/plans/2026-08-09-p1-interface-isolation-i2-v1.md`, check it, and commit it alone.

## Task 2 — RED tests
Create `tests/evaluation/test_i2_interface_isolation.py` and extend `tests/evaluation/test_interface_isolation_evaluator.py`. Confirm RED before any production modification.

Required coverage:
- exact menu sequence becomes `action.enum`;
- empty/duplicate/non-string menus fail closed;
- R0 and I1 exact wire hashes remain frozen;
- I1 schema remains enum-free;
- I2 profile requires the current menu;
- evaluator injects the *current* menu on each call;
- fake off-list output is still rejected by Runtime Core.

## Task 3 — GREEN implementation
Modify only:
- `src/pchsi/evaluation/interface_isolation_request.py`
- `src/pchsi/evaluation/policy_execution_profile.py`
- `src/pchsi/evaluation/episode_evaluator.py`

Produce:
- `i2_admissible_action_schema_dict`
- `i2_admissible_action_schema_sha256`
- `I2AdmissiblePolicyRequestV1`
- `I2_EXECUTION_PROFILE_V1`
- `requires_current_admissible_commands`

Run focused tests, I1 regression tests, full pytest, compileall, static scope audit, then commit and push.

## Task 4 — Freeze future teacher-input evidence readiness
Read only the frozen R0 DEV output. Require exactly 117 `policy_calls.jsonl` files and 351 valid `PolicyCallEvidenceV1` records. Freeze evidence that complete `raw_response_text`, raw HTTP response bytes, prompt, observation, full menu, executed history, feedback, and hashes are preserved. The future teacher sees these as `policy_generated_text` / `verbalized_rationale_evidence`, never as `ground_truth_reasoning`.

## Task 5 — Materialize I2 execution package
Freeze a package that binds the new code head, same 12-task manifest and seed 17, xgrammar/no-fallback, dynamic-enum preflight, complete policy-call evidence, per-call enum==menu sequence audit, I1↔I2 call-0 divergence, and a submit gate requiring `EXECUTION_APPROVED_P1_INTERFACE_ISOLATION_I2_V1`.

**Pre-collection completion:** code pushed/local==remote; full suite passes; forbidden core files unchanged; R0/I1 compatibility passes; P2 readiness is 117 cells/351 calls; I2 package static verify passes; `GPU_EXECUTION=NOT_APPROVED`, `SBATCH_EXECUTED=False`, `I2_EXECUTION=NOT_APPROVED`.
