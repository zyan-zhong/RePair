# Failure Memory Sequence Failure Experience V1 Implementation Plan

## 1. Status and authority

Plan status:

`PLAN_CANDIDATE_FAILURE_MEMORY_SEQUENCE_EXPERIENCE_V1`

Production implementation status:

`NOT_AUTHORIZED`

Scientific execution status:

`NOT_AUTHORIZED`

Approved parent design:

`docs/superpowers/specs/2026-08-14-failure-memory-v1-design.md`

Failure Memory roadmap:

`docs/memory/FAILURE_MEMORY_V1_IMPLEMENTATION_ROADMAP.md`

Task-access foundation seal:

`docs/audits/FAILURE_MEMORY_TASK_ACCESS_FOUNDATION_SEAL_V1.md`

Foundation seal commit:

`7403745e51ca634aa1c0c8ea7df56a77afa74240`

Roadmap synchronization base:

`171ed4720b5393c5456ab75312b21fe9857b580d`

Planning branch:

`plan/failure-memory-sequence-experience-v1`

This plan covers only:

`SEQUENCE_FAILURE_EXPERIENCE_V1`

It does not authorize:

- Procedural Failure Memory;
- semantic Analyzer output;
- failure-mechanism classification;
- recovery generation;
- applicability inference;
- retrieval;
- Policy projection;
- Memory-aware prompting;
- source-state replay;
- ALFWorld execution;
- model calls;
- Memory-assisted execution;
- training;
- benchmark execution;
- scientific claims.

No production code may be written until this plan receives explicit
human approval.

---

## 2. Scientific purpose

Unit 2 implements deterministic factual reconstruction of a registered
multi-step failure sequence.

The output answers only:

> What happened in the registered failure sequence?

It must not answer:

> Why did the policy fail?

It must not answer:

> What should the policy have done?

It must not answer:

> When should this Memory be retrieved?

Those questions belong to later units.

The data flow for this unit is:

```text
sealed immutable attempt evidence
        ↓
existing whole-episode deterministic validation
        ↓
registered factual sequence boundary
        ↓
deterministic factual reconstruction
        ↓
SEQUENCE_FAILURE_EXPERIENCE_V1
```

The unit creates no reusable Procedural Failure Memory record.

---

## 3. Historical no-touch boundary

Unless a later separately approved plan explicitly states otherwise,
this unit must not modify:

```text
src/pchsi/evaluation/
```

including:

```text
action_trace.py
canonical_evidence.py
policy_call_evidence.py
public_transition.py
episode_artifact.py
episode_sequence.py
runtime_core.py
budget.py
raw_policy_parser.py
raw_policy_prompt.py
```

It must not modify the closed task-access foundation:

```text
src/pchsi/memory/task_access.py
src/pchsi/memory/policy_contract.py
src/pchsi/memory/task_access_sha_authority_correction.py

scripts/memory/materialize_task_access_v1.py

configs/memory/task_access_regeneration_v1.json
configs/memory/task_access_regeneration_v2.json
```

The authoritative task-access identities remain:

```text
protected task-access SHA-256
=
260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea

sanitized task-access SHA-256
=
e7dc8ddd1795b4ed51fdf62735a49620c8bc03470b86de220180d45a336c5228
```

Population semantics remain:

```text
TRAIN_MEMORY_SOURCE = 2367
TRAIN_RETRIEVAL_DEV = 1186

VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED = 140

VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED = 134
```

Unit 2 must not reinterpret these roles.

---

## 4. Reused evidence authorities

The implementation may import and consume the existing public contracts
from:

```text
src/pchsi/evaluation/canonical_evidence.py
src/pchsi/evaluation/action_trace.py
src/pchsi/evaluation/policy_call_evidence.py
src/pchsi/evaluation/public_transition.py
src/pchsi/evaluation/episode_artifact.py
src/pchsi/evaluation/episode_sequence.py
```

These remain the evidence authorities.

Unit 2 may not create a second independent interpretation of:

- model-call numbering;
- BudgetState semantics;
- parser outcomes;
- environment-step numbering;
- public observations;
- admissible menus;
- executed actions;
- done/won/score;
- episode termination.

Before reconstruction, the complete source episode must pass the
existing deterministic cross-record episode validation.

A sequence builder must fail closed when upstream evidence is internally
inconsistent.

---

# 5. Core factual contracts

## 5.1 Registered sequence boundary

Unit 2 introduces an explicit factual range contract:

`REGISTERED_FAILURE_SEQUENCE_WINDOW_V1`

It exists so the deterministic builder never decides for itself which
part of an episode is scientifically relevant.

The registration contains only source/range authority.

Minimum fields:

```text
schema_id
schema_version

registration_id

source_bundle_sha256
source_attempt_id
source_task_id

relevant_start_model_call_index
failure_onset_model_call_index
final_model_call_index

registered_recovery_start_model_call_index
registered_recovery_final_model_call_index

registration_source_sha256
```

The recovery range may be null.

Rules:

- model-call indices are inclusive;
- relevant start <= failure onset <= final model call;
- a registered recovery range must lie inside the registered sequence;
- recovery start <= recovery final;
- no free-text mechanism field exists;
- no proposed action exists;
- no recovery advice exists;
- no applicability field exists;
- no causal label exists;
- no outcome may be chosen by the builder after reconstruction.

The registration is an external boundary input.

The builder validates it.

The builder does not invent or widen it.

---

## 5.2 Sequence event

Each relevant policy attempt is represented as a factual event.

The canonical event must bind at least:

```text
model_call_index

execution_status
attempt_outcome

parser_status
parser_error

literal_action
normalized_action
admissibility_status

interface_feedback_before

policy_attempt_count_before
policy_attempt_count_after

environment_step_count_before
environment_step_count_after

protocol_failure_count_before
protocol_failure_count_after

inadmissible_action_count_before
inadmissible_action_count_after

consecutive_nonexecuted_attempt_count_before
consecutive_nonexecuted_attempt_count_after

pre_observation
pre_observation_sha256

pre_admissible_commands
pre_admissible_commands_sha256

raw_model_response
raw_model_response_sha256

submitted_environment_action

resulting_observation
resulting_observation_sha256

resulting_admissible_commands
resulting_admissible_commands_sha256

environment_step_index

score
done
won

visible_state_change_disposition

trace_source_sha256
policy_call_source_sha256
public_transition_source_sha256
```

Fields not applicable to a nonexecuted attempt are null.

`visible_state_change_disposition` is deterministic and may only encode
direct public evidence, for example:

```text
NONEXECUTED

NO_VISIBLE_STATE_CHANGE

OBSERVATION_CHANGED

MENU_CHANGED

OBSERVATION_AND_MENU_CHANGED

ENVIRONMENT_ERROR
```

It must not encode:

```text
progress
regression
correct transition
wrong transition
useful state change
bad branch
```

Those are semantic interpretations.

---

## 5.3 Relevant start

The factual relevant start is derived only from the first registered
model-call index.

It binds:

```text
model_call_index

public_task_goal
public_task_goal_sha256

observation
observation_sha256

admissible_commands
admissible_commands_sha256

interface_feedback_before

BudgetState-before identity
```

The builder may not move the relevant start because another point looks
more useful.

---

## 5.4 Source identity

One sequence experience must bind:

```text
experience_id
schema_id
schema_version

source_round
source_condition

source_task_id
source_gamefile_group_id

source_bundle_sha256
source_attempt_id

registered policy-call range
derived included environment-step indices

source bundle file hashes

registration_id
registration_source_sha256
```

Real materialization later must accept only sources authorized as:

`TRAIN_MEMORY_SOURCE`

unless a later separate plan explicitly authorizes another scientific
role.

No valid_seen or valid_unseen sequence may silently become a Memory
development source.

---

## 5.5 Terminal / observed outcome

The sequence record may contain only outcome information that lies
inside the registered factual sequence.

If the registered sequence reaches episode termination, the factual
terminal fields may contain:

```text
termination_reason
final_success
final_done
final_won
final_budget
```

If the registered sequence ends before episode termination, later
episode outcomes must not be copied into the sequence merely because
they are available in the source bundle.

This prevents accidental future-information injection into a bounded
sequence record.

---

## 5.6 Factual recovery

A recovery is included only when the registration explicitly identifies
an observed recovery range and the source evidence contains it.

Unit 2 does not decide that an action was a good recovery.

It records only the factual registered sequence.

The record must not contain:

```text
recommended_recovery
should_execute
preferred_action
correct_action
repair_instruction
```

---

# 6. Canonical Sequence Failure Experience

The main output is:

`SEQUENCE_FAILURE_EXPERIENCE_V1`

It contains these logical groups:

```text
identity_and_source
registration_binding
relevant_start
observed_sequence
failure_development
factual_recovery
observed_end_state
source_binding
```

The object must be immutable once constructed.

Canonical serialization uses the repository's existing deterministic
JSON convention:

```text
UTF-8
sort_keys = true
compact separators
allow_nan = false
one terminal LF
```

The experience identity is domain separated.

Conceptually:

```text
SHA256(
  "SEQUENCE_FAILURE_EXPERIENCE_V1"
  + NUL
  + canonical_payload_without_experience_id
)
```

The exact construction must be frozen by focused tests.

Two constructions from byte-identical source evidence and registration
must produce byte-identical output and the same experience ID.

---

# 7. Source binding requirements

Every factual value copied into the experience must be bound to
existing source evidence.

## 7.1 Whole-episode validation first

The complete attempt must pass existing:

`validate_episode_sequence(...)`

before any registered subrange is accepted.

A valid local slice may not hide an invalid whole attempt.

## 7.2 Trace ↔ PolicyCall binding

For each included model call, the builder must verify consistency for
all overlapping factual fields, including at minimum:

```text
model_call_index
public_task_goal
observation
admissible_commands
raw response
interface feedback
BudgetState-before
```

A mismatch is fatal.

## 7.3 Trace ↔ PublicTransition binding

For executed environment steps, transition identity must remain
consistent with the existing episode validator.

The builder must not fuzzy-match transitions.

No nearest-index repair is allowed.

## 7.4 Source-file hashes

The sequence must retain exact hashes for the sealed bundle members used
as source authority.

The output must never claim provenance from a file whose supplied hash
does not match the source bytes.

---

# 8. Order and range invariants

The builder must reject:

- empty registered sequence;
- negative indices;
- noncontiguous model-call range;
- range outside the source episode;
- failure onset outside the registered range;
- recovery range outside the registered range;
- reversed recovery range;
- source attempt mismatch;
- source task mismatch;
- source bundle SHA mismatch;
- duplicate model-call indices;
- out-of-order policy calls;
- out-of-order transitions;
- transition attached to the wrong model call;
- any silent range widening;
- any silent range shrinking.

Original sequence order is authoritative.

The builder must not sort model attempts into a different scientific
order.

---

# 9. Semantic non-authority boundary

The Python model and wire schema must provide no canonical fields for:

```text
failure_mechanism
capability_deficit
progress_blindness
phase_error
root_cause
recommended_action
correct_action
repair
recovery_advice
activation_condition
release_condition
non_applicability_condition
effect_status
benefit
harm
confidence
```

A source string containing one of those words is not itself forbidden.

The rule concerns canonical semantic fields and builder-generated
interpretation.

Raw model response text remains factual source evidence.

Unit 2 does not reinterpret its meaning.

---

# 10. Planned repository surfaces

Production implementation scope is limited to:

```text
src/pchsi/memory/sequence_failure_experience.py

configs/memory/schemas/
sequence_failure_experience_v1.json

tests/memory/
test_sequence_failure_experience.py

scripts/memory/
materialize_sequence_failure_experience_v1.py
```

A supplemental static audit may be added only if required by source
review:

```text
scripts/memory/
audit_sequence_failure_experience_v1.py
```

Documentation is updated only during module closure.

No historical evaluation source file may be modified.

---

# 11. TDD and implementation tasks

Each task closes independently.

No later task may silently fix an earlier closed task.

---

## Task 1 — Canonical factual contract

Purpose:

Implement the immutable wire/data contract without building real
sequences yet.

### RED

Add failing tests for:

- module absent;
- registration schema absent;
- experience schema absent;
- invalid index ordering;
- semantic/advice fields unavailable;
- canonical serialization identity;
- deterministic experience-ID generation;
- strict JSON rejection;
- duplicate-key rejection;
- nonfinite-number rejection.

Expected RED reason must be missing Unit-2 behavior, not syntax,
collection or infrastructure failure.

### GREEN

Implement:

```text
RegisteredFailureSequenceWindowV1
SequenceFailureEventV1
SequenceFailureRelevantStartV1
SequenceFailureObservedEndV1
SequenceFailureExperienceV1
```

plus:

```text
to_dict
from_dict
to_json
from_json
canonical bytes
experience ID
```

Use frozen immutable records.

### Focused verification

```text
tests/memory/test_sequence_failure_experience.py
```

### Full regression

Run complete repository pytest.

### No-touch audit

Historical evaluation files and closed task-access files must remain
byte-identical to the Task-1 parent.

### Task-1 commit

Suggested subject:

`Define factual sequence experience contract`

Push immediately and verify local/remote equality.

---

## Task 2 — Source evidence binding

Purpose:

Bind the contract to existing immutable episode evidence.

### RED

Add failing tests for:

- invalid whole episode rejected before slicing;
- PolicyCall / ActionTrace observation mismatch;
- PolicyCall / ActionTrace menu mismatch;
- PolicyCall / ActionTrace raw-response mismatch;
- BudgetState-before mismatch;
- task identity mismatch;
- attempt identity mismatch;
- source-bundle hash mismatch;
- invalid registered range;
- noncontiguous call range;
- recovery range outside sequence;
- transition/model-call mismatch.

Use synthetic immutable evidence.

No model or environment execution.

### GREEN

Implement source-binding validation using existing evidence contracts.

The implementation must call the existing whole-episode sequence
validator rather than replacing it.

No fuzzy matching or evidence repair is allowed.

### Task-2 commit

Suggested subject:

`Bind sequence experience to episode evidence`

Push immediately and verify local/remote equality.

---

## Task 3 — Deterministic factual reconstruction

Purpose:

Construct the complete factual sequence from a valid registered range.

### RED

Add failing tests for:

- relevant start not equal to registered first call;
- missing policy attempt inside range;
- original order not preserved;
- nonexecuted attempt incorrectly assigned a transition;
- visible state-change disposition incorrect;
- future episode outcome leaking past registered end;
- terminal outcome missing when terminal lies inside range;
- factual recovery invented when no recovery range is registered;
- same source + registration not byte reproducible;
- different source bytes not changing experience identity.

### GREEN

Implement:

`build_sequence_failure_experience_v1(...)`

The builder must:

1. validate the complete source episode;
2. validate the registration;
3. validate all source bindings;
4. preserve exact call order;
5. construct relevant start;
6. construct one factual event per included policy call;
7. attach exact executed transition where applicable;
8. derive public state-change disposition only;
9. include only registered factual recovery;
10. include only outcome visible inside the registered range;
11. bind source-file hashes;
12. calculate deterministic experience identity;
13. return immutable V1 output.

### Task-3 commit

Suggested subject:

`Build deterministic factual failure sequences`

Push immediately and verify local/remote equality.

---

## Task 4 — Read-only materializer candidate and audit

Purpose:

Provide a deterministic offline materializer without authorizing real
historical materialization.

### RED

Add failing synthetic tests for:

- unauthorized task-access role rejected;
- source bundle missing;
- source bundle hash mismatch;
- registration/source mismatch;
- duplicate experience ID;
- noncanonical output;
- source order instability;
- output overwrite attempt;
- symlink output rejected;
- real model/environment import forbidden.

### GREEN

Implement:

`materialize_sequence_failure_experience_v1.py`

The code candidate accepts only explicit inputs.

It must not discover or select failure regions itself.

The interface must require a registered sequence-window input.

It must not call:

```text
ALFWorld
env.reset
env.step
policy model
OpenAI
Anthropic
vLLM
retriever
Analyzer
```

The materializer produces deterministic offline artifacts only.

Candidate output is write-once.

Real sequence materialization remains blocked.

Historical Round-1 `valid_unseen` evidence is not authorized by this
plan as an active Failure Memory source. Its historically exposed status
and mechanism-development-only boundary remain unchanged.

### Task-4 commit

Suggested subject:

`Build sequence experience materializer candidate`

Push immediately and verify local/remote equality.

---

# 12. Required adversarial tests

Before Unit-2 code approval, focused tests must explicitly prove:

```text
invalid upstream episode
→ fail

wrong registered source bundle
→ fail

wrong task
→ fail

wrong attempt
→ fail

missing call inside registered sequence
→ fail

policy-call / trace mismatch
→ fail

trace / public-transition mismatch
→ fail

future outcome outside registered range
→ excluded

semantic mechanism field
→ not representable in canonical schema

recovery advice field
→ not representable in canonical schema

registered recovery absent from source
→ fail

same immutable evidence
→ byte-identical output

changed immutable evidence
→ changed source binding / experience identity
```

---

# 13. Static forbidden-surface audit

The Unit-2 implementation must not contain execution integrations for:

```text
alfworld
env.step(
env.reset(
openai
anthropic
vllm
torch
transformers
```

The presence of a type name or documentation string alone is not an
execution violation.

The static audit should inspect imports/calls rather than rely only on
broad substring matching.

Unit 2 must not import later Failure Memory modules because those modules
do not yet exist scientifically.

---

# 14. Real-data authorization boundary

Even after all four implementation tasks pass, the following remain
unauthorized:

```text
REAL_ROUND1_SEQUENCE_MATERIALIZATION
=
NOT_AUTHORIZED

MEMORY_RECORD_MATERIALIZATION
=
NOT_AUTHORIZED

ANALYZER_EXECUTION
=
NOT_AUTHORIZED

ALFWORLD_EXECUTION
=
NOT_AUTHORIZED

MEMORY_ASSISTED_POLICY_EXECUTION
=
NOT_AUTHORIZED

STAGE0_SCIENTIFIC_EXECUTION
=
NOT_AUTHORIZED
```

The code candidate must receive independent fixed-head source review.

The next gate after the code candidate is:

`CODE_APPROVED_FAILURE_MEMORY_SEQUENCE_EXPERIENCE_V1`

Only after Code Approval may a separate real-materialization package be
designed and submitted for approval.

---

# 15. Real sequence-registration boundary

Unit 2 deliberately separates:

```text
range registration
```

from:

```text
deterministic reconstruction
```

The reconstruction implementation must not choose its own scientifically
interesting regions.

Before real historical materialization, a separate authoritative
registration input must exist for every requested sequence.

The registration process may be manual or generated by a separately
approved deterministic protocol.

It is not authorized by this implementation plan.

This prevents Unit 2 from silently becoming a semantic failure detector.

---

# 16. Review checklist

Code review must confirm:

### Scientific scope

- purely factual;
- no mechanism inference;
- no recovery prescription;
- no applicability inference;
- no effect labels;
- no retrieval;
- no Policy projection.

### Evidence integrity

- whole episode validated first;
- source hashes bound;
- exact range bound;
- source order preserved;
- no fuzzy repair;
- no future-range leakage.

### Reproducibility

- canonical JSON;
- deterministic IDs;
- duplicate-key rejection;
- no current time in canonical scientific payload;
- no checkout absolute path in canonical scientific identity;
- no mutable output overwrite.

### Historical no-touch

No historical evaluation or task-access semantics changed.

### Tests

- focused tests pass;
- full applicable regression passes;
- compile passes;
- diff check passes;
- static scope audit passes.

---

# 17. Module closure

Every implementation task closes immediately after passing its focused
and regression verification.

For each Task:

```text
RED
→ GREEN
→ focused tests
→ full applicable regression
→ compile
→ diff/scope audit
→ source review
→ single-purpose commit
→ push
→ local/remote equality
→ clean worktree
```

After Task 4, perform cumulative fixed-head code review.

The Unit-2 code implementation is not scientifically closed merely
because tests pass.

Real sequence materialization, if later approved, requires its own:

```text
preflight
execution identity
artifact hashes
independent audit
ledger update
closure commit
```

---

# 18. Planned documentation closure

After successful Code Approval and any separately approved real
materialization, update only the necessary Memory documentation.

At minimum review:

```text
docs/memory/FAILURE_MEMORY_V1_LEDGER.md
docs/memory/FAILURE_MEMORY_V1_IMPLEMENTATION_ROADMAP.md
docs/experiments/EXPERIMENT_LEDGER.md
docs/code_map.md
```

The roadmap should then advance from:

```text
Unit 2 — Factual failure-sequence reconstruction
```

to:

```text
Unit 3 — Canonical Procedural Failure Memory
```

only after Unit 2 is actually closed.

---

# 19. Fixed-plan source/design review hardening amendment V1

This section is normative.

It supersedes any earlier Unit-2 wording that is ambiguous about:

- task-access source identity;
- registration-label authority;
- required preceding prefix;
- terminal/future-outcome inclusion;
- environment-step coverage;
- source-record hashing;
- implementation-task decomposition.

The amendment does not change the approved Failure Memory research
design.

It narrows Unit 2 to deterministic factual reconstruction.

---

## 19.1 Exact task-access source binding

Unit 2 requires:

`SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1`

for any real source episode that may be materialized.

Minimum fields are:

```text
schema_id
schema_version

task_access_protected_manifest_sha256

task_access_record_line_index
task_access_record_sha256

task_gamefile_group_id
dataset_relative_gamefile
gamefile_sha256

task_type
split
access_class
```

For the current Failure Memory foundation:

```text
task_access_protected_manifest_sha256
=
260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea
```

`task_access_record_sha256` is:

```text
SHA256(
    exact canonical protected-task-access JSONL
    record bytes including the terminal LF
)
```

The binding must independently verify:

```text
source EpisodeArtifact.gamefile_sha256
==
task-access record gamefile_sha256

source EpisodeArtifact.task_type
==
task-access record task_type
```

The task/gamefile group ID is taken only from the authoritative
task-access record and must also independently satisfy the frozen
`ALFWORLD_TASK_GAMEFILE_GROUP_V1` derivation.

No `task_id` string parsing may be used to invent the group ID.

For active Failure Memory source construction:

```text
access_class
=
TRAIN_MEMORY_SOURCE
```

is required.

`TRAIN_RETRIEVAL_DEV` is not active-bank writeback input.

`valid_seen` is forbidden as development source.

Historically exposed `valid_unseen` may be used only under a separately
approved mechanism-development protocol and never as an active formal
Memory source.

---

## 19.2 Registration authority is not raw-evidence authority

The registered range remains an external input.

The contract must use:

`REGISTERED_FAILURE_SEQUENCE_WINDOW_V1`

with explicit registration provenance.

Required registration-authority fields are:

```text
registration_id

registration_authority_type
registration_protocol_id

registration_artifact_sha256
registration_record_sha256
```

`registration_record_sha256` is the SHA-256 of the exact canonical
registration-record bytes.

The earlier ambiguous field:

```text
registration_source_sha256
```

is superseded by the two explicit identities:

```text
registration_artifact_sha256
registration_record_sha256
```

The failure marker field is named:

```text
registered_failure_onset_model_call_index
```

not:

```text
failure_onset_model_call_index
```

because the marker is a registered boundary label, not environment truth.

The registered recovery fields remain:

```text
registered_recovery_start_model_call_index
registered_recovery_final_model_call_index
```

but their authority type is:

`REGISTERED_BOUNDARY_LABEL`

not:

`FACT_AUTHORITY`

The two recovery fields must be:

```text
both null
```

or:

```text
both non-null integers
```

and when non-null must satisfy:

```text
registered_failure_onset_model_call_index
<=
registered_recovery_start_model_call_index
<=
registered_recovery_final_model_call_index
<=
final_model_call_index
```

Unit 2 may state only:

> this range was registered as the observed recovery window.

It may not state:

> this recovery was beneficial, correct, causal or transferable.

`source_round` and `source_condition` are opaque registered provenance
identities.

The builder must never infer them by parsing free-form IDs.

Any future automatic registration protocol requires separate approval.

---

## 19.3 Required preceding-prefix binding

The approved relevant-start contract requires the history that produced
the registered starting state.

Unit 2 therefore deterministically binds the complete source prefix.

For:

```text
relevant_start_model_call_index = k
```

the required preceding policy-call range is exactly:

```text
0 .. k-1
```

or empty when:

```text
k = 0
```

The sequence output records:

```text
required_preceding_model_call_range

required_preceding_environment_step_indices

required_preceding_prefix_source_binding
```

`required_preceding_environment_step_indices` contains the exact
environment-step indices associated with preceding source attempts.

No preceding call or transition is selected because it looks
scientifically important.

The full prefix is a deterministic provenance dependency.

The preceding-prefix binding is not duplicated as Policy-visible Memory
content in Unit 2.

---

## 19.4 Deterministic registered-end and future-information rule

The phrase:

> if the registered sequence reaches episode termination

has one exact V1 meaning.

Let:

```text
registered_final_call
=
final_model_call_index

whole_episode_final_call
=
len(source_action_traces) - 1
```

Then:

```text
registered_final_call
==
whole_episode_final_call
```

requires:

```text
episode_terminal_disposition
=
INCLUDED_REGISTERED_WINDOW
```

and the sequence MUST bind the exact source:

```text
termination_reason
final_success
final_done
final_won
final_budget
```

If:

```text
registered_final_call
<
whole_episode_final_call
```

then:

```text
episode_terminal_disposition
=
OUTSIDE_REGISTERED_WINDOW
```

and all episode-terminal fields MUST be null.

There is no optional implementation choice.

Per-transition fields:

```text
score
done
won
```

remain factual when the corresponding transition itself lies inside the
registered call window.

The output also records the BudgetState-after of the final included
policy attempt.

That local ending budget is distinct from the episode-final budget.

---

## 19.5 Environment-step coverage is derived, not registered

The registered scientific range is model-call based.

The builder derives:

```text
included_environment_step_indices
```

from the included source traces/transitions.

It must preserve the exact observed indices.

It must not assume a one-to-one relationship between:

```text
model calls
```

and:

```text
environment transitions
```

because nonexecuted attempts and environment-error attempts exist.

No fuzzy or nearest-index transition matching is allowed.

---

## 19.6 Exact source-record pointers and hashes

Every included source record is identified by an exact source pointer.

The pointer contains:

```text
bundle_member_name
zero_based_line_index
exact_record_sha256
whole_member_sha256
```

For JSONL evidence:

```text
exact_record_sha256
=
SHA256(
    exact canonical source JSONL record bytes
    including terminal LF
)
```

The relevant bundle members are:

```text
attempt.json
action_traces.jsonl
policy_calls.jsonl
public_transitions.jsonl
SHA256SUMS
```

The source attempt used by the current Unit-2 contract must contain
`policy_calls.jsonl`.

A bundle lacking the required policy-call evidence fails closed under:

`POLICY_CALL_EVIDENCE_REQUIRED`

`source_bundle_sha256` means the existing deterministic
`attempt_bundle_sha256`.

It is not a new directory hash or filesystem-order-dependent digest.

The per-event fields earlier described as:

```text
trace_source_sha256
policy_call_source_sha256
public_transition_source_sha256
```

mean the corresponding exact source-record SHA-256 values defined
above.

For a nonexecuted attempt:

```text
public_transition_source_pointer = null
```

For an environment-error attempt without a public transition:

```text
public_transition_source_pointer = null
```

No fabricated transition record is permitted.

---

## 19.7 Normative implementation-task decomposition

This subsection supersedes the earlier four-task numbering in Section 11.

The approved implementation sequence after plan approval is five
independently sealed tasks.

### Task 1 — Source-access and registration contracts

Implement only:

```text
SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1
REGISTERED_FAILURE_SEQUENCE_WINDOW_V1
source-record pointer contract
```

No Sequence Failure Experience builder yet.

Suggested commit:

`Define sequence source and registration contracts`

### Task 2 — Canonical factual experience wire contract

Implement only:

```text
SequenceFailureEventV1
SequenceFailureRelevantStartV1
SequenceFailureObservedEndV1
SequenceFailureExperienceV1

strict wire parsing
canonical serialization
domain-separated experience identity
```

Suggested commit:

`Define factual sequence experience contract`

### Task 3 — Source evidence binding

Bind:

```text
task-access record
EpisodeArtifact
ActionTrace
PolicyCallEvidence
PublicTransition
attempt bundle
registered range
```

The complete episode is validated before slicing.

Suggested commit:

`Bind sequence experience to episode evidence`

### Task 4 — Deterministic factual reconstruction

Implement:

`build_sequence_failure_experience_v1(...)`

including:

- complete preceding-prefix binding;
- exact registered range;
- factual event construction;
- derived transition indices;
- deterministic terminal/future-information rule;
- exact source-record pointers.

Suggested commit:

`Build deterministic factual failure sequences`

### Task 5 — Read-only materializer candidate and static audit

Implement the write-once offline materializer candidate.

No real sequence materialization is authorized.

Suggested commit:

`Build sequence experience materializer candidate`

Each Task must independently complete:

```text
RED
→ GREEN
→ focused tests
→ full applicable regression
→ compile
→ diff/scope audit
→ source review
→ single-purpose commit
→ push
→ local/remote equality
→ clean worktree
```

---

## 19.8 Additional required adversarial tests

The fixed plan must additionally prove:

```text
wrong task-access protected-manifest identity
→ fail

wrong task-access record SHA
→ fail

wrong task-gamefile group binding
→ fail

non-TRAIN_MEMORY_SOURCE active source
→ fail

registration label promoted to fact authority
→ fail

one-null / one-non-null recovery range
→ fail

recovery starts before registered failure marker
→ fail

missing required preceding prefix binding
→ fail

terminal fields present outside registered final call
→ fail

terminal fields missing when whole-episode final call is included
→ fail

environment steps assumed from model-call arithmetic
→ fail

wrong JSONL source line hash
→ fail

wrong JSONL line index
→ fail

missing policy_calls.jsonl
→ fail

legacy/incomplete source bundle silently accepted
→ fail
```

These tests supplement, rather than replace, the adversarial tests
already specified above.

---

## 19.9 Fixed-plan review disposition

After this amendment is committed and independently reviewed, the plan
may proceed to the existing approval gate.

Until then:

```text
PRODUCTION_IMPLEMENTATION
=
NOT_AUTHORIZED
```


# 20. Plan approval gate

Current authorization:

```text
UNIT2_IMPLEMENTATION_PLAN
=
CANDIDATE_FOR_HUMAN_REVIEW

PRODUCTION_IMPLEMENTATION
=
NOT_AUTHORIZED

REAL_MATERIALIZATION
=
NOT_AUTHORIZED

SCIENTIFIC_EXECUTION
=
NOT_AUTHORIZED
```

Required approval token:

`PLAN_APPROVED_FAILURE_MEMORY_SEQUENCE_EXPERIENCE_V1`

Until that exact approval is given, no Unit-2 production implementation
may be written.
