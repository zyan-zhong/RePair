# Failure Memory Source Collection → Package B Unified Execution Plan

Date: 2026-08-19

## Goal

Close the last train-side source-evidence gap without contaminating formal
SELECT or evaluation data, then finish Package A and bootstrap Package B with
the minimum number of human interaction gates.

## Delivery model

One ZIP contains all code and all stage scripts.

There are only two unavoidable human scientific/authority gates:

1. code approval after the new source-collection implementation passes
   RED→GREEN, Memory/full regression, static review, commit/push and fixed-head
   code review;
2. factual failure-window approval for the first three source failures.

No new code ZIP is required after either gate.

## Stage 1 — Build and seal source-collection implementation

Implement:

- `pchsi.memory.source_collection`
- complete source-panel manifest builder
- dataset-root identity discovery
- pi1 Train17 runtime-identity discovery
- source collection runner
- human registration panel builder
- schemas and tests
- this design amendment and plan

Required tests:

- full 2367-panel freeze;
- deterministic outcome-free complete ordering;
- immutable panel SHA;
- all executed case receipts retained;
- short-write-safe append-only collection ledger;
- no mid-batch stopping;
- selected failure panel references first three failures in complete ledger;
- explicit `NO_PERFORMANCE_ESTIMAND`;
- no SELECT task evidence reuse;
- runtime discovery must not inspect observed success/failure for model choice.

After focused/Memory/full regression and schema/static audit, create one commit:

`Add Failure Memory train-side source collection`

Push and verify local/remote equality.

Then rerun a fresh fixed-head source-collection code review.

Gate:

`CODE_APPROVED_FAILURE_MEMORY_SOURCE_COLLECTION_V1`

## Stage 2 — Freeze source panel and execute source collection

Before any model execution:

1. verify corrected protected task-access artifact;
2. discover and fully SHA-audit the unique local dataset root;
3. recover exact pi1 Train17 runtime identity from frozen formal identity
   evidence only;
4. validate frozen local base model/tokenizer/chat template and LoRA;
5. publish runtime binding;
6. build and publish the complete 2367-entry source panel manifest;
7. hash-freeze all pre-execution evidence.

Only then launch the vLLM runtime and source collection.

Execute complete 12-case batches. Preserve every executed case and append every
case receipt. Check the stopping rule only after the complete batch is
published.

After stopping, publish:

- complete collection ledger;
- source collection closure;
- reference-only first-three-failure panel;
- human registration panel ZIP.

No performance estimate is computed.

## Stage 3 — Human factual registration

Review exactly the three selected failures.

Approve factual window indices and descriptive assembly text.

The human approval artifact is immutable and becomes the authority referenced by
the generated failure-window registrations and assembly boundaries.

Gate:

`HUMAN_FAILURE_MEMORY_REGISTRATION_APPROVED_V1`

## Stage 4 — Finalize Package A and bootstrap Package B

From the approved three cases:

1. create canonical `REGISTERED_FAILURE_SEQUENCE_WINDOW_V1`;
2. mechanically materialize `SEQUENCE_FAILURE_EXPERIENCE_V1`;
3. create deterministic descriptive procedural assembly registrations;
4. construct exact registered source-state replay objects from the source
   evidence at each approved relevant-start state;
5. create exact replay/materialization manifests;
6. run pre-execution audits;
7. authorize and execute A9 environment-only reconstruction;
8. materialize governed candidates and all four authority ledgers;
9. publish and rehash-audit `MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1`;
10. run A10 no-touch/tests/docs closure;
11. commit/push and verify remote equality;
12. fast-forward main only if main is an ancestor;
13. create and push:
    `implementation/failure-memory-package-b-policy-exposure-v1`;
14. create Package-B worktree at:
    `/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-failure-memory-package-b-v1`.

Final Package-A marker:

`MEMORY_CAUSAL_TEST_INFRASTRUCTURE_READY`

Package-B handoff marker:

`PACKAGE_B_IMPLEMENTATION_READY`
