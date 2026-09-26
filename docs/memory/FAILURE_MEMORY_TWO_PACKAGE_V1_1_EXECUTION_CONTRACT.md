# Failure Memory Two-Package Unified Execution Contract V1.1.1

## Authority chain

```text
Unit-4 code authority
0332971d88f1592575ba6b8197c9db5b54472a13

↓ docs-only V1.1 plan

↓ fixed-head plan-hardening commit

↓ PLAN_APPROVED_FAILURE_MEMORY_TWO_PACKAGE_V1_1

↓ fast-forward final plan head into main

↓ Package A implementation branch

↓ Package A closure

↓ Package B implementation branch
```

Production implementation never starts from a commit that lacks the approved plan/spec.

## Script storage

All ZIPs, external runners and execution logs live under:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts`

Git worktrees remain under:

`/data/run01/scwb204/sdar_repro/badcase/github_exports/`

## Package A phases

```text
A_BUILD
A0–A8
→ per-task commit/push/equality
→ cumulative code review
→ CODE_APPROVED_FAILURE_MEMORY_PACKAGE_A_V1
→ freeze real execution manifest
→ PACKAGE_A_EXECUTION_APPROVED
→ A9 real environment-only replay
→ real staging materialization
→ real source-integrity/descriptive eligibility
→ MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1
→ A10 closure
→ MEMORY_CAUSAL_TEST_INFRASTRUCTURE_READY
```

No real ALFWorld call before code approval + execution approval.

## Package B phases

```text
B-DIRECT BUILD
B0–B7
→ per-task commit/push/equality
→ PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_READY

optional separate scientific execution approval
→ matched-record train-development study

B-RETRIEVAL BUILD/EXECUTION
B8 partition
B9 Stage-0 query panel
B10 BM25
B11 E5
B12 RRF
B13 blind gold
B14 calibration
B15 independent retriever selection
B16 retrieval-bound Stage-1 DEV snapshot
B17 Stage-0 closure
→ PI1_MEMORY_ON_STAGE1_DEV_READY
```

The B-DIRECT scientific study and B-RETRIEVAL Stage-0 work are separate evidence lineages even when housed in one Package-B branch.

## Resume receipts

Every internal task produces an external receipt containing:
- task;
- parent SHA;
- task commit SHA;
- test commands/results;
- audit markers;
- push result;
- remote SHA;
- worktree cleanliness.

Resume starts at the first task without both a valid closure receipt and local/remote equality.

SSH disconnect does not cause completed tasks to be rerun.

## Git rules

- one scientific/engineering purpose per commit;
- push immediately after each task;
- no force push;
- no amend after push;
- no published reset/rebase;
- branch must remain linear descendant of approved base;
- integration after cumulative code approval only.

Git worktree isolation is required.

## Hard stops

Stop on:
- wrong branch/base;
- unexpected dirty path;
- invalid RED;
- failed focused/full test;
- schema mismatch;
- no-touch mismatch;
- forbidden model/policy/network call;
- source-state mismatch;
- ledger chain break;
- no-clobber destination already exists;
- snapshot/artifact hash mismatch;
- unauthorized access split;
- Package-A effect other than UNTESTED;
- FM3 exposure before prescriptive authority;
- remote divergence.

## Approval tokens

```text
DESIGN_APPROVED_FAILURE_MEMORY_TWO_PACKAGE_ACCELERATION_V1_1

PLAN_APPROVED_FAILURE_MEMORY_TWO_PACKAGE_V1_1

CODE_APPROVED_FAILURE_MEMORY_PACKAGE_A_V1
PACKAGE_A_EXECUTION_APPROVED
MEMORY_CAUSAL_TEST_INFRASTRUCTURE_READY

CODE_APPROVED_FAILURE_MEMORY_PACKAGE_B_DIRECT_V1
PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_READY
STAGE1_MATCHED_REPRESENTATION_ABLATION_APPROVED

PACKAGE_B_EXECUTION_APPROVED
CODE_APPROVED_FAILURE_MEMORY_PACKAGE_B_V1
PI1_MEMORY_ON_STAGE1_DEV_READY

STAGE1_TRAIN_DEV_MEMORY_ABLATION_APPROVED
RESULT_AUDIT_APPROVED_STAGE1_TRAIN_DEV_MEMORY_ABLATION
```
