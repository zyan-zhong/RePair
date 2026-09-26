# Failure Memory Token-Budget Feasibility + B-DIRECT Amendment V1

Date: 2026-08-19

```text
STATUS = APPROVED_FROM_USER_REVIEW
SCOPE = PRE-OUTCOME TOKEN-BUDGET CALIBRATION + B-DIRECT
CHANGE_AUTHORITY = EXPLICIT USER/RESEARCHER DIRECTIVE
```

## 1. Motivation

Package A closed successfully with three governed descriptive Memory records.

Real observed representation sizes:

```text
FM1 raw:
514 / 357 / 323 tokens under the old 256 ceiling
→ 3/3 PROJECTION_INELIGIBLE_TOKEN_BUDGET

FM2 structured:
180 / 186 / 184 tokens
→ 3/3 ELIGIBLE
```

FM1 safety passed in all three cases. The failure is representational
feasibility, not Policy-view safety.

The historical Package-A snapshot remains immutable evidence of the old 256
contract. It is never rewritten.

Before any π1 Memory-ON scientific execution, Package B must calibrate a
replacement token-budget contract using train-side representation-length
statistics only.

## 2. Scientific boundary

The token-budget calibration is explicitly:

```text
NO_PERFORMANCE_ESTIMAND
NO_MEMORY_ON_EXECUTION
NO_VALID_SEEN_ACCESS
NO_VALID_UNSEEN_ACCESS
NO_BENEFIT_HARM_AUTHORITY
NO_MODEL_SELECTION_FROM_TASK_SUCCESS
```

Allowed evidence:

- `TRAIN_MEMORY_SOURCE` tasks only;
- the already frozen complete source-panel order;
- frozen π1 / Train17 identity;
- Memory OFF;
- Harness OFF;
- failure trajectories selected only because they are failures in the frozen
  source-panel order;
- representation lengths;
- static Policy-view safety;
- calibration-only Analyzer localization/description output.

Forbidden evidence:

- π1 Memory-ON success;
- benchmark result;
- Benefit/Harm;
- valid_seen;
- valid_unseen;
- downstream representation-ablation result.

## 3. Calibration sample

Target:

```text
first 30 failures in the already frozen TRAIN_MEMORY_SOURCE panel order
```

The existing 12 executed source cases are reused; they are not rerun.

If fewer than 30 failures exist in the already executed prefix, continue the
same frozen source-panel order in complete 12-case batches.

Every newly executed case is preserved.

Stopping is evaluated only after a complete batch.

The source extension is not a performance estimate.

## 4. Calibration-only Hierarchical Analyzer

Trajectory segmentation belongs to the Hierarchical Analyzer under
`PROJECT_ARCHITECTURE_FREEZE_V1`.

For token-budget calibration only, a frozen Analyzer processes each of the first
30 source failures and outputs:

- `status = ANALYZED | ABSTAIN`;
- relevant-start model-call index;
- failure-onset model-call index;
- final model-call index;
- concise activation cues;
- concise failure-pattern hypothesis;
- concise release cues;
- optional non-applicability cues.

The Analyzer output is:

```text
CALIBRATION_ONLY_ANALYZER_PROPOSAL
```

It is not a registered factual Memory boundary and may not enter the active
Failure Experience Library.

The Analyzer:

- must use a frozen prompt;
- must use a frozen model name;
- must use strict JSON-schema output;
- may not see Memory-ON performance;
- may not see Benefit/Harm labels;
- may not propose exact current actions;
- may abstain.

The first 30 failure identities are fixed before Analyzer calls.

No failure is replaced because the Analyzer abstained.

## 5. Calibration representations

### 5.1 FM1 calibration view

FM1 is the exact complete Analyzer-proposed registered-equivalent window:

```text
relevant_start ... final
```

Every event in that window is retained.

For the raw arm:

```text
event truncation = FORBIDDEN
LLM compression = FORBIDDEN
post-hoc excerpt selection = FORBIDDEN
```

The historical FM1 event-dropping fallback is retired for Package B.

If the complete window does not fit the frozen operating ceiling, FM1 is
unavailable.

### 5.2 FM2 calibration view

The calibration-only FM2-shaped view uses the same six-field descriptive schema:

```text
activation_cues
failure_pattern
revalidate_on
release_cues
non_applicability_cues
recovery_procedure=[]
```

Its semantic content comes only from the frozen calibration Analyzer output.

It is used only to estimate representation length.

It does not become active Memory authority.

## 6. Candidate ceilings and frozen selection rules

### 6.1 Single-record candidates

```text
256
384
512
640
768
```

Selection rule:

> Select the smallest candidate that contains at least 90% of valid,
> safety-clean, whole-window FM1 calibration views.

Require at least 20 valid FM1/FM2 calibration records among the first 30
failures.

If no candidate satisfies the rule, hard stop before Memory-ON execution.

### 6.2 Library-total candidates

```text
384
512
640
768
```

`max_record_count = 3`.

Valid calibration records remain in frozen failure order.

Create consecutive, non-overlapping triples of FM2 payloads and measure the
token count of the exact canonical JSON array that the Policy would receive.

Selection rule:

> Select the smallest library-total candidate that contains at least 90% of
> these whole-record three-item packs.

If no candidate satisfies the rule, hard stop before Memory-ON execution.

No mid-record truncation is allowed.

## 7. Token-budget contract

Publish:

```text
FAILURE_MEMORY_TOKEN_BUDGET_CONTRACT_V1
```

It binds:

- source-panel SHA;
- calibration failure-panel SHA;
- Analyzer prompt SHA;
- Analyzer model identity;
- tokenizer identity/revision;
- candidate ceilings;
- valid calibration count;
- exact FM1 length vector;
- exact FM2 length vector;
- exact library-pack length vector;
- coverage target;
- selected single-record ceiling;
- selected library-total ceiling;
- max record count;
- no-truncation rules;
- `NO_PERFORMANCE_ESTIMAND`;
- contract SHA.

Once written and committed, the contract may not be changed after Memory-ON
results appear without an explicit new protocol amendment.

## 8. Historical Package-A snapshot

Historical Package-A closure:

```text
sealed head:
d6257c2e28f35f400d60b5ac835e1ebf70762dd5

historical snapshot:
df271ba7527ebaee104a888d82533832ada0a4aab8735f717767e5d1b1d51cc4
```

remains immutable historical truth under the old 256 ceiling.

It is not deleted or rewritten.

After the new token-budget contract is frozen, it is not the active Package-B
development snapshot.

## 9. FM1 builder amendment

Package B changes FM1 construction so that the raw arm is the complete factual
window.

Old behavior that dropped whole events to fit a ceiling is not used for the
Package-B raw arm.

FM1 remains fail-closed:

- Policy-view safety failure → unavailable;
- source/governance failure → unavailable;
- complete-window token overflow → unavailable;
- no truncation;
- no rewrite.

The generic projection token-count envelope supports the calibrated single-record
candidate range through 768 tokens.

This change exists on Package B only; historical Package-A commits remain
unchanged.

## 10. New active DEV snapshot

After the budget contract is frozen:

1. reuse the same three Package-A governed records;
2. reuse the same factual source experiences and human registrations;
3. rebuild FM1 using the complete raw window and the new single-record ceiling;
4. rebuild FM2 with the new single-record ceiling;
5. rerun deterministic Policy-view safety;
6. publish a new immutable snapshot:

```text
MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V2
```

V2 binds:

- historical Package-A snapshot SHA;
- token-budget contract SHA;
- tokenizer identity/revision;
- governed record SHA;
- retrieval-key SHA;
- rebuilt FM1 SHA and disposition;
- rebuilt FM2 SHA and disposition;
- deterministic ordered membership;
- snapshot SHA.

No FM3 membership is allowed.

## 11. A9 dependency audit

Package-A A9 environment-only replay is not automatically rerun.

Before reuse, publish:

```text
FAILURE_MEMORY_A9_TOKEN_BUDGET_DEPENDENCY_AUDIT_V1
```

It must verify that the environment-only replay authority depends on:

- source task/gamefile;
- source fingerprint;
- environment runtime;
- executed prefix;
- reconstructed state;

and does not depend on:

- Policy-visible FM1 token ceiling;
- FM1 payload bytes;
- FM2 payload bytes;
- active Memory snapshot.

If this independence check passes, the environment-only replay evidence is
reused and the new snapshot receives a rebind receipt.

If not, stop and require a targeted A9 rerun.

## 12. Package-B B0 dependency binding

B0 binds:

- Package-A sealed head;
- historical Package-A snapshot;
- token-budget contract;
- A9 dependency audit;
- active snapshot V2;
- effect authority `UNTESTED`;
- Package-A exposure `NOT_EXPOSED_PACKAGE_A`.

B0 must not silently replace historical Package-A evidence.

## 13. B1 snapshot loader and availability

The B1 loader:

- verifies full snapshot SHA;
- rejects symlinks;
- verifies exact file census;
- rehashes all member artifacts;
- rejects FM3;
- exposes explicit availability:

```text
FM1_ELIGIBLE
FM1_UNAVAILABLE_TOKEN_BUDGET
FM1_UNAVAILABLE_OTHER
FM2_ELIGIBLE
FM2_UNAVAILABLE
```

Unavailable is never treated as Memory-OFF.

## 14. B2 whole-projection packing

### Direct

```text
DIRECT_SINGLE_RECORD
record_count = exactly 1
limit = token_budget_contract.single_record_hard_ceiling
```

### Library

```text
LIBRARY
record_count = 0..3
limit = token_budget_contract.library_total_hard_ceiling
```

Rules:

- whole record only;
- no partial truncation;
- deterministic order;
- stop before the first record that would exceed the library limit;
- record actual packed token count.

## 15. B3 common Memory-aware prompt

Frozen field order:

```text
TASK_GOAL_JSON
CURRENT_OBSERVATION_JSON
EXECUTED_TRANSITIONS_JSON
RETRIEVED_FAILURE_EXPERIENCES_JSON
VISIBLE_ADMISSIBLE_COMMANDS_JSON
INTERFACE_FEEDBACK_JSON
OUTPUT_REQUIREMENT
```

M0:

```text
RETRIEVED_FAILURE_EXPERIENCES_JSON=[]
```

Memory-ON:

```text
RETRIEVED_FAILURE_EXPERIENCES_JSON=[whole frozen projections]
```

Historical `RAW_POLICY_PROMPT_V1` and `MEMORY_M0_V1` remain unchanged.

## 16. B4 Runtime bridge and exposure

The bridge may:

- construct the Memory-aware prompt;
- call existing Runtime Core precondition/generation-processing functions;
- record immutable exposure evidence.

It may not:

- repair actions;
- canonicalize actions;
- reorder/filter menu;
- change BudgetState;
- call Analyzer;
- perform retrieval unless a frozen result is supplied;
- infer whether the model used the Memory.

## 17. B5 canonical single-cue representation

Authority:

```text
SINGLE_CUE_POLICY_VIEW_V1
```

It binds:

- same Memory lineage/version;
- source FM2 payload SHA;
- `failure_pattern_index = 0`;
- exact cue text;
- exact Policy-view safety report;
- exact token count;
- build disposition;
- canonical SHA.

No LLM rewrite.
No post-result cue selection.
No alternate cue search.

## 18. B6 direct applicability

B6 uses only mechanically checkable registered Policy-visible cues.

Possible results:

```text
APPLICABLE
NOT_APPLICABLE
CONFLICTING
UNCERTAIN
```

No Analyzer call.
No hidden phase/subgoal inference.
No semantic paraphrase matching.

## 19. B7 matched representation cells

For one exact Memory lineage/version:

```text
M0 = common empty slot
M1 = FM1 complete raw view
M2 = SINGLE_CUE_POLICY_VIEW_V1
M3 = FM2 structured descriptive view
```

A matched record is eligible only if:

- FM1 is ELIGIBLE;
- single-cue is ELIGIBLE;
- FM2 is ELIGIBLE;
- all record bindings are identical;
- all pass the active token-budget contract;
- no arm performs independent retrieval.

Unavailable arms are explicitly recorded.

Two markers remain separate:

```text
B_DIRECT_INFRASTRUCTURE_READY
```

means the engineering chain is complete.

```text
PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_READY
```

requires a mechanical readiness audit with at least three matched
FM1/single-cue/FM2 records under the active snapshot.

No readiness marker authorizes a scientific execution. Real π1 Memory-ON
execution still requires a separate Package-B execution approval.

## 20. External research context

This amendment does not treat larger context as intrinsically better.

The purpose is to avoid a ceiling so small that the scientific representation
comparison cannot be instantiated while still keeping a pre-outcome,
data-calibrated bound.

The budget remains deliberately constrained and is frozen before Memory-ON
results.
