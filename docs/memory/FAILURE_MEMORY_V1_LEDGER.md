# Failure Memory V1 Ledger

## Current state

`DESIGN_APPROVED_FAILURE_MEMORY_V1`

## Plain-language status

The historical Round-1 assets have been consolidated.

Failure Memory V1 has received explicit final human approval. The final-review amendments and four final narrow hardenings are part of the approved design. The system has not been implemented.

The primary V1 objective is now:

```text
frozen policy
+
persistent external procedural Failure Memory
+
controlled multi-round Memory improvement
```

Policy-weight internalization is a deferred optional extension.

## Design document

[Failure Memory V1 Design](../superpowers/specs/2026-08-14-failure-memory-v1-design.md)

## Original design-candidate commit

`81bda87bb36c49e2351b7b0233616e909d09f659`

## First amendment commit

`e9adb3b37586670bcd4406dbe185f84ef9afdd07`

## Final hardened design commit

`6b84488ca08f730f11427dcd0f1611ad6408ceb7`

The approval-seal commit is identified through Git history; this ledger does not self-embed its own commit SHA.

## Repository design base

`b30e188f70890ff808a874c05c0ddfcc98973a7c`

## Verified design inputs

### Historical asset consolidation

Commit:

`b30e188f70890ff808a874c05c0ddfcc98973a7c`

### Task exposure census

Local ALFWorld population:

```text
train        = 3553
valid_seen   = 140
valid_unseen = 134
```

Historical exposure:

```text
valid_unseen exposed = 134 / 134
valid_seen exposed   = 0 / 140 in registered Round-1 evidence
train exposed        = 0 / 3553 in registered Round-1 evidence
```

### Task-access design candidate

Schema:

`MEMORY_TASK_ACCESS_MANIFEST_CANDIDATE_V2_1`

SHA-256:

`6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a`

Population:

```text
TRAIN_MEMORY_SOURCE                                      = 2367
TRAIN_RETRIEVAL_DEV                                      = 1186
VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED                  = 140
VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED = 134
```

This is a design input, not an execution authorization.

### Task-access SHA authority correction

Approved correction decision:

`DESIGN_APPROVED_FAILURE_MEMORY_TASK_ACCESS_SHA_AUTHORITY_CORRECTION_V1`

Preserved historical candidate identity:

```text
historical_design_candidate_sha256
=
6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a

role
=
PRESERVED_HISTORICAL_DESIGN_CANDIDATE

execution_authority
=
false
```

Proposed finalized exact-contract protected-regeneration authority:

```text
approved_exact_contract_protected_sha256
=
260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea
```

The correction does not change task membership, task/gamefile identity,
partition semantics, role semantics, or the frozen populations
`2367 / 1186 / 140 / 134`.

The authority correction must be supported by machine-auditable
`TASK_ACCESS_SHA_AUTHORITY_CORRECTION_EVIDENCE_V1` binding the three
independent reproductions and the preserved failed-V2 incident evidence.

Current authorization boundary:

```text
CORRECTION_DESIGN = APPROVED
CORRECTION_PLAN = APPROVED
TASK1_CORRECTION_EVIDENCE_IMPLEMENTATION = IMPLEMENTED_AND_VERIFIED
REAL_TASK_ACCESS_MATERIALIZATION = NOT_APPROVED
REPOSITORY_ARTIFACT_CLOSURE = NOT_APPROVED
```

The original Failure Memory design commit:

`b3cb816e2e727600f79f1947a77c73ce87d4a97c`

remains design ancestry.

The correction-focused commit supersedes only the old digest-authority
binding. It is identified through Git history and is the authority to be
bound by the later correction-aware V2 execution config.

### Superseded task-access candidates

The following candidate identities are retained as historical design
records but are not the current design basis:

```text
MEMORY_TASK_ACCESS_MANIFEST_CANDIDATE_V1
sha256 = 7eca1ea5073a4c0f3ca5ba0fb7e846b83fff2316d26736350d7ccc14610d399b

MEMORY_TASK_ACCESS_MANIFEST_CANDIDATE_V2
sha256 = 18cf4125f155b9657d93d3c0b32207e02eeb2ab9a726eab49c8fb6089009383a
```

### Retrieval capability

Current environment contains:

- Transformers;
- PyTorch;
- NumPy/SciPy/scikit-learn;
- a partial local `intfloat/e5-base-v2` cache.

The E5 cache is incomplete and is not a valid retriever freeze.

No dense retriever is selected by this design.

The Stage 0 retriever-selection protocol compares a small preregistered
lexical, dense and hybrid candidate set using train-only retrieval
development data.

## Approved-in-principle architecture

```text
immutable raw evidence
→ Sequence Failure Experience
→ Procedural Failure Memory
→ semantic annotations
→ retrieval key and Policy views
→ immutable snapshot
→ gated retrieval
→ frozen task policy
```

## Primary experiments

```text
FM0 = no persistent Memory
FM1 = matched raw episodic view
FM2 = structured descriptive Memory
FM3 = gated prescriptive Memory
```

## Primary research stages

```text
Stage 0 = quality / safety / retrieval development
Stage 1 = record and train-development Memory effects
Stage 2 = controlled multi-round external Memory improvement
Stage 3 = frozen valid_seen + valid_unseen evaluation
```

## Deferred extension

```text
parametric policy internalization
=
DEFERRED_OPTIONAL_EXTENSION
```

It is not required for Failure Memory V1 success.

## Final-review amendment decisions

The six final-review amendments are incorporated.

### State and prompt identity

```text
SOURCE_DECISION_STATE_FINGERPRINT_V1
!=
BRANCH_PROMPT_EXPOSURE_IDENTITY_V1
```

F0/F1 must begin from the same source state.

Their final rendered prompts intentionally differ through the
empty-versus-filled persistent-Memory projection.

### Primary policy contract

```text
primary worker selection
=
minimum policy-training seed
from frozen {17,31,47}

primary worker
=
Train17
```

Source-record paired tests use the original source checkpoint.

Train31 and Train47 perform preregistered final FM0-versus-FM3
robustness audits with no method feedback and no best-of-checkpoint
selection.

### Stage 2 attribution

The complete Memory processing pipeline is frozen across the primary
multi-round accumulation curve.

Only Memory population, record versions, snapshot identity and
deterministically derived index content may change.

### Statistical authority

```text
project-held-out primary confirmation
=
valid_seen FM3 vs FM0

standard historically exposed OOD benchmark
=
valid_unseen FM3 vs FM0
```

The two splits are reported separately.

### Project-held-out terminology

`valid_seen` is held out from this project's Failure Memory development.

No pretraining-level non-exposure claim is made.

### Access regeneration and retrieval gold

Task-access regeneration must reproduce candidate SHA-256:

`6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a`

Retrieval gold labels use a retriever-blind rubric, independent second
pass, registered adjudication and append-only evidence.

Unresolved cases remain uncertain and permit abstention.


## Final narrow-hardening decisions

The final human review identified four narrow design hardenings.

### Terminology

All scientific prose uses:

`PROJECT_HELD_OUT_ID_CONFIRMATION`

for `valid_seen`.

This means held out from this project's Failure Memory development.

It does not claim pretraining-level non-exposure.

### Procedural completeness

`PROCEDURAL_COMPLETENESS_GATE_V1` prevents reusable Memory from
collapsing into:

```text
bad action
→ corrected action
```

The temporal failure process, state/feedback relation and
applicability/release boundary must remain represented.

### Retrieval-gold candidate view

`MEMORY_RETRIEVAL_GOLD_CANDIDATE_VIEW_V1` is descriptive-only.

Initial applicability annotators do not see recovery guidance, effect
status, promotion state, Analyzer confidence or retriever information.

Applicability and recovery quality remain separate judgments.

### Execution schedule and aggregation

`STAGE2_ROUND_SCHEDULE_V1` prohibits performance-dependent stopping and
requires all scheduled snapshots to be reported.

`LIBRARY_EVALUATION_TASK_AGGREGATION_V1` uses one preregistered primary
library-evaluation seed per task and FM condition.

Additional seeds are secondary robustness evidence and cannot redefine
the primary task-level binary result.

## Final human approval

Decision:

`DESIGN_APPROVED_FAILURE_MEMORY_V1`

Approval date:

`2026-08-15`

Approved authority:

```text
Failure Memory V1 final hardened design
commit 6b84488ca08f730f11427dcd0f1611ad6408ceb7
```

The approval authorizes implementation planning.

It does not authorize implementation, Memory materialization, ALFWorld
execution, external model calls or scientific execution.

## Authorization after design approval

Authorized now:

- integrate the approved design into its parent documentation branch;
- create a dedicated implementation-planning branch;
- write and review the Failure Memory V1 implementation plan.

Still prohibited:

- building Memory records;
- implementing a Memory builder;
- downloading or selecting a retriever for scientific use;
- calling an Analyzer;
- running ALFWorld;
- modifying Runtime Core;
- modifying historical E1/SELECT schedules;
- revealing `valid_seen`;
- executing formal `valid_unseen`;
- Memory-assisted policy execution;
- scientific execution.

## Implementation planning

Master roadmap:

`docs/memory/FAILURE_MEMORY_V1_IMPLEMENTATION_ROADMAP.md`

Current detailed implementation plan:

`docs/superpowers/plans/2026-08-15-failure-memory-task-access-policy-identity-v1.md`

Current planning status:

`PLAN_APPROVED_FAILURE_MEMORY_TASK_ACCESS_POLICY_IDENTITY_V1`

The current detailed plan covers only:

- final task-access regeneration;
- final task-role manifest;
- Train17 primary worker identity;
- Train31/Train47 secondary robustness identities.

It does not authorize Failure Memory records, retrieval, model calls,
environment execution or scientific evaluation.

## First implementation Plan approval

Decision:

`PLAN_APPROVED_FAILURE_MEMORY_TASK_ACCESS_POLICY_IDENTITY_V1`

Approval date:

`2026-08-15`

Approved Plan basis:

`010e525a90d546999b65e31c3389e3d687727e73`

Authorized now:

- create the dedicated implementation branch;
- run the pre-implementation baseline test suite;
- write synthetic RED tests;
- implement only the approved code candidate under the new
  Memory-specific package, test, script and configuration paths;
- commit and push the reviewed code candidate.

Still prohibited:

- real ALFWorld dataset materialization;
- real Round-1 policy/checkpoint materialization;
- committed protected held-out regeneration artifacts;
- Memory-record construction;
- Memory retrieval;
- model calls;
- environment execution;
- scientific execution.

The code candidate must be pushed and reviewed before either real
read-only materializer may run.

## Next action

1. commit and push this Plan approval seal;
2. create
   `implementation/failure-memory-task-access-policy-identity-v1`
   from the exact approval-seal commit;
3. run the full repository baseline test suite;
4. begin TDD Task 1 by writing only the synthetic task-access RED
   tests;
5. confirm that the RED tests fail for the expected missing module and
   behavior.

Real dataset/checkpoint materialization and scientific execution remain
unauthorized.

---

## Task-access foundation closure — 2026-08-16

Status:

```text
FAILURE_MEMORY_FOUNDATION_TASK_ACCESS
=
SCIENTIFICALLY_CLOSED
```

Foundation seal commit:

`7403745e51ca634aa1c0c8ea7df56a77afa74240`

Authoritative materialization:

```text
record_count = 3827

TRAIN_MEMORY_SOURCE = 2367
TRAIN_RETRIEVAL_DEV = 1186

VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED = 140

VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED = 134
```

Protected task-access SHA-256:

`260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea`

Sanitized task-access SHA-256:

`e7dc8ddd1795b4ed51fdf62735a49620c8bc03470b86de220180d45a336c5228`

Dataset source-integrity PRE/POST fingerprint:

`d657703df1033a9797e7e9a18b3eb989e49dd3391a468d1a65f6edff3e609e24`

The SHA-authority incident is resolved for the task-access foundation.

This closure does not establish Failure Memory effectiveness.

Current next implementation unit:

`SEQUENCE_FAILURE_EXPERIENCE_V1`

Production implementation of that unit remains blocked until its
implementation plan receives explicit human approval.

---

## Primary Policy identity foundation closure — 2026-08-17

Status:

FAILURE_MEMORY_PRIMARY_POLICY_IDENTITY
=
SCIENTIFICALLY_CLOSED

Approved source-code head:

`1a0feeef8085ba124fa79e72c38fea90b812d9f9`

Frozen source root seal:

`6dd3ad3389869d6f929af24283589f2e22f4c687a800072af16bb6f23b5092f8`

Primary policy:

`P4-R1-Q2-BAD-TRAIN17`

Secondary policy-realization audit:

`P4-R1-Q2-BAD-TRAIN31`

`P4-R1-Q2-BAD-TRAIN47`

Primary policy contract SHA-256:

`048b131d57c8080592e8855d483ced33c30b0362eec644a545a5f3ec29e86f82`

Execution manifest SHA-256:

`e88b66e512e47d3ee15f955238d0b9cc225e7e54a7c910b936c84c6f9c8de8e7`

Source PRE/POST identity was byte-equal.

No policy execution, ALFWorld execution, Memory construction, retrieval,
training or benchmark evaluation occurred.

Together with the task-access foundation seal, Failure Memory
implementation Unit 1 is now fully closed.

Current next unit remains:

`SEQUENCE_FAILURE_EXPERIENCE_V1`

The hardened Unit-2 plan identity remains:

`d8f1410bd12ea2730479dc3200dae46b0e7c047e`

with plan SHA-256:

`e60509e00400f61606624392330faab44bd3b904eab8a4ed582b76e9ce4cced0`

---

## Unit 2 / Task 1 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Task:

`Source-access and registration contracts`

Approved Unit-2 plan:

`d8f1410bd12ea2730479dc3200dae46b0e7c047e`

Approved Unit-2 plan SHA-256:

`e60509e00400f61606624392330faab44bd3b904eab8a4ed582b76e9ce4cced0`

Implementation base:

`45a5e9df9dfcffe79dee28ceff52f951a51bbff6`

Implemented contracts:

- `SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1`
- `REGISTERED_FAILURE_SEQUENCE_WINDOW_V1`
- `SourceRecordPointerV1`

TDD evidence:

- RED: 17 expected failures from missing Unit-2 contracts;
- focused GREEN: 17 passed;
- task-access authority regression: 72 passed;
- full regression: `1045 passed in 89.91s (0:01:29)`.

Artifact identities:

```text
sequence_failure_experience.py
SHA-256 =
29f3ade138d3787f2413709d9ce07d9988982c16e0b50ddf2db17aa8fac49037

test_sequence_failure_experience.py
SHA-256 =
e43040957931a592eee60678e1b203706ac4c76bd68eb4e1d890d17b309c303f

RED console log
SHA-256 =
14052840316a038ba999f41388b5329af13ed50bd9327cf7c183dc4c60deee04

focused GREEN log
SHA-256 =
f4c54f560d4852dbd7713391230713c64fc2dfc590330f04cb75ce91e8be1ded

authority regression log
SHA-256 =
47a5dbfc7f0e7efc74e2c7e32ce13edbad0c55285c842ee76ee10367ebc81794

full regression log
SHA-256 =
7d9cbc2b6aba128a7c8d3a8ce27479a44e82b9604d446957d4a253c1d1d34ed6
```

Audit results:

- `TASK1_PRE_CLOSURE_SCOPE_PASS`
- `TASK1_HISTORICAL_TRACKED_FILES_NO_TOUCH_PASS`
- `TASK1_STATIC_SCOPE_AUDIT_PASS`
- `TASK1_DETERMINISTIC_CONTRACT_AUDIT_PASS`

Scientific boundary:

- no sequence reconstruction;
- no failure-mechanism inference;
- no recovery generation;
- no Procedural Failure Memory;
- no retrieval;
- no Policy projection;
- no ALFWorld execution;
- no model execution;
- no real sequence materialization.

Next implementation task:

`Task 2 — Canonical factual experience wire contract`

Task 2 has not started.

---

## Unit 2 / Task 2 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Approved Unit-2 plan:

`d8f1410bd12ea2730479dc3200dae46b0e7c047e`

Approved Unit-2 plan SHA-256:

`e60509e00400f61606624392330faab44bd3b904eab8a4ed582b76e9ce4cced0`

Task parent:

`aca46a6dda4ac1d5e75a1674be54344ddeaf934e`

Verification:

- focused TDD cycle: PASS;
- full regression: `1060 passed in 305.30s (0:05:05)`;
- compile: PASS;
- scoped diff/status audit: PASS;
- local Git bundle backup: created after commit.

Implementation detail:

Implemented the immutable factual wire contract: SequenceFailureEventV1, SequenceFailureRelevantStartV1, SequenceFailureObservedEndV1 and SequenceFailureExperienceV1, with strict JSON parsing, canonical serialization and domain-separated experience identity. No source binding or builder was added in this task.

Scientific boundary:

- no ALFWorld execution;
- no model call;
- no Analyzer execution;
- no retrieval;
- no Procedural Failure Memory;
- no real sequence materialization.

Remote publication was subsequently recovered through the verified GitHub SSH-over-443 channel. The Task-2 commit `2e18978235499667e7c4bd76d71277c2bec35915` was published before Task 3 began; later Task-3 entry/remote-parent checks independently verified that exact remote identity.

---

## Unit 2 / Task 3 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Approved Unit-2 plan:

`d8f1410bd12ea2730479dc3200dae46b0e7c047e`

Approved Unit-2 plan SHA-256:

`e60509e00400f61606624392330faab44bd3b904eab8a4ed582b76e9ce4cced0`

Task parent:

`2e18978235499667e7c4bd76d71277c2bec35915`

Implementation:

Bound Sequence Failure Experience inputs to existing immutable
EpisodeArtifact, ActionTrace, PolicyCallEvidence, PublicTransition,
AttemptBundle, task-access and registered-range authorities.

The existing complete-episode sequence validator is invoked before
registered-range slicing.

Verification:

- original package RED: 6 expected missing-source-binding failures;
- original package GREEN: 38 passed;
- supplemental corrected parent-replay RED: 11 selected tests failed
  at the exact Task-2 parent with the expected missing-source-binding
  marker;
- the supplemental replay is recorded as conformance evidence and is
  not represented as original chronological TDD authorship;
- corrected supplemental GREEN: 11 passed;
- final focused suite: `49 passed in 1.01s`;
- final full repository regression: `1077 passed in 153.06s (0:02:33)`;
- compile: PASS;
- whitespace audit: PASS;
- static forbidden-execution-surface audit: PASS;
- Task-4/Task-5 premature-surface audit: PASS;
- historical evaluation / closed foundation no-touch audit: PASS.

Supplemental frozen-plan coverage explicitly verifies:

- invalid complete episode rejected before slicing;
- PolicyCall / ActionTrace observation mismatch;
- PolicyCall / ActionTrace admissible-menu mismatch;
- PolicyCall / ActionTrace raw-response mismatch;
- PolicyCall / ActionTrace BudgetState-before mismatch;
- task identity mismatch;
- attempt identity mismatch;
- registered range outside source episode;
- noncontiguous source-call sequence;
- registered recovery outside source episode;
- transition/model-call binding mismatch.

Publication gate:

This Task-3 commit is closed only after the resume runner performs a
fast-forward-only, non-force publication through the verified GitHub
SSH-over-443 channel and proves exact local/remote branch equality.

Scientific boundary:

- no deterministic sequence reconstruction yet;
- no failure-mechanism inference;
- no recovery guidance;
- no Procedural Failure Memory;
- no retrieval;
- no model call;
- no ALFWorld execution;
- no real historical sequence materialization.

Next implementation task:

`Task 4 — Deterministic factual reconstruction`

Task 4 has not started.

---

## Unit 2 / Task 4 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Approved Unit-2 plan:

`d8f1410bd12ea2730479dc3200dae46b0e7c047e`

Approved Unit-2 plan SHA-256:

`e60509e00400f61606624392330faab44bd3b904eab8a4ed582b76e9ce4cced0`

Task parent:

`8b7a3f8c636f936b65da2ff7f96c4f5ed4d9cf7c`

Implementation:

Implemented deterministic factual reconstruction through
`build_sequence_failure_experience_v1(...)`.

The builder validates complete source evidence before reconstruction,
preserves exact registered model-call order, binds the complete preceding
prefix, constructs one factual event per included policy call, attaches
only exact public transitions, derives environment-step coverage from
source evidence, enforces the registered-end future-information rule,
retains exact source-record/member hashes and returns immutable canonical
V1 output.

Verification:

- original package RED: 5 expected missing-reconstruction failures;
- original package GREEN before supplement: 54 passed;
- supplemental frozen-plan parent-replay RED: 8 expected
  missing-reconstruction failures at the exact Task-3 parent;
- supplemental frozen-plan GREEN: 8 passed;
- final focused suite: `62 passed in 2.69s`;
- final full repository regression: `1090 passed in 156.99s (0:02:36)`;
- compile: PASS;
- whitespace audit: PASS;
- whole-source-validation-first source review: PASS;
- no-order-rewrite source review: PASS;
- forbidden execution-surface audit: PASS;
- historical evaluation / closed foundation no-touch audit: PASS.

Supplemental reconstruction coverage verifies:

- exact registered call order;
- missing policy attempt rejected;
- no unregistered recovery invented;
- registered recovery range preserved without widening;
- complete terminal fields when episode termination lies inside range;
- exact source-member hashes and source-record pointers;
- changed exact source bytes change experience identity;
- environment-step identity is derived from source evidence rather than
  model-call arithmetic;
- executed visible-state-change disposition is factual and deterministic.

Publication gate:

This commit is considered closed only after the execution wrapper performs
a non-force fast-forward push through the verified GitHub SSH-over-443
channel and proves exact local/remote branch equality.

Scientific boundary:

- no Failure Memory mechanism inference;
- no recovery quality judgment;
- no Procedural Failure Memory;
- no retrieval;
- no model call;
- no ALFWorld execution;
- no real historical sequence materialization.

Next implementation task:

`Task 5 — Read-only materializer candidate and static audit`

Task 5 has not started.

---

## Unit 2 / Task 5 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Approved Unit-2 plan:

`d8f1410bd12ea2730479dc3200dae46b0e7c047e`

Approved Unit-2 plan SHA-256:

`e60509e00400f61606624392330faab44bd3b904eab8a4ed582b76e9ce4cced0`

Task parent:

`3450e2620a7a12a1ac411e2dbb19e156b0c3c94f`

Implementation:

Added the write-once offline
`materialize_sequence_failure_experience_v1.py`
candidate.

The candidate accepts only explicit attempt-directory, registration,
protected task-access manifest, protected-manifest line index and output
inputs. It validates the frozen protected-manifest identity, requires
TRAIN_MEMORY_SOURCE, requires the exact five-member attempt bundle
including policy_calls.jsonl, reconstructs through the already-closed
Task-4 builder and writes exact canonical bytes with no-clobber semantics.

Verification:

- original package RED: 6 expected missing-materializer failures;
- original package GREEN before supplement: 68 passed;
- supplemental frozen-plan parent-replay RED: 12 expected
  missing-materializer failures at the exact Task-4 parent;
- supplemental frozen-plan GREEN: 12 passed;
- final focused suite: `80 passed in 1.89s`;
- final full repository regression: `1108 passed in 173.04s (0:02:53)`;
- compile: PASS;
- whitespace audit: PASS;
- explicit-input CLI audit: PASS;
- protected task-access role audit: PASS;
- exact attempt-bundle/member audit: PASS;
- source filesystem-creation-order stability audit: PASS;
- canonical output round-trip audit: PASS;
- no-clobber and symlink audit: PASS;
- forbidden model/environment/network/process/discovery surface audit: PASS;
- closed Task-4 and historical-source no-touch audit: PASS.

Publication gate:

This Task-5 commit is considered closed only after a non-force
fast-forward publication through the verified GitHub SSH-over-443
channel and exact local/remote branch equality.

Unit-2 implementation state after publication:

`SEQUENCE_FAILURE_EXPERIENCE_V1`
implementation candidate is complete.

This is code-candidate completion only.

Still NOT authorized:

- real Round-1 sequence materialization;
- Failure Memory record materialization;
- Analyzer execution;
- retrieval;
- ALFWorld execution;
- model execution;
- Memory-assisted policy execution;
- scientific execution.

Next gate:

independent fixed-head source review for the exact Unit-2 implementation
head, followed only if approved by:

`CODE_APPROVED_FAILURE_MEMORY_SEQUENCE_EXPERIENCE_V1`
---

## Unit 3 / Task 6 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Design approval:

`DESIGN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Implementation-plan approval:

`PLAN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Approved implementation-plan SHA-256:

`143f8a0f0ac7d9c55390a89c9b7734e401e54cc595f6544aeda9beb9715bee8f`

Task parent:

`cc8156d0b159c731fbc6abf43b71a4dba7b59e5c`

Verification:

- focused TDD cycle: `11 passed in 0.12s`;
- full repository regression: `1123 passed in 272.62s (0:04:32)`;
- compile / strict syntax checks: PASS;
- scoped diff/status audit: PASS;
- forbidden execution-surface audit: PASS;
- historical evaluation and closed Unit-1/Unit-2 production no-touch audit: PASS;
- non-force fast-forward publication and local/remote equality are required
  by the same task runner after this commit is created.

Implementation detail:

Defined Memory authority/reference primitives, exact Unit-2 factual sequence bindings, assembly-registration provenance, typed previous-record lineage binding, stable lineage/version record identity and immutable procedural provenance. The first full-suite attempt in this fresh linked worktree exposed a pre-existing ignored native-test prerequisite: the security tests require native/s1_backend_probe/build/pchsi-s1-backend-probe to exist before their collection order reaches the reproducibility test that builds it. The resume runner deterministically bootstrapped that ignored prerequisite using the repository's own reproducible-build environment, then reran the complete regression. No Task-6 scientific behavior was changed.

Documentation Sync Check:

- parent Failure Memory ledger: `UPDATED`;
- Failure Memory implementation roadmap: `CHECKED_NO_CHANGE_REQUIRED`;
- Experiment Ledger: `CHECKED_NO_CHANGE_REQUIRED`;
- Code Map: `CHECKED_NO_CHANGE_REQUIRED`;
- root README: `CHECKED_NO_CHANGE_REQUIRED`.

Scientific boundary:

- no real procedural Memory record materialization;
- no Analyzer execution;
- no retrieval;
- no Policy projection;
- no source-state replay;
- no effect verification;
- no snapshot publication;
- no model call;
- no ALFWorld execution;
- no scientific execution.

This ledger block is scientifically valid as a CLOSED small-module record only
when the same task runner also records successful remote publication, exact
local/remote branch equality and a clean worktree.
---

## Unit 3 / Task 7 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Design approval:

`DESIGN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Implementation-plan approval:

`PLAN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Approved implementation-plan SHA-256:

`143f8a0f0ac7d9c55390a89c9b7734e401e54cc595f6544aeda9beb9715bee8f`

Task parent:

`498cf114254f55748f2c59b1a27ec1522cdd1ee2`

Verification:

- focused TDD cycle: `11 passed in 0.83s`;
- full repository regression: `1134 passed in 189.42s (0:03:09)`;
- compile / strict syntax checks: PASS;
- scoped diff/status audit: PASS;
- forbidden execution-surface audit: PASS;
- historical evaluation and closed Unit-1/Unit-2 production no-touch audit: PASS;
- non-force fast-forward publication and local/remote equality are required
  by the same task runner after this commit is created.

Implementation detail:

Defined declarative activation, continuation, revalidation, release, termination, non-applicability and Policy-visible state-change boundary contracts with exact registered provenance. No current-state matching or online applicability engine is implemented.

Documentation Sync Check:

- parent Failure Memory ledger: `UPDATED`;
- Failure Memory implementation roadmap: `CHECKED_NO_CHANGE_REQUIRED`;
- Experiment Ledger: `CHECKED_NO_CHANGE_REQUIRED`;
- Code Map: `CHECKED_NO_CHANGE_REQUIRED`;
- root README: `CHECKED_NO_CHANGE_REQUIRED`.

Scientific boundary:

- no real procedural Memory record materialization;
- no Analyzer execution;
- no retrieval;
- no Policy projection;
- no source-state replay;
- no effect verification;
- no snapshot publication;
- no model call;
- no ALFWorld execution;
- no scientific execution.

This ledger block is scientifically valid as a CLOSED small-module record only
when the same task runner also records successful remote publication, exact
local/remote branch equality and a clean worktree.
---

## Unit 3 / Task 8 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Design approval:

`DESIGN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Implementation-plan approval:

`PLAN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Approved implementation-plan SHA-256:

`143f8a0f0ac7d9c55390a89c9b7734e401e54cc595f6544aeda9beb9715bee8f`

Task parent:

`6ef21f35559a741cee13c17fb2a746d894ebb711`

Verification:

- focused TDD cycle: `14 passed in 0.13s`;
- full repository regression: `1148 passed in 492.34s (0:08:12)`;
- compile / strict syntax checks: PASS;
- scoped diff/status audit: PASS;
- forbidden execution-surface audit: PASS;
- historical evaluation and closed Unit-1/Unit-2 production no-touch audit: PASS;
- non-force fast-forward publication and local/remote equality are required
  by the same task runner after this commit is created.

Implementation detail:

Separated optional SEMANTIC_HYPOTHESIS annotations, registered observed recovery bindings and RECOVERY_PROPOSAL objects with typed origin artifacts. No Analyzer, verified-recovery, benefit or effect authority is created.

Documentation Sync Check:

- parent Failure Memory ledger: `UPDATED`;
- Failure Memory implementation roadmap: `CHECKED_NO_CHANGE_REQUIRED`;
- Experiment Ledger: `CHECKED_NO_CHANGE_REQUIRED`;
- Code Map: `CHECKED_NO_CHANGE_REQUIRED`;
- root README: `CHECKED_NO_CHANGE_REQUIRED`.

Scientific boundary:

- no real procedural Memory record materialization;
- no Analyzer execution;
- no retrieval;
- no Policy projection;
- no source-state replay;
- no effect verification;
- no snapshot publication;
- no model call;
- no ALFWorld execution;
- no scientific execution.

This ledger block is scientifically valid as a CLOSED small-module record only
when the same task runner also records successful remote publication, exact
local/remote branch equality and a clean worktree.
---

## Unit 3 / Task 9 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Design approval:

`DESIGN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Implementation-plan approval:

`PLAN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Approved implementation-plan SHA-256:

`143f8a0f0ac7d9c55390a89c9b7734e401e54cc595f6544aeda9beb9715bee8f`

Task parent:

`d4e4175ccac5f6cc7b9cb1e3ebe9c785467fd1fe`

Verification:

- focused TDD cycle: `11 passed in 18.10s`;
- full repository regression: `1159 passed in 419.03s (0:06:59)`;
- compile / strict syntax checks: PASS;
- scoped diff/status audit: PASS;
- forbidden execution-surface audit: PASS;
- historical evaluation and closed Unit-1/Unit-2 production no-touch audit: PASS;
- non-force fast-forward publication and local/remote equality are required
  by the same task runner after this commit is created.

Implementation detail:

Defined the full V1 governance/effect/lifecycle and relation vocabulary while separately enforcing the Unit-3 initial-state and initial-relation firewalls. MEMORY_RECORD relation targets bind exact canonical-record identity; future VERIFIED_BY/HARMFUL_UNDER states are representable but cannot be instantiated by Unit 3.

Documentation Sync Check:

- parent Failure Memory ledger: `UPDATED`;
- Failure Memory implementation roadmap: `CHECKED_NO_CHANGE_REQUIRED`;
- Experiment Ledger: `CHECKED_NO_CHANGE_REQUIRED`;
- Code Map: `CHECKED_NO_CHANGE_REQUIRED`;
- root README: `CHECKED_NO_CHANGE_REQUIRED`.

Scientific boundary:

- no real procedural Memory record materialization;
- no Analyzer execution;
- no retrieval;
- no Policy projection;
- no source-state replay;
- no effect verification;
- no snapshot publication;
- no model call;
- no ALFWorld execution;
- no scientific execution.

This ledger block is scientifically valid as a CLOSED small-module record only
when the same task runner also records successful remote publication, exact
local/remote branch equality and a clean worktree.
---

## Unit 3 / Task 10 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Design approval:

`DESIGN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Implementation-plan approval:

`PLAN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Approved implementation-plan SHA-256:

`143f8a0f0ac7d9c55390a89c9b7734e401e54cc595f6544aeda9beb9715bee8f`

Task parent:

`1664c44f43ff99f60629486a68ccbd994e59d9f3`

Verification:

- focused TDD cycle: `12 passed in 5.25s`;
- full repository regression: `1171 passed in 491.06s (0:08:11)`;
- compile / strict syntax checks: PASS;
- scoped diff/status audit: PASS;
- forbidden execution-surface audit: PASS;
- historical evaluation and closed Unit-1/Unit-2 production no-touch audit: PASS;
- non-force fast-forward publication and local/remote equality are required
  by the same task runner after this commit is created.

Implementation detail:

Implemented the mechanical PROCEDURAL_COMPLETENESS_GATE_V1 report and frozen failure-code ordering. Process evidence uses exact Unit-2 field predicates; single infrastructure-error-only or trivial no-state-change events cannot establish a reusable policy procedural lesson. Semantic hypotheses and recovery proposals remain outside the completeness decision.

Documentation Sync Check:

- parent Failure Memory ledger: `UPDATED`;
- Failure Memory implementation roadmap: `CHECKED_NO_CHANGE_REQUIRED`;
- Experiment Ledger: `CHECKED_NO_CHANGE_REQUIRED`;
- Code Map: `CHECKED_NO_CHANGE_REQUIRED`;
- root README: `CHECKED_NO_CHANGE_REQUIRED`.

Scientific boundary:

- no real procedural Memory record materialization;
- no Analyzer execution;
- no retrieval;
- no Policy projection;
- no source-state replay;
- no effect verification;
- no snapshot publication;
- no model call;
- no ALFWorld execution;
- no scientific execution.

This ledger block is scientifically valid as a CLOSED small-module record only
when the same task runner also records successful remote publication, exact
local/remote branch equality and a clean worktree.
---

## Unit 3 / Task 11 closure — 2026-08-17

Status:

`IMPLEMENTATION_TASK_CLOSED`

Design approval:

`DESIGN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Implementation-plan approval:

`PLAN_APPROVED_FAILURE_MEMORY_PROCEDURAL_RECORD_V1`

Approved implementation-plan SHA-256:

`143f8a0f0ac7d9c55390a89c9b7734e401e54cc595f6544aeda9beb9715bee8f`

Task parent:

`357f3bd4b59f80fcfd07c150269f7f9a5b1967b8`

Verification:

- focused TDD cycle: `26 passed in 10.06s`;
- full repository regression: `1197 passed in 419.41s (0:06:59)`;
- compile / strict syntax checks: PASS;
- scoped diff/status audit: PASS;
- forbidden execution-surface audit: PASS;
- historical evaluation and closed Unit-1/Unit-2 production no-touch audit: PASS;
- non-force fast-forward publication and local/remote equality are required
  by the same task runner after this commit is created.

Implementation detail:

Implemented deterministic PROCEDURAL_FAILURE_MEMORY_RECORD_V1 assembly, exact ordered source-experience manifest binding, parse-time derived-identity recomputation, full V1 governance/relation representability with Unit-3 initial-authority firewall, strict nested final-record and assembly-registration schemas, and an explicit-input write-once offline materializer candidate. The materializer is tested only on synthetic temporary inputs; no real procedural Memory materialization is executed or authorized.

Documentation Sync Check:

- parent Failure Memory ledger: `UPDATED`;
- Failure Memory implementation roadmap: `CHECKED_NO_CHANGE_REQUIRED`;
- Experiment Ledger: `CHECKED_NO_CHANGE_REQUIRED`;
- Code Map: `CHECKED_NO_CHANGE_REQUIRED`;
- root README: `CHECKED_NO_CHANGE_REQUIRED`.

Scientific boundary:

- no real procedural Memory record materialization;
- no Analyzer execution;
- no retrieval;
- no Policy projection;
- no source-state replay;
- no effect verification;
- no snapshot publication;
- no model call;
- no ALFWorld execution;
- no scientific execution.

This ledger block is scientifically valid as a CLOSED small-module record only
when the same task runner also records successful remote publication, exact
local/remote branch equality and a clean worktree.
---

## Unit 3 fixed-head source-review correction — 2026-08-17

Status:

`SOURCE_REVIEW_CORRECTION_CLOSED`

Reviewed parent:

`fcd7e2dc9a5ee768550cdc7993d1b9b08e0dffb1`

Correction:

- multi-event process establishment now requires at least one strictly later
  `executed` or `not_executed` policy event;
- a later environment error remains factual evidence but cannot be the sole
  event establishing a multi-event policy process;
- all seven applicability arrays in both schemas bind `boundary_type` using
  the corresponding exact `const`;
- parent-directory-fsync failure is explicitly regression-tested as a
  fail-closed/write-once durability incident: exact output bytes remain, the
  call reports failure, and a second write cannot overwrite the artifact;
- final-schema future-authority expressiveness and assembly-schema
  future-authority rejection are explicitly regression-tested.

Verification:

- Task-10 focused: `13 passed in 2.76s`;
- Task-11 focused: `31 passed in 19.02s`;
- Memory suite: `383 passed in 111.30s (0:01:51)`;
- full repository regression: `1203 passed in 587.85s (0:09:47)`;
- source-review RED evidence from the reviewed fixed head: PASS;
- static execution-surface audit: PASS;
- strict schema const audit: PASS;
- already-approved Tasks 6-9 production no-touch: PASS;
- Task-11 builder/materializer implementation no-touch: PASS;
- historical evaluation no-touch: PASS.

Correction-runner incident note:

The first correction runner correctly established the Task-10 and schema
RED cases, but its patch payload accidentally appended the literal two-byte
sequence `\\n` at EOF instead of a newline. The resume runner removed only
that terminal harness artifact and preserved the intended source/schema
corrections before all GREEN/regression evidence above was collected.

Materializer durability incident semantics:

`PARENT_DIRECTORY_FSYNC_FAILURE`
=
`DURABILITY_INCIDENT_FAIL_CLOSED`

If file content write and file fsync succeed but parent-directory fsync fails,
the call reports failure, preserves the exact existing output, and does not
automatically overwrite or delete it. A later normal write to the same
canonical path fails through `O_EXCL`.

Scientific boundary:

- no real procedural Memory materialization;
- no Analyzer execution;
- no retrieval;
- no Policy projection;
- no effect verification;
- no snapshot publication;
- no model execution;
- no ALFWorld execution;
- no scientific execution.

Next gate:

fresh exact-head cumulative source review for:

`CODE_APPROVED_PROCEDURAL_FAILURE_MEMORY_RECORD_V1`


## Unit 4 / Task 1 — Projection safety contracts

Status:

`IMPLEMENTED_AND_TESTED`

Scope:

```text
projection common contracts
Policy tokenizer counter interface
Policy-view static safety
contextual current-menu exact-oracle validator
```

Scientific execution remains unauthorized. Real Memory materialization,
retrieval, source-state replay, model/ALFWorld execution and Memory-assisted
Policy execution remain outside this task.

Closure commit is identified by Git history using subject:

`Define Failure Memory projection safety contracts`


## Unit 4 / Task 2 — Deterministic retrieval-key representation

Status:

`IMPLEMENTED_AND_TESTED`

Scope:

```text
MEMORY_RETRIEVAL_KEY_V1
hard-filter metadata / scoring-payload firewall
deterministic semantic retrieval text
content-level retrieval shortcut safety
```

No lexical, dense or hybrid retrieval algorithm is implemented. No ranking,
thresholding, abstention or online retrieval execution is authorized.

Closure commit is identified by Git history using subject:

`Build deterministic Failure Memory retrieval keys`


## Unit 4 / Task 3 — FM1 matched raw episodic view

Status:

`IMPLEMENTED_AND_TESTED`

Scope:

```text
FM1_MATCHED_RAW_EPISODIC_VIEW_V1
unique factual-source ownership
exact Unit-2 pre/post/action mapping
mandatory relevant-start / failure-onset / final anchors
whole-event bounded packing
```

Multi-source records are FM1-ineligible in V1 rather than allowing caller-side
source selection. Scientific Memory execution remains unauthorized.

Closure commit is identified by Git history using subject:

`Build bounded matched raw Failure Memory views`


## Unit 4 / Task 4 — FM2/FM3 structured Policy projection

Status:

`IMPLEMENTED_AND_TESTED`

Scope:

```text
FM2 descriptive projection
FM3 gated prescriptive projection
typed SEMANTIC_HYPOTHESIS failure patterns
exact Unit-3 applicability mapping
FM2/FM3 descriptive-byte identity
separate FM3 recovery disposition
```

This task does not establish effect authority and does not activate any Memory
record or snapshot. Real Memory materialization, retrieval and Policy execution
remain unauthorized.

Closure commit is identified by Git history using subject:

`Build structured Failure Memory Policy projections`

### Unit 4 / Task 4 test-fixture correction

During the first focused GREEN attempt, the Task-4 boundary-test double named
`HugeTokenizer` returned `len(text)`.  The structured FM2 test payload was shorter
than the 256-token hard ceiling, so that fixture did not actually construct the
registered overflow condition.  The production implementation and schema remained
byte-identical to the approved execution payload.  The test-only fixture was
narrowed to deterministic `return 257`, after which the full Task-4 verification
sequence was rerun before closure.


## Failure Memory Policy projection — saved-object integrity hardening

Status:

`IMPLEMENTED_AND_TESTED`

This closure makes saved/reloaded FM1/FM2/FM3 projection objects obey the same
state machine as objects produced directly by the builder.

It adds:
- canonical Policy-payload SHA recomputation during strict object construction;
- exact consistency between build disposition and retained payload/hash/token/
  safety evidence;
- explicit FM1 safety-report class identity;
- `None iff ambiguous` source-provenance semantics for multi-source FM1;
- strict FM2 descriptive-only and FM3 recovery/context consistency.

No retrieval algorithm, Memory materialization, source-state replay, model call,
ALFWorld execution, or Memory-assisted Policy execution is authorized.

Closure commit subject:

`Harden Failure Memory projection envelope integrity`


### Hash integrity / authenticity responsibility boundary

The projection parser verifies internal and deterministic consistency:

```text
SHA256(canonical_json_bytes(actual Policy payload))
==
stored policy_visible_payload_sha256
==
retained safety_report.projection_sha256
```

and it continues to enforce the complete build-disposition, token, safety,
recovery and projection-class state machine.

This does **not** claim that one self-contained mutable JSON artifact can prove
that a fully co-rewritten, internally self-consistent alternate artifact was
not substituted for an earlier artifact. External artifact identity/integrity
binding belongs to the later immutable snapshot/manifest layer.

The future snapshot contract must bind at least:

```text
SHA256(canonical_bytes(full projection artifact))
```

rather than only the Policy-visible payload. This note does not implement the
snapshot, HMAC, signature, model execution, Memory materialization or replay.


## Failure Memory Policy projection — internal-identity and packing hardening

Status:

`IMPLEMENTED_AND_TESTED`

This closure prevents exact known internal provenance identities from leaking
through otherwise Policy-visible free text and proves the deterministic
multi-event FM1 packing contract.

The prohibited exact identities are collected only from the frozen Unit-2 /
Unit-3 field paths approved in the Code-review hardening plan. Matching is
case-sensitive and performs no normalization, fuzzy matching or LLM judgment.

FM1 optional-event packing is proved to stop at the first non-fitting optional
event; mandatory anchors are never silently removed or truncated.

No retrieval algorithm, Memory materialization, source-state replay, model call,
ALFWorld execution, or Memory-assisted Policy execution is authorized.

Closure commit subject:

`Harden FM1 Policy safety and bounded packing proof`


## Failure Memory Policy projection — deterministic reload safety closure

Status:

`IMPLEMENTED_AND_TESTED`

For every ELIGIBLE FM1/FM2/FM3 projection carrying an actual Policy-visible
payload, strict object construction/reload reruns the existing deterministic
Policy-view static audit and requires full equality with the stored
`PolicyViewSafetyReportV1`.

This closes the case where a payload and ordinary internal SHA fields are
rewritten self-consistently while a forged PASS safety report is retained.

The closure does not load Unit-2/Unit-3 source objects, reload a tokenizer,
implement snapshot/manifest, change retrieval, or execute a model/environment.

The hash/authenticity boundary remains unchanged:
the parser enforces internal deterministic consistency; external/original
artifact identity is owned by the later immutable snapshot/manifest binding of
the full canonical projection artifact.

Closure commit subject:

`Recompute deterministic Policy safety on projection reload`

## Unit 4 final fixed-head Code Approval

Decision:

`CODE_APPROVED_FAILURE_MEMORY_POLICY_PROJECTION_V1`

Code authority:

`0332971d88f1592575ba6b8197c9db5b54472a13`

Full regression at approval:

`1290 passed`

This approval authorizes Package-A A1–A8 implementation only. Real source-state
replay/materialization remains separately gated.

## Package-A A9 / A10 closure — FM1/FM2 representation availability

Package-A code authority:

`8c8b88b554cb4099dd43c2aac6f81f60168538ea`

Source panel:

`1d84ac1dc76a01495fab2aa344e077cf35fe54d32d7164e85a240996608730ea`

Source collection ledger:

`404bf34b6c5fa26ec5fdab91a24578cea8a7e61a1f684d6ff4c5ba9682ff9e9c`

Human registration approval:

`4d8f40cde8ce45335c6e2aec7833bf37f5e182de835d4ac7166727ed013adee3`

A9 receipt:

`cb8cda7be63f2755fba1a7f94abad2b106f2b56fde3016f11eac5d4c33f123fc`

DEV descriptive snapshot:

`df271ba7527ebaee104a888d82533832ada0a4aab8735f717767e5d1b1d51cc4`

The three current source records are descriptively eligible through FM2 while
their FM1 raw episodic views remain independently unavailable under the frozen
256-token ceiling. No FM1 ceiling, truncation or safety rule was relaxed.

Effect authority remains `UNTESTED`; Package A created no Policy exposure,
Benefit/Harm or prescriptive FM3 authority.

Final disposition:

`MEMORY_CAUSAL_TEST_INFRASTRUCTURE_READY`

## Memory Scientific Validation V1 targeted hardening — design approved

`MEMORY_SCIENTIFIC_VALIDATION_V1 = DESIGN_APPROVED_TARGETED_HARDENING`

Engineering base: `112ba5d3ccc0a3f3c3a9fdd143ec4c69fa525229`.

Frozen scientific boundaries:
- A0 is a 3×4 source-state local representation/mechanism probe only.
- A1 is optional/conditional and is not a downstream execution blocker.
- effect labels remain Benefit/Harm/Neutral/Uncertain with `SOURCE_STATE_LOCAL_PAIRED` scope.
- terminal effect and mechanism effect are separate.
- B retrieval development uses task/gamefile-group-disjoint calibration, selection-validation and registered safety-stress pools.
- applicability gold is diagnostic/safety authority, not causal effect authority.
- C query groups exclude A0, token-calibration, active-Memory-source and B-development exact task/gamefile groups.
- C2 must bind the frozen Package-B retriever, threshold/config, snapshot and applicability gate.
- pre-result infrastructure failure is not a scientific outcome and retries only the exact frozen cell.
- outcome-guided redesign is forbidden outside a versioned amendment for a registered protocol defect/contamination/safety/identity incident.
- Package-C efficiency estimands and policy-internalization pre-freeze are mandatory.
- paper visual planning cannot suppress adverse/null/contradictory results.

Scientific execution remains `NOT_AUTHORIZED`; effect authority remains `UNTESTED`.

## Memory A0 scientific-contract implementation

Added pure/offline scientific contracts for the approved A0 local representation probe and downstream B/C isolation rules.

The implementation establishes:
- exact 3×4 A0 manifest semantics;
- common M0 empty Memory slot and descriptive-FM2 M3 semantics;
- local paired effect scope with separate terminal/mechanism fields;
- pre-result infrastructure retry as exact same frozen cell and not a scientific outcome;
- B task/gamefile-group disjointness helper;
- C exact query/source-group isolation helper;
- frozen Package-B retrieval binding for C2;
- registered amendment triggers only;
- policy-internalization pre-freeze contract;
- explicit offline write-once A0 manifest materializer.

This code performs no model, environment, retriever, Analyzer, or policy-training execution. `SCIENTIFIC_EXECUTION_AUTHORIZED=false` remains frozen in the A0 manifest.

## Memory Scientific Validation V1 — A0 fixed-head Code Approval

Fixed code head: `2d0c38cbbae511d2f05b3375ff2e2f48e16427b0`.

Disposition: `CODE_APPROVED_MEMORY_SCIENTIFIC_VALIDATION_A0_CONTRACTS_V1`.

Evidence: 12 focused / 557 Memory / 1377 full regression PASS plus compile/schema/static/scope/local-remote/clean fixed-head gates.

Scientific execution remains NOT_AUTHORIZED; effect authority remains UNTESTED.

## Memory Scientific Validation V1 — pre-ABC closure

Shared scientific preparation before formal Packages A/B/C is sealed.

A is ready for its formal execution package. B and C remain dependency-gated. No scientific execution is authorized; effect authority remains UNTESTED.

## Formal Package A — implementation start

Formal local representation/mechanism probe implementation begins from the sealed pre-ABC authority.
No scientific execution is authorized by this implementation-plan commit.

### Formal A replay-and-hold-open

Added a continuation-safe wrapper around the existing exact source-state replay authority.
All existing replay checks remain authoritative; only the unconditional final close is shielded
until the formal continuation completes. Failure paths close the real adapter.

### Formal A real-input binding and execution contracts

Added fail-closed source↔governed-record↔B-DIRECT representation binding plus pure
prompt-census, cell-identity, infrastructure-retry, and cell-result contracts.
The binder is offline-only and preserves scientific_execution_authorized=false.

### Formal A execution candidate

Added an explicit-approval-gated single-cell continuation runner and deterministic 12-cell
local paired aggregator. Pre-result infrastructure failure can retry only the same frozen
cell identity; post-execution infrastructure ambiguity is a hard stop with no auto-retry.
The candidate is not invoked or scheduler-submitted by code preparation.
Effect authority remains UNTESTED.

## Formal Package A — pre-execution evidence hardening

Human fixed-head review of `8792808c7171f1324649ddafd97c60e78fb1ea19`
identified execution-evidence gaps that must be closed before the first Memory-ON
scientific outcome.

Approved narrow correction:
- runtime template/arm/payload identity is rebound exactly to the frozen A0 cell;
- no Policy exposure means no scientific outcome and no denominator entry;
- every post-source environment transition is retained as content-addressed evidence;
- aggregation reparses and rehashes each cell result and binds the selected attempt/evidence;
- post-provider-response token/model/schema/evidence ambiguity is a no-auto-retry hard stop;
- the execution candidate binds the repository `src/` layout explicitly.

The 3×4 scientific design, three source states, M0/M1/M2/M3 payloads,
continuation seed 17, effect scope, and local-only authority are unchanged.

Mechanism-effect classification remains `NOT_EVALUATED` until a separate
outcome-blind registered classification rule exists.

Scientific execution remains NOT_AUTHORIZED; effect authority remains UNTESTED.

## Formal Package A — hardened fixed-head Code Approval

Decision: `CODE_APPROVED_FORMAL_MEMORY_PACKAGE_A_A0_EXECUTION_V1`.

Execution-code authority: `9d4e4b853fb62757ed8c709d76d14b80bc3fd357`.

Fixed-head evidence: 13 focused / 574 Memory / 1394 full repository PASS.
Runtime exposure identity, no-exposure semantics, continuation evidence, result
revalidation and no-auto-retry post-response ambiguity are approved.

Mechanism-effect classification remains NOT_EVALUATED pending a separately
registered outcome-blind rule. Scientific execution remains separately gated.

## Formal Package A — Train17 runtime freeze

Code Approval head: `b38b7a83af706faa29089f1e0077af9438209e29`.

Train17 runtime is frozen through PolicyCondition semantic identity, exact SELECT v2
byte integrity, actual runtime-descriptor file identity, historical A800 model-identity
smoke, model/tokenizer/LoRA identities, and exact request decoding semantics.

The runtime descriptor is not required to self-contain its externally assigned
semantic runtime SHA.

No scientific execution occurred. Next gate is explicit A0 execution approval.

## Formal Package A0 — scientific result seal

Formal A0 completed 12/12 frozen source-state-local cells and 9/9 M0-paired
terminal-effect comparisons. Exact effect counts and arm summaries are frozen in
`configs/memory/formal_a0_result_authority_v1.json`.

Authority remains LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY. General representation
superiority is not authorized. Mechanism effect remains NOT_EVALUATED pending a
separately registered rule.

Package B proceeds under the pre-frozen retrieval/applicability-safety protocol;
A0 outcomes do not authorize outcome-guided downstream redesign.

## Formal Package B — activation and implementation plan

Formal Package B begins from A0 scientific result seal
`577ee618a334dc08d73dd6fa31c7afa152b9afd5`.

A0 terminal result remains Benefit=0 / Harm=0 / Neutral=9 and does not alter the
pre-frozen Package-B question or three-stage protocol.

Formal B will evaluate retrieval and applicability safety using disjoint
RETRIEVER_CALIBRATION_DEV / RETRIEVER_SELECTION_VALIDATION /
REGISTERED_SAFETY_STRESS task-gamefile groups and independent gold authority.

Scientific execution remains NOT_AUTHORIZED.

## Formal Package B — retrieval/selection evaluator

Implemented the pure/offline Formal-B evaluator for the pre-frozen Q3 protocol:
three task-gamefile-group-isolated pools, independent gold, deterministic
CASEFOLD_WORD_JACCARD_V1 ranking, tie abstention, threshold calibration/selection,
existing direct applicability gate integration, and safety/coverage metrics.

No B scientific panel was executed.

## Formal Package B — offline execution runner

Added a gated offline runner that binds an immutable independent-gold panel to the
strict active snapshot loader and executes Calibration DEV → Selection Validation →
Registered Safety Stress. The stress stage reuses the frozen selected config and
cannot modify it.

The runner requires a separate explicit scientific-execution approval token. No
Formal-B scientific panel was executed by this implementation module.

## Formal Package B — pre-outcome protocol-defect hardening

Before any Formal-B scientific outcome, fixed-head source review registered
`PROTOCOL_DEFECT`: threshold selection did not treat gold-abstention Memory exposure
as a selection-time safety violation, and the runner did not rebind panels to a real
independent gold-authority artifact.

The corrected evaluator uses unsafe exposure (wrong lineage + non-applicable exposure)
as the primary safety criterion, requires positive and abstention gold in every pool,
and requires an independently loaded gold authority.

No B scientific panel had been executed. Q3, the three-stage pools, lexical ranker,
threshold grid and applicability gate remain unchanged.

## Formal Package B — hardened fixed-head Code Approval

Decision: `CODE_APPROVED_FORMAL_MEMORY_PACKAGE_B_RETRIEVAL_SAFETY_V1`.

Approved code authority: `f17b29d518c916e83f26ba453d545f1120ee4b9d`.
9 focused / 583 Memory / 1403 full repository tests PASS.

Source census and independent-gold preparation may proceed.
Formal-B scientific execution remains separately gated.

## Formal Package B — outcome-blind query-pool freeze

Formal-B task/gamefile groups and pre-gold query candidates were frozen before
annotation or retrieval scoring. The freeze contains 10/10/10 disjoint groups and
one active-Memory source-provenance anchor per pool.

Repeated model calls with identical production query identity are collapsed before selecting the final up to three unique query candidates per failure.

Gold labels remain ungenerated. Scientific execution remains unauthorized.

## Formal Package B — blinded independent-gold annotation packet

The frozen 79 query candidates were converted into a blinded annotation packet.
Boundary clause text is included only after exact rebinding to the independently
registered boundary authority artifact.

Pool/task/source identity and all retriever/gate outputs remain hidden from the
annotator. No gold label has been generated.

## Formal Package B — Gold Authority Correction V1

Round1 blind annotation is preserved as diagnostic protocol-defect evidence and is
not final gold.

Before any retrieval scoring, exact PolicyCallEvidenceV1 inputs are now the query
timing authority. Frozen task/gamefile-group pools remain unchanged.

Final gold requires two independent V2 passes, registered adjudication, explicit
REFERENCE_APPLICABILITY vs RETRIEVER_OBSERVABILITY separation, and a post-gold
pool prerequisite audit. Calibration remains forbidden.

## Formal Package B — minimal Q3 validation protocol

Formal B is deliberately narrowed to the minimum Memory-tool function needed for
Q3: retrieve relevant history and abstain safely. No external model/API annotation
is part of Memory or Formal-B execution.

## Formal Package B — minimal Q3 result seal

Formal B completed as a pure offline Memory-tool evaluation with no external
model/API, no policy inference, and no environment rollout.

Result authority: `ba2290e90631b8836ea93106fd1630237c7b45470bc465c1000e7fb18647fb7b`.

Registered Safety Stress: unsafe=0/30 wrong=0/30 nonapp=0/28 correct=0/2 abstain=30/30 coverage=0/30 selective_accuracy=0/0.

This closes the Memory retrieval/applicability-safety evidence needed for Q3.

## Corrected Failure Memory V1 completion scope

Restored Memory V1 to core records, role-specific exports, mechanical round
maintenance, scientific harnesses and external component ports. Hierarchical
Analyzer, Training Researcher/Planner, policy training and OFF/OFF execution are
external/deferred and are not implemented by Memory.

## Role-specific Memory exports

Implemented distinct Policy, Analyzer and Training Researcher exports. The Policy
path retains the sealed direct-exposure gate; Analyzer candidate support is bounded
but does not inherit the final Policy threshold; Researcher full-record access
requires explicit train-side partition authority and held-out evidence is aggregate-only.

## Deterministic Memory round maintenance

Implemented immutable within-round snapshots, append-only shadow events, no
same-round readback, next-round-only Benefit promotion, Harm quarantine,
Neutral descriptive-only, Uncertain staging, retrieval-dev shadow-only and strict
held-out/formal-evaluation no-writeback.

## External component ports

Implemented typed Analyzer proposal ingress, same-state Verifier effect ingress,
Researcher evidence export and optional verified training-evidence export. These
ports preserve authority boundaries and do not implement or execute the external
Analyzer, Researcher, trainer or benchmark.

## Memory scientific program and Q1-Q5 gates

Implemented Stage 0/1A/1B/2/3 scientific identities and an authority-backed Q1-Q5
matrix. Missing real Analyzer/F0-F1/training/OFF-OFF authorities remain OPEN or
DEFERRED; engineering tests cannot close scientific questions.
