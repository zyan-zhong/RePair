# Failure Memory V1 Implementation Roadmap

## Authority

Approved design:

`docs/superpowers/specs/2026-08-14-failure-memory-v1-design.md`

Approved integration commit:

`b3cb816e2e727600f79f1947a77c73ce87d4a97c`

This roadmap does not authorize implementation or scientific execution.

Each implementation unit requires its own written plan and human
approval before production code is written.

## Architecture decision

Failure Memory V1 is implemented in a new sibling package:

```text
src/pchsi/memory/
```

with tests in:

```text
tests/memory/
```

and Memory-specific configuration/materialization tooling under:

```text
configs/memory/
scripts/memory/
```

Historical evaluation protocols remain separate.

## Historical no-touch boundary

Unless a later explicitly approved plan states otherwise, the following
historical contracts remain byte-unchanged:

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

The Memory study must not be represented as a legacy E1, P1 or SELECT
cell.

`MEMORY_M0_V1` remains unchanged.

## Reusable evidence surfaces

The new Memory package may read or use public contracts from:

```text
canonical_evidence.py
action_trace.py
policy_call_evidence.py
public_transition.py
episode_artifact.py
episode_sequence.py
task_manifest.py
distillation_access.py
```

Reuse does not grant permission to rewrite historical evidence or
reinterpret historical semantics.

## Implementation sequence

### 1. Task access and primary Policy identity

Freeze:

- train Memory-source tasks;
- train retrieval-development tasks;
- project-held-out valid_seen tasks;
- historically exposed valid_unseen benchmark tasks;
- Train17 primary worker;
- Train31/Train47 secondary policy-realization audit identities.

No Memory record is created.

### 2. Factual failure-sequence reconstruction

Create deterministic factual sequence records from immutable episode
evidence.

No semantic mechanism or recovery is invented.

### 3. Canonical procedural Failure Memory

Create the versioned Memory record and authority types.

Enforce the procedural-completeness gate.

### 4. Policy projection and safety

Create matched raw, descriptive and prescriptive Policy views.

Enforce leakage and action-oracle prohibitions.

### 5. Source-state replay and Memory execution identity

Implement independent state reconstruction and Memory-specific paired
branch identity.

Do not modify legacy E1/SELECT execution identity.

### 6. Event, effect, promotion and exposure ledgers

Create four append-only evidence streams with separate authority.

### 7. Immutable Memory snapshots

Create read-only versioned library snapshots and rollback-by-pointer.

### 8. Retrieval-development separation and blind gold labels

Partition the train retrieval-development pool into calibration,
retriever-selection validation and frozen multi-round evaluation roles.

### 9. Retriever candidates

Implement preregistered lexical, dense and hybrid candidates.

No retriever is selected from cache availability.

### 10. Threshold and abstention selection

Apply the frozen safety-first lexicographic selection rule.

### 11. Common Memory-aware Policy interface

Create a new prompt interface with an explicit persistent-Memory slot.

Do not change `RAW_POLICY_PROMPT_V1`.

### 12. Stage-0 quality, safety and retrieval validation

Audit provenance, sequence fidelity, procedural completeness, leakage,
applicability, reproducibility and cost.

### 13. Single-record paired effect test

Run direct frozen-projection source-state paired interventions.

Live retrieval is not used.

### 14. FM0–FM3 train-development study

Compare no Memory, matched raw episode, structured descriptive Memory
and gated prescriptive Memory.

### 15. Controlled multi-round Memory accumulation

Keep the policy and the complete processing pipeline frozen.

Only Memory population/version/snapshot and deterministically derived
index content may change.

### 16. Statistical analysis and reporting

Implement task-level paired inference and the preregistered reporting
contract.

### 17. Formal ID/OOD evaluation

Use one frozen package for project-held-out valid_seen and the standard
historically exposed valid_unseen benchmark.

No cross-split method change or writeback is allowed.

### 18. Secondary policy-realization robustness

After the complete method is frozen, run Train31 and Train47 under the
registered FM0-versus-FM3 secondary audit.

## Closure rule

Every implementation unit closes independently:

```text
approved plan
→ RED
→ GREEN
→ focused tests
→ full applicable regression
→ deterministic audit
→ authoritative artifacts
→ ledger update
→ single-purpose commit
→ push
→ local/remote equality
→ clean worktree
```

A later unit may not silently repair a scientific decision made by an
earlier closed unit.

## Closed unit

### Unit 1 — Task access and primary Policy identity foundation

Task-access scientific foundation status:

`SCIENTIFICALLY_CLOSED`

Foundation seal commit:

`7403745e51ca634aa1c0c8ea7df56a77afa74240`

Authoritative task-access identities:

```text
protected SHA-256
=
260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea

sanitized SHA-256
=
e7dc8ddd1795b4ed51fdf62735a49620c8bc03470b86de220180d45a336c5228

TRAIN_MEMORY_SOURCE
=
2367

TRAIN_RETRIEVAL_DEV
=
1186

VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED
=
140

VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
=
134
```

Detailed task-access seal:

`docs/audits/FAILURE_MEMORY_TASK_ACCESS_FOUNDATION_SEAL_V1.md`

Primary Policy identity foundation status:

`SCIENTIFICALLY_CLOSED`

Primary Policy identity:

```text
PRIMARY_FROZEN_MEMORY_WORKER
=
P4-R1-Q2-BAD-TRAIN17

SECONDARY_POLICY_REALIZATION_AUDIT
=
TRAIN31
TRAIN47

PRIMARY_POLICY_CONTRACT_SHA256
=
048b131d57c8080592e8855d483ced33c30b0362eec644a545a5f3ec29e86f82
```

Detailed Primary Policy identity seal:

`docs/audits/FAILURE_MEMORY_PRIMARY_POLICY_IDENTITY_FOUNDATION_SEAL_V1.md`

Combined Unit-1 foundation status:

`SCIENTIFICALLY_CLOSED`

Both Unit-1 requirements are now closed:

- authoritative task/gamefile access;
- frozen primary/secondary Policy identity.

## Current next unit

### Unit 2 — Factual failure-sequence reconstruction

The next implementation unit is:

`SEQUENCE_FAILURE_EXPERIENCE_V1`

Its purpose is to reconstruct deterministic factual multi-step failure
sequences from immutable episode evidence.

This unit must not invent:

- semantic failure mechanisms;
- recovery prescriptions;
- applicability hypotheses;
- causal claims.

The detailed Unit-2 implementation plan must receive separate human
approval before production implementation begins.

## Package A closed — causal-test infrastructure ready

The real source-collection / human-registration / exact-input / environment-only
replay chain is complete for three train-side π1 failures.

A representation-coupling audit established that all three FM1 raw episodic
views exceed the frozen 256-token ceiling while all three FM2 descriptive views
remain independently safe and eligible. Package A therefore preserves FM1 as a
canonical token-ineligible artifact instead of blocking the governed descriptive
record or rewriting the raw view.

The immutable DEV descriptive snapshot preserves that availability state and
contains no FM3.

Next package: Package B direct Policy exposure and retrieval development.
