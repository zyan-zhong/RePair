# Failure Memory V1 Final Execution Design V1

Status: pre-outcome final execution protocol.

## Scope

This protocol closes only Failure Memory-owned implementation and scientific
stages. It does not implement a Hierarchical Analyzer, Training Researcher,
policy trainer, or Memory-OFF/Harness-OFF policy internalization evaluation.

The real live cell executor is a mechanical execution adapter. It may run the
frozen policy and environment, build the three role-specific Memory packs, and
record mechanical outcomes. It must never assign Q1--Q5 dispositions.

## Registered execution

### Stage 1B

- Population: the three previously registered Formal-A source decision states.
- Conditions per state: FM0, FM1, FM2, FM3.
- Cell count: 12.
- Purpose: source-state-local representation and effect evidence.

### Stage 2

- Population: 60 deterministic TRAIN_MEMORY_SOURCE tasks.
- Selection: first ten task identities in each of the six ALFWorld task
  families after sorting by frozen task-gamefile-group identity.
- Logical snapshots: S0, S1, S2, S3, exposing zero, one, two, or three
  governed records from the same immutable active snapshot.
- Round-active records use a prescriptive FM3 projection only when the frozen
  governance state establishes that authority; otherwise the controlled
  accumulation arm uses the governed descriptive FM2 projection. A registered
  Stage-1B/Stage-3 FM3 cell never silently falls back to FM2.
- Cell count: 240.
- No same-round Memory readback or evaluation writeback is permitted.

### Stage 3

- Population: all 140 valid_seen identities and all 134 valid_unseen
  identities from the protected task-access authority.
- Conditions: FM0, FM1, FM2, FM3.
- Cell count: 1,096.
- Registered primary split: valid_seen.
- valid_unseen is reported as a historically exposed standard OOD benchmark
  and cannot be described as fresh OOD.

## Frozen policy and runtime

The task policy is the existing pi1/Train17 checkpoint and exact runtime
identity recovered from prior formal SELECT evidence. The base model,
adapter, tokenizer, chat template, vLLM version, decoding contract, Runtime
Core, 60/30/3 budget, full admissible menu, and Harness-OFF behavior remain
fixed.

## Scientific authority

- Cells write only the exact five artifacts in
  LIVE_CELL_EXECUTOR_CONTRACT_V1.
- Complete-population recomputation is performed by Package 2.
- Stage 1B, Stage 2, and Stage 3 are run in order.
- Q4 and Q5 remain handoffs only.
- Tests, smoke runs, and synthetic fixtures cannot substitute for real
  outcomes.
- Result seal requires the post-result human audit token:
  RESULT_AUDIT_APPROVED_FAILURE_MEMORY_V1_MEMORY_OWNED_CLOSURE_V2.

## Git publication

The delivery ZIP is not committed. The repository receives:

1. the final execution protocol and real executor implementation;
2. after result audit approval, compact result authorities, tables,
   narratives, handoffs, approval evidence, and a result-seal manifest.

The main branch is not updated by this package.

## Human approval gates

This delivery does not collapse critical approvals:

1. `CODE_APPROVED_FAILURE_MEMORY_LIVE_CELL_EXECUTOR_V1` follows fixed-head
   review of the real executor.
2. `EXECUTION_APPROVED_FAILURE_MEMORY_LIVE_STAGES_V1` authorizes real Stage
   1B/2/3 execution after all pre-outcome inputs are frozen.
3. `RESULT_AUDIT_APPROVED_FAILURE_MEMORY_V1_MEMORY_OWNED_CLOSURE_V2` follows
   review of real outcomes and authorizes the Git result seal.

No later gate may be supplied before its evidence exists.
