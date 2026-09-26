# Failure Memory Package A — Causal-Test Infrastructure Implementation Plan V1.1.1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build and qualify the write, identity, governance, source-state replay, staging materialization and immutable DEV descriptive-snapshot infrastructure required before any Memory effect experiment.

**Architecture:** Package A extends `src/pchsi/memory/` without changing legacy E1/SELECT identity or Runtime Core semantics. Code is tested with injected/fake adapters first. After cumulative code approval, a separate execution phase may run ALFWorld only for environment-only prefix replay, then materialize governed DEV candidates and a descriptive snapshot. No policy inference or Memory effect continuation occurs in Package A.

**Tech Stack:** Python 3.12 standard library, pytest, existing `pchsi.evaluation` contracts, JSON Schema, existing spawn-only ALFWorld adapter, Bash runners, Git worktrees.

**Spec:** `docs/superpowers/specs/2026-08-18-failure-memory-two-package-v1_1-design-amendment.md`

## Authority

Unit-4 code authority:

`0332971d88f1592575ba6b8197c9db5b54472a13`

Implementation plan authority:

`FINAL_PLAN_HARDENING_HEAD`

The Package-A implementation branch must be created only after the final plan-hardening commit has been fast-forwarded to `main`.

The implementation branch base is therefore:

```text
final approved plan commit
```

not the older Unit-4 code commit.

Unit-4 production bytes are still reviewed over:

```text
91c349039c318c330e3803671a0faa16101575ff
..
0332971d88f1592575ba6b8197c9db5b54472a13
```

## Global Constraints

- Dedicated branch: `implementation/failure-memory-package-a-causal-test-infrastructure-v1`.
- Dedicated worktree: `/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-failure-memory-package-a-v1`.
- External scripts/ZIP/logs root: `/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts`.
- Unit-4 production files remain byte-identical unless the fixed-head review finds and separately approves a blocker correction.
- Real ALFWorld use is limited to the post-code-approval environment-only replay qualification.
- No policy/model inference.
- No Memory continuation.
- No positive effect, Benefit, Harm or prescriptive promotion.
- Effect status remains `UNTESTED`.
- Candidate materialization is DEV-only and staging-first.
- FM3 empty-recovery artifacts may be built as staging integrity artifacts but are not Package-A snapshot members and are not Policy-exposure eligible.
- Package-A snapshot authority is `MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1`, not formal `MEMORY_LIBRARY_SNAPSHOT_V1`.
- Constructors must not read current wall-clock time. Any event timestamp is explicit caller-supplied evidence metadata.
- Every internal task closes with one single-purpose commit, push, remote equality and clean worktree.
- Any failed task stops later tasks.
- No force push, amend-after-push, reset of published history, or branch rewrite.

## Historical no-touch files

Hash before A1 and again before A10:

```text
src/pchsi/evaluation/runtime_core.py
src/pchsi/evaluation/budget.py
src/pchsi/evaluation/raw_policy_parser.py
src/pchsi/evaluation/raw_policy_prompt.py
src/pchsi/evaluation/run_schedule.py
src/pchsi/evaluation/condition_run_schedule.py
src/pchsi/evaluation/condition_execution_binding.py
src/pchsi/evaluation/select_execution_identity.py
src/pchsi/evaluation/policy_condition.py
```

`MEMORY_M0_V1` remains byte/semantic unchanged.

---

## Task A0 — Unit-4 cumulative fixed-head review

**Files**
- Create: `docs/audits/FAILURE_MEMORY_POLICY_PROJECTION_FIXED_HEAD_REVIEW_V1.md`
- Modify: `docs/memory/FAILURE_MEMORY_V1_LEDGER.md`

**Checks**
- exact Unit-4 head and ancestry;
- five production modules;
- four projection schemas;
- four focused test files;
- policy-visible exact-identity leakage;
- current-menu oracle lint;
- FM1 bounded whole-event packing;
- FM2/FM3 descriptive-byte identity;
- strict reload safety recomputation;
- no source-state replay/retriever/model/environment execution surface.

Run:

```text
pytest -q tests/memory
pytest -q
python -m compileall -q src tests
git diff --check
```

Produce either:

`CODE_APPROVED_FAILURE_MEMORY_POLICY_PROJECTION_V1`

or a blocker list.

Commit:

`Audit Failure Memory Policy projection fixed head`

Marker:

`PACKAGE_A_TASK_A0_UNIT4_FIXED_HEAD_REVIEW_CLOSED`

---

## Task A1 — Source-state immutable contracts

**Create**
- `src/pchsi/memory/source_state_contracts.py`
- strict schemas for source fingerprint, replay source, replay report and branch prompt identity
- `tests/memory/test_source_state_contracts.py`

`SourceDecisionStateFingerprintV1` binds:

```text
source task/gamefile
source bundle
source policy condition
executed-prefix identity
observation SHA
menu-sequence SHA
MEMORY_M0_V1 SHA
interface feedback
complete BudgetState
model-call index
canonical historical non-Memory base-input SHA
derived fingerprint SHA
```

The stored fingerprint SHA is recomputed during construction/reload.

RED tests:
- exact fields;
- invalid SHA;
- wrong derived SHA;
- negative indices;
- invalid BudgetState;
- branch role outside `MEMORY_OFF|MEMORY_ON`;
- projection bytes included in source fingerprint;
- persistent-Memory slot included in base-input hash;
- non-deterministic serialization.

Commit:

`Define Failure Memory source-state identity contracts`

Marker:

`PACKAGE_A_TASK_A1_SOURCE_STATE_CONTRACTS_CLOSED`

---

## Task A2 — Deterministic source-state replay engine

**Create**
- `src/pchsi/memory/source_state_replay.py`
- `tests/memory/test_source_state_replay.py`

Public interface:

```python
def replay_source_decision_state_v1(
    *,
    source: RegisteredReplaySourceV1,
    adapter: ReplayAdapterV1,
) -> SourceStateReplayReportV1:
    ...
```

The adapter surface is exactly:

```text
reset exact gamefile
step exact action
close
```

Tests must prove:
- fresh reset;
- exact action strings/order;
- each observation SHA;
- each menu-sequence SHA;
- each score/done/won;
- each environment-step index;
- terminal mismatch fail-closed;
- missing/extra transition fail-closed;
- close on success/failure;
- no model or policy regeneration.

Policy-side rehydration restores from frozen evidence:
- M0;
- interface feedback;
- full BudgetState;
- model-call index.

Commit:

`Implement deterministic Failure Memory source-state replay`

Marker:

`PACKAGE_A_TASK_A2_SOURCE_STATE_REPLAY_CLOSED`

---

## Task A3 — Memory-specific paired execution identity

**Create**
- `src/pchsi/memory/memory_execution_identity.py`
- `configs/memory/schemas/memory_bound_replay_cell_v1.json`
- `tests/memory/test_memory_execution_identity.py`

Factory-only pair creation:

```python
def build_memory_bound_replay_pair_v1(...) -> MemoryBoundReplayPairV1:
    ...
```

The two cells must share:
- pair ID;
- source fingerprint;
- source round/bundle/task/call;
- policy checkpoint;
- M0 hash;
- observation/menu;
- BudgetState;
- snapshot identity;
- continuation seed.

Only active difference:
- OFF: empty projection tuple;
- ON: exact frozen projection tuple.

Direct cell construction with inconsistent derived identity is rejected.

Legacy E1/SELECT identities are forbidden.

Commit:

`Bind Failure Memory paired execution identity`

Marker:

`PACKAGE_A_TASK_A3_MEMORY_EXECUTION_IDENTITY_CLOSED`

---

## Task A4 — Four append-only authority ledgers

**Create**
- `event_ledger.py`
- `effect_ledger.py`
- `promotion_ledger.py`
- `exposure_ledger.py`
- four schemas
- `tests/memory/test_memory_ledgers.py`

Rules:
- canonical line bytes;
- previous-entry hash chain;
- unique entry ID;
- write-once/no-clobber;
- file fsync + parent-directory fsync semantics;
- append failure preserves previous valid bytes;
- event time is an explicit input field;
- constructors never call current clock.

Package-A effect ledger accepts only:

```text
UNTESTED
```

Package-A promotion ledger may record only descriptive DEV governance decisions and may not claim Benefit/Harm.

Tests explicitly reject:
- `POSITIVE`;
- `HARM`;
- `PRESCRIPTIVE_ELIGIBLE_DEV`;
- formal-evaluation access;
- later positive overwrite of earlier harm;
- broken hash chain;
- duplicate entry.

Commit:

`Add append-only Failure Memory authority ledgers`

Marker:

`PACKAGE_A_TASK_A4_MEMORY_LEDGERS_CLOSED`

---

## Task A5 — Source integrity and descriptive eligibility

**Create**
- `source_integrity.py`
- `descriptive_eligibility.py`
- schemas
- focused tests

Source integrity validates every bound source experience:
- ID;
- canonical bytes/hash;
- ordering;
- registered ranges;
- source refs;
- no unresolved source mismatch.

Descriptive eligibility requires:
- source integrity PASS;
- sequence fidelity;
- procedural completeness;
- authority typing;
- allowed DEV access;
- Policy-view safety;
- no contamination blocker.

Eligibility produces a new governed record version.

It never mutates the candidate artifact.

Commit:

`Gate descriptive Failure Memory eligibility`

Marker:

`PACKAGE_A_TASK_A5_DESCRIPTIVE_ELIGIBILITY_CLOSED`

---

## Task A6 — Staging candidate materializer code

**Create**
- `src/pchsi/memory/candidate_materialization.py`
- `scripts/memory/materialize_failure_memory_candidates_v1.py`
- schema/manifest types
- focused tests

Modes:

```text
--validate-manifest
--dry-run
--execute
--audit-existing
```

Code tests never run real data.

Execution requires:
- exact manifest SHA;
- registered input roots;
- no symlink input;
- no unregistered source;
- write-once paths;
- content-addressed identity;
- no policy/model/environment/network/retrieval call.

Generated staging set:
- procedural record;
- retrieval key;
- FM1;
- FM2;
- empty-recovery FM3 integrity artifact.

All are `STAGING_CANDIDATE`.

FM3 is not snapshot-eligible in Package A.

Commit:

`Materialize governed Failure Memory staging candidates`

Marker:

`PACKAGE_A_TASK_A6_CANDIDATE_MATERIALIZATION_CODE_CLOSED`

---

## Task A7 — DEV descriptive snapshot code

**Create**
- `src/pchsi/memory/dev_descriptive_snapshot.py`
- `scripts/memory/build_failure_memory_dev_snapshot_v1.py`
- `configs/memory/schemas/memory_dev_descriptive_snapshot_v1.json`
- focused tests

Authority name:

`MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1`

Membership may reference only governed descriptive-eligible versions.

It binds:
- record full-artifact hash;
- retrieval-key full-artifact hash;
- FM1 full-artifact hash;
- FM2 full-artifact hash;
- access policy;
- projection schema identities;
- tokenizer ceiling contract if already known;
- deterministic ordered membership;
- snapshot SHA.

It does not claim:
- selected retriever;
- embeddings/index;
- thresholds;
- prescriptive recovery;
- formal evaluation authority.

FM3 is excluded.

Rollback is pointer change to an older immutable snapshot; old snapshot bytes never change.

Commit:

`Build immutable Failure Memory DEV descriptive snapshots`

Marker:

`PACKAGE_A_TASK_A7_DEV_SNAPSHOT_CODE_CLOSED`

---

## Task A8 — Environment-only qualification runner code

**Create**
- `scripts/memory/qualify_source_state_replay_v1.py`
- CLI tests

Modes:

```text
--validate-manifest
--execute-environment-only
--audit-existing
```

The build/test phase:
- does not launch ALFWorld;
- does not import/call policy clients;
- does not read Memory projection bytes into policy prompts;
- uses fake/injected replay adapters;
- runs focused tests, `tests/memory`, full pytest, compileall and static import/call scans.

Commit:

`Prepare Failure Memory environment-only replay qualification`

Marker:

`PACKAGE_A_TASK_A8_REPLAY_QUALIFICATION_CODE_CLOSED`

After A8:
- cumulative fixed-head source review;
- `CODE_APPROVED_FAILURE_MEMORY_PACKAGE_A_V1`;
- freeze Package-A real execution manifest;
- `PACKAGE_A_EXECUTION_APPROVED`.

No real ALFWorld call occurs before both tokens.

---

## Task A9 — Real Package-A execution

Order is mandatory.

### A9.1 Environment-only replay qualification

For every registered qualification case:

```text
historical source fingerprint
=
independent reconstruction A
=
independent reconstruction B
```

No policy/model inference and no Memory continuation.

Mismatch:
`SOURCE_STATE_RECONSTRUCTION_FAILED`
and stop.

### A9.2 Real staging materialization

Run exact manifest-bound candidate materializer.

### A9.3 Real source-integrity and eligibility audit

For every real candidate:
- run source-integrity report;
- run descriptive-eligibility report;
- append governance/event evidence;
- if PASS, create a new governed descriptive version;
- if FAIL/UNCERTAIN, remain outside snapshot.

### A9.4 Build DEV descriptive snapshot

Snapshot membership contains only governed descriptive-eligible versions.

Verify:
- every effect = `UNTESTED`;
- no Package-A snapshot FM3 member;
- no nonempty recovery exposed;
- exact census/disposition;
- no unregistered file;
- immutable hashes and receipts.

Marker:

`PACKAGE_A_TASK_A9_REAL_EXECUTION_CLOSED`

---

## Task A10 — Cumulative closure

Update:
- `docs/memory/FAILURE_MEMORY_V1_LEDGER.md`
- `docs/memory/FAILURE_MEMORY_V1_IMPLEMENTATION_ROADMAP.md`
- create `docs/audits/FAILURE_MEMORY_PACKAGE_A_CLOSURE_V1.md`

Run:
- full Memory tests;
- full applicable repository regression;
- compileall;
- diff check;
- strict schema inventory;
- historical no-touch hash equality;
- branch ancestry;
- per-task commit-purpose audit;
- remote equality;
- clean worktree.

Commit:

`Seal Failure Memory causal-test infrastructure`

Final marker:

`MEMORY_CAUSAL_TEST_INFRASTRUCTURE_READY`

This marker means only that causal-test infrastructure is qualified.
