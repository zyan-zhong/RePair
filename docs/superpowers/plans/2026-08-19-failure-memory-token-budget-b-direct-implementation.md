# Token-Budget Feasibility → B-DIRECT Unified Implementation Plan V1

Date: 2026-08-19

## Goal

Starting from the current remotely equal Package-B head, complete the approved
pre-outcome token-budget amendment, create the new active descriptive snapshot,
bind Package B to it, and implement B-DIRECT B1–B7 without running a Memory-ON
scientific experiment.

## Required starting state

Package-B branch:

`implementation/failure-memory-package-b-policy-exposure-v1`

Expected start head:

`29d59472b9872c3661997d3b425bba7c03bd581e`

Package-A sealed head:

`d6257c2e28f35f400d60b5ac835e1ebf70762dd5`

Historical snapshot:

`df271ba7527ebaee104a888d82533832ada0a4aab8735f717767e5d1b1d51cc4`

Source-panel SHA:

`1d84ac1dc76a01495fab2aa344e077cf35fe54d32d7164e85a240996608730ea`

## Execution discipline

Every implementation task follows:

```text
RED
→ implementation
→ focused GREEN
→ relevant regression
→ exact scope
→ single-purpose commit
→ push
→ fetch
→ local == remote
→ clean worktree
```

Shell runners use:

```bash
set +e
set +u
set +o pipefail
```

For important pipelines:

```bash
command | tee log
RC="${PIPESTATUS[0]}"
```

## Task TB0 — Freeze token-budget amendment design

Install and commit:

- token-budget feasibility design amendment;
- this implementation plan.

Commit:

`Freeze Failure Memory token-budget feasibility amendment`

No execution.

## Task TB1 — Generic token-budget contract and complete-window FM1

Create:

- `src/pchsi/memory/token_budget_contract.py`;
- tests for candidate ceilings and selection rules.

Modify Package-B code only:

- `projection_common.py` supports calibrated single-record ceilings through 768;
- `matched_raw_view.py` removes event-dropping fallback for the Package-B raw
  arm and measures the complete registered window.

Tests prove:

- 256 remains valid;
- 640/768 are valid only as explicit ceilings;
- >768 is rejected;
- complete-window FM1 never removes events to fit;
- overflow returns token-ineligible;
- safety failures remain fail-closed.

Commit:

`Add pre-outcome Failure Memory token-budget contracts`

## Task TB2 — Calibration source extension code

Create a calibration-only source runner that:

- consumes the already frozen source panel;
- reuses existing first 12 source cases;
- continues from panel index 12;
- executes Memory-OFF / Harness-OFF π1;
- preserves every additional executed case;
- stops only after a complete 12-case batch once at least 30 total failures are
  available;
- writes the first 30 failure identities in frozen panel order;
- states `NO_PERFORMANCE_ESTIMAND`.

No Memory-ON.

Commit:

`Prepare train-side token-budget calibration source collection`

After code review, run the extension using the site Slurm contract.

## Task TB3 — Calibration-only Analyzer and length ledger

Create:

- frozen Analyzer prompt;
- strict JSON-schema result;
- analyzer runner;
- calibration length builder.

For exactly the first 30 frozen failures:

- no replacement;
- Analyzer may abstain;
- build complete-window FM1 calibration payload;
- build FM2-shaped descriptive calibration payload;
- run static Policy-view safety;
- measure exact Policy tokenizer counts;
- preserve Analyzer request/response identities.

Require at least 20 valid calibration records.

No calibration output becomes active Memory authority.

Commit code:

`Analyze Failure Memory token-budget feasibility`

Then execute the Analyzer and length materialization.

## Task TB4 — Freeze token-budget contract

Candidate sets:

```text
single: 256,384,512,640,768
library: 384,512,640,768
```

Coverage target:

`0.90`

Choose the smallest qualifying candidate using the approved rules.

Publish and commit:

`configs/memory/failure_memory_token_budget_contract_v1.json`

Commit:

`Freeze Failure Memory token budgets before Memory-ON`

This commit is the no-outcome budget-freeze authority.

## Task TB5 — Rebuild active snapshot V2 and A9 dependency audit

Create:

- `dev_descriptive_snapshot_v2.py`;
- rebuild CLI;
- A9 token-budget dependency audit;
- tests.

Rebuild only:

- FM1;
- FM2;
- active snapshot metadata.

Reuse:

- governed records;
- retrieval keys;
- factual source experiences;
- human registrations;
- Package-A environment-only replay evidence if dependency audit passes.

Historical Package-A snapshot remains immutable.

Publish:

`MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V2`

Commit the dependency binding metadata, not large external evidence.

Commit:

`Bind Package B to the calibrated Failure Memory snapshot`

Marker:

`PACKAGE_B_TASK_B0_DEPENDENCY_CLOSED`

## Task B1 — Snapshot loader and availability

Create:

`src/pchsi/memory/dev_snapshot_loader.py`

Tests:

- exact snapshot SHA;
- file census;
- no symlink;
- no FM3;
- representation availability preserved.

Commit:

`Load calibrated immutable Failure Memory DEV snapshots`

Marker:

`PACKAGE_B_TASK_B1_DEV_SNAPSHOT_LOADER_CLOSED`

## Task B2 — Whole-projection packing

Create:

`projection_packing.py`

Use only active budget contract.

Commit:

`Pack Failure Memory projections with frozen budgets`

Marker:

`PACKAGE_B_TASK_B2_PACKING_CLOSED`

## Task B3 — Memory-aware prompt

Create:

`memory_augmented_prompt.py`

Commit:

`Build the Failure Memory augmented Policy prompt`

Marker:

`PACKAGE_B_TASK_B3_MEMORY_PROMPT_CLOSED`

## Task B4 — Runtime bridge and exposure evidence

Create:

- `memory_runtime_bridge.py`;
- `policy_exposure.py`;
- schema and tests.

Commit:

`Bridge Failure Memory exposure to Runtime Core`

Marker:

`PACKAGE_B_TASK_B4_RUNTIME_EXPOSURE_CLOSED`

## Task B5 — Canonical single-cue baseline

Create:

- `single_cue_failure_summary.py`;
- strict schema and tests.

Authority:

`SINGLE_CUE_POLICY_VIEW_V1`

Commit:

`Build deterministic single-cue Failure Memory views`

Marker:

`PACKAGE_B_TASK_B5_SINGLE_CUE_SUMMARY_CLOSED`

## Task B6 — Mechanical applicability

Create:

`applicability_gate.py`

No Analyzer.

Commit:

`Gate direct Failure Memory applicability`

Marker:

`PACKAGE_B_TASK_B6_DIRECT_APPLICABILITY_CLOSED`

## Task B7 — Matched representation cells

Create:

- `representation_ablation.py`;
- CLI/materializer;
- schemas/tests.

Produce per-record availability for M0/M1/M2/M3.

Emit:

`B_DIRECT_INFRASTRUCTURE_READY`

only after engineering review.

Emit:

`PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_READY`

only if at least three current snapshot records mechanically have:

```text
FM1 ELIGIBLE
single-cue ELIGIBLE
FM2 ELIGIBLE
same lineage/version
```

No scientific execution.

Commit:

`Materialize matched Failure Memory representation cells`

## Final fixed-head audit

Run:

- all new B-DIRECT tests;
- all Memory tests;
- full repository regression;
- compileall;
- `git diff --check`;
- forbidden surface scan;
- remote equality.

Final allowed state:

```text
B_DIRECT_INFRASTRUCTURE_READY
PACKAGE_B_DIRECT_CODE_READY
```

Scientific execution remains separately gated.
