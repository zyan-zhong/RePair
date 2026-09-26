# Stage 1 Generic Round Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task. This package performs the same sequence mechanically without committing.

**Goal:** Add a generic, train-only round control plane that coordinates existing project components and role authority without duplicating scientific logic.

**Architecture:** Add a new `pchsi.round_control` package only. Existing Analyzer, Memory, Research Planner, takeover, distillation, evaluator, and deterministic materialization remain authoritative. The package first adds tests and confirms RED, then adds the implementation, runs targeted regressions, and produces a review bundle.

**Tech Stack:** Python 3.12, dataclasses, existing `pchsi.reference_loop`, `pchsi.research_intelligence`, `pchsi.evaluation`, pytest.

**Spec:** `docs/stage1/STAGE1_GENERIC_ROUND_CONTROL_PLANE_DESIGN_V1.md`

## Global Constraints

- Exact repository HEAD: `daef26b9cde45182ada534d96335da3ea451f12f`.
- Stage 0 closeout ZIP SHA-256: `7d29e40bf7c5f7df8869382071529a90fc2a44c1f3acc29d0e0b367d941bdba3`.
- Stage 0 remains `PILOT_ENGINEERING_ROUND_V1`; no paper efficacy evidence and no promotion eligibility.
- Adaptive clean work must be ALFWorld train-only.
- No model execution, environment execution, training execution, benchmark execution, commit, or push.
- Existing Generic SELECT Stage 0 worktree changes are preserved.
- Production source remains English-only.

---

### Task 1: Verify Stage 0 and worktree authority

**Files:**
- Execute: `10_VERIFY_STAGE0_AND_WORKTREE.py`
- Produce: `stage1_generic_round_automation_control_plane_v1_output/STAGE1_PRECONDITION_RECEIPT_V1.json`

**Interfaces:**
- Consumes: Stage 0 closeout ZIP, Stage 0 Generic SELECT patch receipt, detached worktree.
- Produces: exact precondition receipt.

- [ ] Verify closeout ZIP file SHA and CRC.
- [ ] Verify `round_status=CLOSED`, `paper_efficacy_evidence=false`, `promotion_eligible=false`.
- [ ] Verify 85 paired / 170 total Stage 0 cells.
- [ ] Verify Stage 1 handoff SHA.
- [ ] Verify Stage 0 Generic SELECT patch freeze root.
- [ ] Verify detached worktree HEAD and exact pre-existing changed path set.

### Task 2: Add lifecycle and orchestrator with TDD

**Files:**
- Create: `src/pchsi/round_control/lifecycle.py`
- Create: `src/pchsi/round_control/orchestrator.py`
- Test: `tests/round_control/test_lifecycle.py`
- Test: `tests/round_control/test_promotion_orchestrator.py`

**Interfaces:**
- Consumes: lifecycle stage plus evidence SHA.
- Produces: immutable next lifecycle state and next existing component IDs.

- [ ] Copy tests only.
- [ ] Run `pytest -q tests/round_control` and require RED because `pchsi.round_control` is absent.
- [ ] Add lifecycle implementation with exact transition graph.
- [ ] Add deterministic component routing.
- [ ] Require no execution authorization in orchestration planning objects.

### Task 3: Add clean data access gate

**Files:**
- Create: `src/pchsi/round_control/clean_data_gate.py`
- Test: `tests/round_control/test_clean_data_gate.py`

**Interfaces:**
- Consumes: official split, internal train pool, intended consumer.
- Produces: SHA-bound access grant or fail-closed error.

- [ ] Allow adaptive consumers only from `ALFWORLD_TRAIN/TRAIN_UPDATE`.
- [ ] Allow promotion only from `ALFWORLD_TRAIN/TRAIN_SELECT`.
- [ ] Allow role takeover audit only from `ALFWORLD_TRAIN/TRAIN_AUDIT`.
- [ ] Allow `valid_seen` / `valid_unseen` only for final benchmark.
- [ ] Reject benchmark-to-Analyzer / training / Research Planner leakage.

### Task 4: Add Human→Strong→Local authority switch

**Files:**
- Create: `src/pchsi/round_control/role_authority.py`
- Test: `tests/round_control/test_role_authority.py`

**Interfaces:**
- Consumes: authority phase plus existing takeover evaluation artifact.
- Produces: primary/shadow/auditor mapping.

- [ ] Human-primary requires Strong shadow capture.
- [ ] Strong-primary requires `strong_research_planner_primary_eligible=true`.
- [ ] Strong-primary local shadow requires `local_training_and_shadow_eligible=true`.
- [ ] Local-primary requires `local_research_planner_primary_eligible=true`.
- [ ] Reuse `ResearcherRoleModeV1` rather than redefining role-mode semantics.

### Task 5: Add structured trace handoff and retention

**Files:**
- Create: `src/pchsi/round_control/trace_handoff.py`
- Create: `src/pchsi/round_control/retention.py`
- Test: `tests/round_control/test_trace_handoff.py`
- Test: `tests/round_control/test_retention_and_benchmark.py`

**Interfaces:**
- Consumes: structured role output artifact hashes.
- Produces: round trace ledger plus cross-round retention decision.

- [ ] Require train-side role traces.
- [ ] Require structured output and forbid dependency on provider hidden reasoning.
- [ ] Require Strong PRE and POST traces when applicable.
- [ ] Retain Strong structured traces for localization.
- [ ] Block Stage 0 task-specific semantic artifacts from clean experiments.

### Task 6: Add benchmark sealing and promotion provenance

**Files:**
- Create: `src/pchsi/round_control/benchmark_sealing.py`
- Create: `src/pchsi/round_control/promotion.py`
- Test: `tests/round_control/test_retention_and_benchmark.py`
- Test: `tests/round_control/test_promotion_orchestrator.py`

**Interfaces:**
- Consumes: shared evaluation protocol hash, result hash, internal selection evidence.
- Produces: sealed benchmark record and promotion decision.

- [ ] Seal benchmark output by checkpoint and shared protocol.
- [ ] Forbid reveal before all comparison models are frozen.
- [ ] Keep `benchmark_feedback_authorized=false`.
- [ ] Require `TRAIN_SELECT` for promote/rollback/HOLD evidence.

### Task 7: Bind rather than duplicate existing components

**Files:**
- Create: `src/pchsi/round_control/bindings.py`
- Test: `tests/round_control/test_bindings.py`

**Interfaces:**
- Consumes: repository root.
- Produces: hash-bound reuse registry.

- [ ] Bind Evidence Package to `reference_loop/analyzer_evidence_pack.py`.
- [ ] Bind Analyzer and Memory to their existing packages.
- [ ] Bind Research Planner to role-neutral/reference-trace/reference-round assets.
- [ ] Bind deterministic materialization to `reference_loop/approved_materialization.py`.
- [ ] Bind evaluator to `pchsi.evaluation`.
- [ ] Bind promotion/rollback to existing takeover/reference-round contracts.
- [ ] Bind Strong trace storage to existing distillation/reference-trace assets.
- [ ] Mark external training/rendering runtime bindings as deferred, not reimplemented.

### Task 8: Run compatibility dry run and build review bundle

**Files:**
- Execute: `30_BUILD_STAGE1_REVIEW.py`
- Produce: `STAGE1_GENERIC_ROUND_AUTOMATION_CONTROL_PLANE_REVIEW_V1.zip`

**Interfaces:**
- Consumes: new control plane plus existing takeover/reference-round/distillation/benchmark APIs.
- Produces: review manifest and next gate.

- [ ] Exercise all lifecycle transitions.
- [ ] Exercise Human-primary, Strong-primary, Local-primary authority profiles using synthetic takeover metrics.
- [ ] Exercise clean data gates including deliberate benchmark leakage rejection.
- [ ] Freeze a synthetic existing-format reference-round manifest.
- [ ] Build a synthetic existing-format local-role supervision dataset.
- [ ] Create a shared evaluation protocol and sealed benchmark result.
- [ ] Verify pilot semantic retention is forbidden.
- [ ] Verify train-side Strong trace localization retention is allowed.
- [ ] Verify promotion uses only `TRAIN_SELECT`.
- [ ] Publish review ZIP atomically.
- [ ] End with `STAGE1_CONCRETE_COMPONENT_RUNNER_BINDING_AND_HUMAN_STRONG_LOCAL_DRY_RUN`.
