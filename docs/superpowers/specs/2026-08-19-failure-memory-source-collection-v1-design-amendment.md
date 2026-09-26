# Failure Memory Source Collection V1 — Approved Design Amendment

Date: 2026-08-19

## Status

Approved design amendment for the gap discovered between formal Harness-OFF
SELECT evidence and the train-side `TRAIN_MEMORY_SOURCE` evidence required by
Failure Memory V1.

This document does not change the paper-level scientific claim, the frozen
Memory task-access partition, Package-A causal-test semantics, or Package-B
direct-representation study design.

## Why a dedicated source collection is required

The formal P4 Harness-OFF SELECT attempts are all bound to
`SELECT_SUMMARY_ONLY`. They have zero overlap with the frozen
`TRAIN_MEMORY_SOURCE` partition and therefore cannot be relabeled or reused as
active Failure Memory source evidence.

Failure Memory source collection is a separate train-side development activity:

`FAILURE_MEMORY_SOURCE_COLLECTION_V1`

It is not:
- a benchmark;
- a confirmatory evaluation;
- a Memory-ON experiment;
- a policy-selection experiment;
- a performance estimate.

The collected failures are only factual source evidence for later
human-registered failure windows and Failure Memory construction.

## Frozen source policy

The source policy is the existing primary Round-1 policy identity:

- logical condition: `P4-R1-Q2-BAD`
- checkpoint instance: `P4-R1-Q2-BAD-TRAIN17`
- training seed: `17`
- request protocol: normal strict R0 / RAW policy
- persistent Memory: OFF (`MEMORY_M0_V1` only)
- Harness: OFF
- evaluation/request seed for source collection: `17`

Policy identity is recovered from the frozen formal Train17 runtime authority.
Observed SELECT outcomes are not consulted when choosing the policy.

## Frozen task-access authority

Only records satisfying both are eligible:

- split = `train`
- access class = `TRAIN_MEMORY_SOURCE`

The corrected protected task-access authority remains:

`260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea`

The expected complete source population is exactly `2367` task/gamefile groups.

No `TRAIN_RETRIEVAL_DEV`, `valid_seen`, `valid_unseen`, or SELECT-only record may
enter source collection.

## Contract 1 — Freeze the complete source panel before any model execution

Before the first source-policy model call, publish one immutable
`FAILURE_MEMORY_SOURCE_PANEL_MANIFEST_V1` containing all 2367 source tasks.

For every entry it freezes:

- complete panel index;
- batch index;
- protected task-access line index and line SHA;
- task type;
- dataset-relative gamefile;
- absolute gamefile used by this execution;
- gamefile SHA-256;
- canonical task/gamefile group ID;
- deterministic order score.

Complete order:

1. group the 2367 source entries by task type;
2. within each task type sort by
   `SHA256("FAILURE_MEMORY_SOURCE_PANEL_ORDER_V1\0" + task_gamefile_group_id)`,
   then by task/gamefile group ID;
3. interleave the sorted task types in deterministic round-robin order:
   rank 0 from each type, rank 1 from each type, and so on;
4. assign contiguous panel indices only after the entire order is frozen.

This yields a single complete order. Any later batch continues from that same
order. No outcome-dependent re-ranking, re-sampling, replacement, or new random
draw is allowed.

The manifest additionally binds:

- exact source-collection code Git commit;
- exact pi1 runtime binding SHA;
- protected task-access authority SHA;
- source policy identity;
- batch size and stopping rule;
- explicit performance-estimand boundary.

## Contract 2 — Preserve all executed source cases

The source collection publishes every scientifically completed executed case as
a normal sealed attempt bundle and appends one immutable case receipt to the
complete source-collection ledger.

The ledger is a contiguous prefix of the frozen panel order. Every case receipt
binds:

- panel and batch index;
- task-access line identity;
- task/gamefile group identity;
- source task ID;
- execution attempt ID;
- exact attempt-bundle SHA;
- scientific outcome;
- termination reason;
- previous receipt SHA;
- `NO_PERFORMANCE_ESTIMAND`.

No successfully executed source case may be discarded because it was a success
or because it was not among the first three failures.

`FAILURE_MEMORY_SELECTED_FAILURE_PANEL_V1` is reference-only. It points to the
first three true failures in the frozen complete ledger order. It does not copy,
replace, or hide the rest of the source collection.

## Contract 3 — Explicit `NO_PERFORMANCE_ESTIMAND`

Every source-panel manifest, source-case receipt, selected-failure panel and
source-collection closure record states:

`NO_PERFORMANCE_ESTIMAND`

Source success/failure outcomes have exactly one authorized aggregate use:
evaluate the pre-frozen stopping condition after a complete batch.

They are forbidden from entering:

- benchmark tables;
- pi1 task-success estimates;
- policy-quality claims;
- model/checkpoint selection;
- hyperparameter selection;
- statistical confidence intervals or performance rates.

The source collection may record the cumulative number of failures solely as
evidence that the stopping threshold was or was not reached.

## Batch-complete stopping rule

Batch size:

`12`

Failure target:

`3`

Stopping rule:

`COMPLETE_BATCH_THEN_STOP_IF_CUMULATIVE_SOURCE_FAILURES_GTE_3_V1`

Procedure:

1. execute the next complete batch from the already frozen panel order;
2. preserve all case artifacts and append all case receipts;
3. only after the full batch is complete, inspect cumulative failures;
4. if cumulative failures >= 3, stop;
5. otherwise execute the next 12 tasks from the same frozen order;
6. if the complete panel is exhausted, stop after its final partial terminal
   batch.

There is no mid-batch stopping.

## Human failure-window registration

After source collection stops, choose the first three failures in frozen panel
order. These are only references into the complete collection ledger.

For each, a human reviewer must approve the factual window:

- relevant start model-call index;
- registered failure-onset model-call index;
- final model-call index;
- optional registered recovery start/final range.

The system may present traces and propose a boundary, but it may not create
`REGISTERED_FAILURE_SEQUENCE_WINDOW_V1` authority without the explicit human
approval.

The same approval packet may additionally provide descriptive, non-effect
assembly fields:

- activation condition;
- release/termination condition;
- optional non-applicability condition;
- optional candidate mechanism hypothesis;
- optional proposed recovery steps.

These remain registered boundaries / semantic hypotheses / proposals, not effect
evidence.

## After human approval

The already-built finalization stage may then mechanically perform:

human registration
→ `SEQUENCE_FAILURE_EXPERIENCE_V1`
→ descriptive procedural assembly registration
→ source-state replay registration
→ exact A9 manifests
→ `PACKAGE_A_EXECUTION_APPROVED`
→ real environment-only A9 replay
→ governed candidate materialization
→ four Package-A authority ledgers
→ immutable DEV descriptive snapshot
→ A10 Package-A seal
→ main fast-forward
→ Package-B implementation worktree.

Package A still creates no Benefit/Harm/prescriptive authority and performs no
Memory continuation experiment.

## Package-B handoff

The approved Package-B branch remains:

`implementation/failure-memory-package-b-policy-exposure-v1`

Package B begins with the direct matched representation lane before retriever
development.
