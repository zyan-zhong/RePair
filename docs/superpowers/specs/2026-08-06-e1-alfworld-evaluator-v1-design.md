# E1 ALFWorld Evaluator V1 Design

## Approval and status

```text
DESIGN_ID=E1_ALFWORLD_EVALUATOR_V1
DESIGN_REVISION=1.2

DESIGN_APPROVAL=
DESIGN_APPROVED_E1_ALFWORLD_EVALUATOR_V1

DESIGN_STATUS=APPROVED_PENDING_DESIGN_PR_MERGE

IMPLEMENTATION_PLAN=NOT_AUTHORIZED
IMPLEMENTATION_STATUS=NOT_STARTED

REAL_ENVIRONMENT_EXECUTION=NOT_APPROVED
MODEL_EXECUTION=NOT_APPROVED
ENGINEERING_SMOKE_EXECUTION=NOT_APPROVED
E1_DEV_EXECUTION=NOT_APPROVED
E1_CONFIRMATORY_EXECUTION=NOT_APPROVED
```

This approval authorizes only a design-only pull request. It does not
authorize evaluator implementation, a real ALFWorld environment, vLLM,
model calls, `env.step()`, engineering smoke, or E1 execution.

## Frozen repository starting point

The evaluator design consumes the already merged split/access state:

```text
SPLIT_AND_ACCESS_V1 merge commit=
97ce6358bb2b0db345f67b3bc6278f7d81a028bb

access_mode=
TRUSTED_MANIFEST_DIRECT_V1

dataset_version=
json_2.1.1

split=
valid_unseen

task_count=
134

task_manifest=
data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl

task_manifest_sha256=
6e480bb663a6f17207aa2c7a6e1b504adad8448f6e8a2615c5e62fea0b64c0f4
```

The task manifest is target-host-bound through server-local absolute
`gamefile` paths. Relocation requires manifest regeneration and a new
`SPLIT_AND_ACCESS_V1` freeze.

## Research objective

The evaluator must accurately measure what an off-the-shelf,
project-unadapted `Qwen/Qwen2.5-3B-Instruct` policy can do under the
complete-menu, controller-free R0 condition.

It must preserve sufficient non-leaking public evidence for later:

- phase-critical failure analysis;
- pivotal-transition analysis;
- causal credit assignment;
- benefit/harm evidence construction;
- SFT, preference, and audited-RL dataset lineage.

The evaluator is an experimental measurement instrument. Errors in task
identity, model-visible input, action execution, budget accounting,
termination, retry resolution, or evidence publication can invalidate the
full 134-task × 5-seed experiment.

---

# 1. Formal identifiers

```text
POLICY_TRANSPORT_ID=
VLLM_CHAT_COMPLETIONS_QWEN_NATIVE_V1

POLICY_REQUEST_ID=
E1_POLICY_REQUEST_V1

RUN_SCHEDULE_ID=
E1_RUN_SCHEDULE_V1

ENVIRONMENT_ADAPTER_ID=
ALFWORLD_EXACT_SINGLETON_TEXTWORLD_V1

ENVIRONMENT_RUNTIME_MANIFEST_ID=
ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1

GAMEFILE_IDENTITY_MANIFEST_ID=
E1_GAMEFILE_SHA256_PREFLIGHT_V1

PUBLIC_TRANSITION_SCHEMA=
E1_PUBLIC_TRANSITION_RECORD_V1

EPISODE_ARTIFACT_SCHEMA=
E1_EPISODE_ARTIFACT_V1

ATTEMPT_RECEIPT_SCHEMA=
E1_ATTEMPT_RECEIPT_V1

CELL_LOCK_SCHEMA=
E1_SCIENTIFIC_CELL_LOCK_V1
```

Existing frozen contracts remain authoritative:

```text
RAW_WITH_MENU_V1
RAW_POLICY_PROMPT_V1
RAW_POLICY_PARSER_V1
MEMORY_M0_V1
E1_RUNTIME_CORE_V1_60_30_3_256
ActionTrace / RAW_V1
SPLIT_AND_ACCESS_V1
```

---

# 2. Architecture and trusted boundaries

## 2.1 Evaluator only orchestrates

The evaluator must call the frozen Runtime Core for:

- three-party menu equality;
- pre-policy budget and protocol gating;
- strict response parsing;
- exact case-sensitive admissibility;
- 60/30/3 budget transitions;
- environment-step reservation;
- environment-result finalization;
- termination precedence.

It must not independently implement, approximate, or repair those semantics.

Forbidden evaluator behavior includes:

```text
action repair
action replacement
fuzzy matching
case normalization
menu sorting
menu filtering
menu deduplication
menu truncation
budget recomputation
termination rewriting
hidden controller logic
phase inference
```

## 2.2 Layered components

| Component | Sole responsibility |
|---|---|
| `TaskManifestLoader` | Verify and expose the exact frozen task records |
| `ExactGameEnvironmentFactory` | Create a singleton environment for one exact gamefile |
| `AlfworldEnvironmentAdapter` | Strictly validate reset/step batch structures |
| `PolicyClient` | Send one exact frozen request and return raw generation evidence |
| `EpisodeEvaluator` | Orchestrate prompt, Runtime Core, environment, traces, and termination |
| `TraceAssembler` | Build single-action `ActionTrace` records |
| `EpisodeTraceSequenceValidator` | Validate cross-trace causal and counter continuity |
| `EpisodeArtifactPublisher` | Publish complete immutable attempt directories atomically |
| `RunResolver` | Enforce schedule, retry, cell lock, and no-best-of-run rules |

Environment, policy transport, scientific state, and artifact publication are
separate interfaces. Tests inject fakes rather than executing a real
environment or model.

---

# 3. Exact task selection and byte identity

## 3.1 No directory scan

The evaluator must consume the repository manifest in its original order and
must not select tasks through directory traversal.

Before a run starts, it must verify:

```text
manifest SHA-256 matches frozen value
record count = 134
indices = 0..133
IDs = alfworld_valid_unseen_all134_0000..0133
split = valid_unseen for every record
gamefile values are unique
no extra or missing record
original record order preserved
```

## 3.2 Per-task path and file checks

Before environment construction:

```text
gamefile exists
gamefile is a regular file
gamefile is not a symlink
resolved gamefile equals the frozen manifest path
manifest SHA-1 equals actual SHA-1
frozen preflight SHA-256 equals actual SHA-256
task ID/index/type/split match the frozen record
```

The evaluator does not read or depend on `traj_data.json`, expert plans,
hidden PDDL facts, or expert annotations.

## 3.3 Frozen SHA-256 preflight

`E1_GAMEFILE_SHA256_PREFLIGHT_V1` records for all 134 selected tasks:

```text
index
task_id
manifest gamefile SHA-1
expected gamefile SHA-256
```

A SHA-256 computed only at runtime, without comparison to a pre-frozen value,
is insufficient.

---

# 4. Exact model-visible input

## 4.1 Endpoint and message shape

The policy endpoint is exactly:

```text
/v1/chat/completions
```

The message list is exactly:

```json
[
  {
    "role": "user",
    "content": "<exact RAW_POLICY_PROMPT_V1 text>"
  }
]
```

The API request contains no explicit:

```text
system message
assistant prefill
tools
tool_choice
parallel_tool_calls
response_format
structured output
guided decoding
reasoning parser
documents/RAG
LoRA
```

The absence of an API-level system message does not imply the rendered token
sequence has no template-defined system prefix. The actual scientific input
is the exact rendered prompt and token sequence.

## 4.2 Model, tokenizer, and template identity

Freeze and bind:

```text
model repository=
Qwen/Qwen2.5-3B-Instruct

model revision=
aa8e72537993ba99e69dfaafa59ed015b17504d1

tokenizer revision=
aa8e72537993ba99e69dfaafa59ed015b17504d1

tokenizer manifest SHA-256
tokenizer_config.json SHA-256
special_tokens_map SHA-256
chat template exact UTF-8 SHA-256
```

For every request, record and compare:

```text
raw_policy_prompt_sha256
chat_template_sha256
rendered_prompt_text_sha256
rendered_token_ids_sha256
prompt_token_count
```

The server-returned prompt token IDs must match the locally rendered token IDs
for the same frozen tokenizer/template revision. Mismatch is a
run-invalidating protocol configuration error before a completed generation
enters Runtime Core.

## 4.3 vLLM startup identity

Freeze:

```text
vLLM version=0.11.0
dtype=bfloat16
tensor_parallel_size=1
served_model_name=Qwen2.5-3B-Instruct-E1
generation_config_mode=vllm
chat_template_content_format=string
request_id_headers=enabled
```

The service must explicitly use:

```text
--revision aa8e72537993ba99e69dfaafa59ed015b17504d1
--served-model-name Qwen2.5-3B-Instruct-E1
--dtype bfloat16
--tensor-parallel-size 1
--generation-config vllm
--chat-template <frozen exact template file>
--chat-template-content-format string
--enable-request-id-headers
```

The model repository's generation configuration must not silently override
the frozen experiment request.

---

# 5. E1_POLICY_REQUEST_V1

## 5.1 Canonical request

The client sends canonical UTF-8 JSON bytes rather than relying on an SDK to
silently omit nulls or alter the request shape.

Each request freezes:

```json
{
  "model": "Qwen2.5-3B-Instruct-E1",
  "messages": [
    {
      "role": "user",
      "content": "<exact RAW_POLICY_PROMPT_V1 text>"
    }
  ],
  "temperature": 0.2,
  "top_p": 0.95,
  "max_tokens": 128,
  "seed": "<scheduled seed>",
  "n": 1,
  "stream": false,
  "stop": null,
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0,
  "logprobs": false,
  "top_logprobs": null,
  "best_of": null,
  "use_beam_search": false,
  "top_k": -1,
  "min_p": 0.0,
  "repetition_penalty": 1.0,
  "length_penalty": 1.0,
  "stop_token_ids": [],
  "include_stop_str_in_output": false,
  "ignore_eos": false,
  "min_tokens": 0,
  "skip_special_tokens": true,
  "spaces_between_special_tokens": true,
  "truncate_prompt_tokens": null,
  "prompt_logprobs": null,
  "allowed_token_ids": null,
  "bad_words": [],
  "echo": false,
  "add_generation_prompt": true,
  "continue_final_message": false,
  "add_special_tokens": false,
  "documents": null,
  "chat_template": null,
  "chat_template_kwargs": {},
  "structured_outputs": null,
  "priority": 0,
  "return_token_ids": true,
  "request_id": "<deterministic request id>"
}
```

The following keys must be absent:

```text
tools
tool_choice
parallel_tool_calls
response_format
guided_json
guided_regex
guided_choice
guided_grammar
logits_processors
vllm_xargs
```

Prompt truncation is forbidden. If the rendered prompt plus 128 generation
tokens exceeds the frozen context limit, the evaluator must not call the
model and must invalidate the run as a protocol configuration error.

## 5.2 Response contract

A completed generation exists only when all hold:

```text
HTTP status = 200
body is a valid JSON object
choices contains exactly one item
choice.message.content is a string
finish_reason exists
usage.prompt_tokens is a non-negative integer
usage.completion_tokens is a non-negative integer
provider response/request ID exists
returned prompt token IDs match the frozen local rendering
```

Record:

```text
canonical_request_json_sha256
exact_request_body_sha256
exact_raw_response_body_sha256
raw_model_response_sha256
rendered_token_ids_sha256
finish_reason
prompt_tokens
completion_tokens
requested_seed
client_request_id
provider_request_id
latency_ms
```

`finish_reason="length"` is still a completed generation. The actual truncated
text is passed to the strict parser and consumes one policy attempt.

Transport, HTTP, malformed envelope, or prompt-token alignment failure:

```text
does not consume a policy attempt
does not call env.step
SCIENTIFIC_OUTCOME_NOT_PRODUCED
PRE_RESULT_INFRASTRUCTURE_ERROR
```

Automatic and hidden retries are zero.

---

# 6. Strict menu snapshot

Never directly call:

```python
tuple(current_info["admissible_commands"][0])
```

Validation order:

```text
1. infos must be a mapping.
2. admissible_commands must exist.
3. outer batch must be a stable Sequence.
4. outer batch must not be str/bytes/bytearray/mapping/iterator.
5. outer batch length must be exactly 1.
6. inner menu must be a stable Sequence.
7. inner menu must not be str/bytes/bytearray/mapping/iterator.
8. when done=false, inner menu must contain at least one item.
9. when done=true, an empty menu is permitted.
10. create exactly one immutable tuple snapshot.
```

The exact same tuple object and sequence SHA-256 are used for:

```text
validate_runtime_preconditions
build_raw_policy_prompt
process_completed_generation
ActionTrace
PublicTransitionRecord.pre_action_admissible_commands
```

The evaluator must not re-read or rebuild the menu between policy gating and
environment action processing.

---

# 7. Exact ALFWorld environment

## 7.1 Process isolation and registration

Each execution attempt runs in a fresh spawned Python process.

The exact environment contract is:

```text
gamefiles=[exact frozen gamefile]
batch_size=1
asynchronous=false
auto_reset=false
max_episode_steps=31
```

Requested `EnvInfos`:

```text
won=true
admissible_commands=true
extras=["gamefile"]
```

Wrapper order:

```text
AlfredDemangler(shuffle=false)
AlfredInfos
```

Forbidden environment features:

```text
AlfredExpert
expert_plan
policy_commands
facts
directory game collection
domain randomization
auto reset
```

The registration ID is deterministically derived from:

```text
run_id
scheduled_cell_id
execution_attempt_id
```

and is never reused.

`max_episode_steps=31` exists only to keep the TextWorld wrapper from
preempting the frozen 30-step Runtime Core limit. The evaluator never issues a
31st environment action.

## 7.2 Environment runtime manifest

`ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1` binds:

```text
Python version
Python executable identity
ALFWorld distribution version
ALFWorld source/commit identity
TextWorld version
Gym version
AlfredTWEnv source SHA-256
AlfredDemangler source SHA-256
AlfredInfos source SHA-256
textworld.gym.register_games source SHA-256
wrapper order
exact EnvInfos request
batch_size=1
asynchronous=false
auto_reset=false
max_episode_steps=31
fresh spawned process per attempt
```

Each attempt records this manifest SHA-256.

---

# 8. Reset contract and task identity latch

## 8.1 Reset batch validation

`reset()` must return one valid batch:

```text
observations outer length = 1
infos is a mapping
observation[0] is a string
admissible_commands satisfies the strict menu contract
extra.gamefile exists
extra.gamefile outer batch length = 1
extra.gamefile[0] is a non-empty string
```

The resolved reset gamefile must equal the frozen exact gamefile.

Successful reset validation creates:

```text
latched_gamefile_identity=
resolved exact frozen gamefile
```

Manifest/gamefile mismatch, invalid menu, or public goal parser failure is a
run-invalidating protocol configuration error. A constructor or reset
exception, or malformed reset batch, is a pre-result infrastructure error.

## 8.2 Step extra.gamefile is optional-if-present

Step does not require `extra.gamefile` to be present.

Rules:

```text
key missing:
    accepted

value is None:
    accepted

batch length 1 and element is None:
    accepted

batch length 1 and element is a string:
    resolved value must equal latched_gamefile_identity

other type, length, or non-null mismatch:
    PRE_RESULT_INFRASTRUCTURE_ERROR
    ENVIRONMENT_CONTRACT_ERROR
```

Task identity after reset is guaranteed by:

```text
singleton registered game
fresh spawned process
batch_size=1
auto_reset=false
reset-time exact-game verification
latched_gamefile_identity
```

---

# 9. Public task goal and observation

The public goal comes only from the full public reset observation.

`ALFWORLD_PUBLIC_GOAL_V1`:

```text
split the complete observation with splitlines()
require exactly one line beginning "Your task is to:"
remove only one fixed leading space after the colon
require a non-empty result
preserve the complete original observation unchanged
```

Zero or multiple matches invalidate the run as a protocol configuration
error.

The evaluator must not derive the goal from:

```text
traj_data.json
expert annotation
PDDL state
facts
expert plan
hidden environment state
```

---

# 10. Single-episode state machine

```text
1. Verify run, schedule, protocol, model, environment, and manifest hashes.
2. Load exactly one scheduled manifest record.
3. Verify gamefile path and SHA-1/SHA-256 identity.
4. Spawn one fresh environment process.
5. Create the exact singleton environment.
6. env.reset().
7. Validate reset batch, menu, gamefile, and public goal.
8. Initialize:
       BudgetState()
       executed_history=()
       feedback=None
       current_observation
       current_menu_snapshot
       latched_gamefile_identity
9. Loop:
       a. Validate runtime preconditions using one menu snapshot.
       b. If policy call is not authorized, terminate.
       c. Build RAW_POLICY_PROMPT_V1.
       d. Render and verify exact model tokens.
       e. Send one E1_POLICY_REQUEST_V1 request.
       f. Validate the complete response envelope.
       g. Process the completed generation through Runtime Core.
       h. If should_call_env=false:
              write ActionTrace
              update frozen feedback
              do not update history/state/menu
              resolve termination
              continue
       i. Call env.step([exact candidate action]) exactly once.
       j. Validate the complete step result before finalization.
       k. Call finalize_environment_result().
       l. Build ActionTrace.
       m. For an accepted environment result, build PublicTransitionRecord.
       n. Only for an accepted executed result:
              update executed history
              update observation/menu
       o. Resolve done/won/Runtime Core termination.
10. Establish the immutable scientific outcome when available.
11. Validate the complete trace sequence.
12. Write attempt staging bytes and receipts.
13. Publish the complete directory atomically.
14. Close/terminate the fresh environment process and record operational state.
```

---

# 11. Step result validation and finalization

Correct order:

```text
env.step([action])
→ validate complete four-item result
→ validate every batch and scalar
→ determine environment contract status
→ finalize_environment_result()
→ assemble trace and public transition
→ update history/current state only after accepted result
```

Requirements:

```text
result contains exactly four items
observations/scores/dones/infos outer lengths are exactly 1
resulting_observation is str
type(done) is bool
type(won) is bool
score is finite int/float and not bool
infos is mapping
resulting menu satisfies strict structural validation
optional-if-present gamefile matches the reset latch
```

Never coerce done/won through `bool(value)`.

Result matrix:

| done | won | Meaning |
|---:|---:|---|
| false | false | Continue |
| true | true | Scientific success |
| true | false | Scientific task failure |
| false | true | Pre-result infrastructure contract error |

Score is audit evidence only and never determines success.

If step raises or returns malformed evidence:

```text
finalize_environment_result(
    infrastructure_error=True,
    environment_terminated=False
)
```

The reserved environment step is not rolled back. No resulting public state
or executed-history transition is fabricated.

---

# 12. PublicTransitionRecord

For every accepted environment result, record:

```text
model_call_index
environment_step_index
submitted_action

pre_action_observation
pre_action_observation_sha256
pre_action_admissible_commands
pre_action_admissible_commands_sha256

resulting_observation
resulting_observation_sha256
resulting_admissible_commands
resulting_admissible_commands_sha256

done
won
score
```

Visibility classes:

```text
pre_action_* =
POLICY_VISIBLE_BEFORE_ACTION

resulting_* / done / won / score =
POST_ACTION_PUBLIC_AUDIT_ONLY

host paths / local exception internals =
LOCAL_EXECUTION_ONLY
```

The complete raw `infos` mapping is not persisted.

Resulting public state becomes policy-visible only in the next decision, if
the episode continues.

---

# 13. Environment-call and transition counts

The previous equality between all environment calls and public transitions is
not valid.

Freeze three distinct quantities:

```text
environment_call_trace_count
=
count(traces where env.step was actually invoked)
```

Equivalently:

```text
count(
    ACTION_EXECUTED traces with environment_step_index
    +
    INFRASTRUCTURE_ERROR traces with environment_step_index
)
```

```text
public_transition_count
=
count(
    ACTION_EXECUTED traces whose complete environment result
    passed validation and has exactly one PublicTransitionRecord
)
```

```text
final_environment_step_count
=
environment_call_trace_count
```

An `INFRASTRUCTURE_ERROR` environment-call trace:

```text
has environment_step_index
has no PublicTransitionRecord
has no resulting observation/menu/done/won/score
does not update history/current public state
```

No synthetic transition may be created to satisfy a count.

---

# 14. E1_RUN_SCHEDULE_V1 and retries

## 14.1 Immutable schedule

```text
task_count=134
replicate_seeds=[17,31,47,73,101]
cell_count=670
order=seed-major
primary_statistical_unit=unique_task
replicates_are_not_independent_tasks=true
pooled_670_iid_headline_result=forbidden
```

Cell identity:

```text
scheduled_cell_id=
e1-t<task_index_4_digits>-s<seed_10_digits>
```

Attempt identity:

```text
execution_attempt_id=
<scheduled_cell_id>-a<attempt_ordinal_3_digits>
```

Track separately:

```text
scheduled_cell_id
execution_attempt_id
attempt_ordinal
canonical_resolution
```

## 14.2 Retry rules

Evaluator and HTTP client perform no automatic retry.

An explicit new attempt is permitted only when no scientific result was
produced because of a pre-result infrastructure failure.

Every retry preserves exactly:

```text
task
seed
model revision
tokenizer/template identity
canonical request
Runtime Core protocol
environment runtime manifest
gamefile identity
evaluator commit
all configuration hashes
```

The first valid scientific result locks the scheduled cell. No further model
call is allowed for that cell.

A protocol configuration error invalidates the complete run. It is not a
cell-level retry. A correction requires a new run ID, schedule hash, and
code/config identity.

All attempts are retained. Best-of-run selection is forbidden.

---

# 15. Scientific and operational state separation

Each attempt carries both:

```text
scientific_outcome_status
operational_finalization_status
```

Scientific states:

```text
SCIENTIFIC_OUTCOME_NOT_PRODUCED
SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS
SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE
```

Operational states:

```text
STAGING
PUBLISHED
PUBLICATION_PENDING
CLOSE_FAILED_RECORDED
ARTIFACT_IO_FAILED
```

Once a scientific outcome exists:

```text
compute immutable semantic bytes
compute episode_semantic_sha256
write a no-clobber scientific cell lock
never call the model again for that cell
```

Publication failure may only retry publication from the same immutable staging
bytes. It may not produce a new trajectory.

If staging bytes are lost, the cell remains unresolved in the current run and
cannot be silently replaced by another random model attempt.

A close failure does not automatically erase a completed scientific outcome,
but it must be recorded and satisfy the final result-gate conditions below.

---

# 16. ActionTrace and episode sequence validation

Existing `ActionTrace` remains the single-record contract.

`EpisodeTraceSequenceValidator` must validate before publication:

```text
model_call_index is contiguous from 0
environment_step_index is contiguous across all actual env calls
trace[i].budget_after == trace[i+1].budget_before
task/seed/model/config provenance is constant within the episode
nonexecuted attempts preserve observation/menu/M0
accepted resulting observation equals the next trace observation
accepted resulting menu equals the next pre-action menu
failure feedback propagates exactly
feedback clears after successful execution
M0 hashes recompute from accepted executed transitions
final budget equals the last trace budget_after
trace count equals action_traces.jsonl line count
public transition count follows Section 13
environment call count follows Section 13
final environment step count follows Section 13
termination reason is coherent with the final state
episode success is coherent with final done/won
```

Additionally:

```text
each PublicTransitionRecord maps to exactly one ACTION_EXECUTED trace
each ACTION_EXECUTED accepted result maps to exactly one PublicTransitionRecord
INFRASTRUCTURE_ERROR traces map to no PublicTransitionRecord
```

---

# 17. Attempt artifacts and atomic publication

## 17.1 Run layout

```text
runs/<run_id>/
    run_schedule.json
    run_runtime_manifest.json

    attempt_ledger/
        <attempt_id>.started.json
        <attempt_id>.terminal.json

    attempts/
        .staging/<attempt_id>/
        <attempt_id>/

    cell_locks/
        <scheduled_cell_id>.json
```

Published attempt bundle:

```text
attempt.json
action_traces.jsonl
public_transitions.jsonl
SHA256SUMS
```

Serialization rules:

```text
action_traces.jsonl line =
ActionTrace.to_json() + LF

action trace order =
model_call_index ascending

public transition order =
environment_step_index ascending

SHA256SUMS order =
fixed

SHA256SUMS does not hash itself
```

## 17.2 Directory-level publication

```text
write complete staging directory
→ validate JSON and JSONL
→ EpisodeTraceSequenceValidator
→ fsync every file
→ fsync staging directory
→ no-clobber rename the entire directory
→ fsync attempts parent directory
```

Individual files are never published separately.

Each created attempt has exactly one started receipt and exactly one terminal
receipt, including early failures.

---

# 18. Semantic and exact identities

## 18.1 Scientific semantic identity

`episode_semantic_sha256` includes only:

```text
scheduled cell identity
task/gamefile identity
seed
model/runtime/request/config hashes
ordered model-visible states
ordered raw model response texts
ordered actions
ordered public transition states
budgets
done/won/score
scientific success/termination
```

It excludes:

```text
timestamps
latency
hostname
provider request ID
temporary paths
local exception messages
attempt ordinal
```

## 18.2 Exact bundle identity

`attempt_bundle_sha256` is derived from the fixed ordered set of published
file hashes.

It is written into the cell lock and terminal receipt, not into a file whose
own bytes participate in the same self-referential hash.

---

# 19. Scientific cell lock and published-bundle correspondence

Each scientific cell lock binds:

```text
scheduled_cell_id
execution_attempt_id
episode_semantic_sha256
attempt_bundle_sha256
scientific_outcome_status
```

Every lock must match exactly one published scientific attempt bundle, and
every published scientific attempt bundle must match exactly one lock.

Required equality:

```text
bundle scheduled_cell_id == lock scheduled_cell_id
bundle attempt_id == lock attempt_id
bundle semantic SHA-256 == lock semantic SHA-256
bundle exact bundle SHA-256 == lock bundle SHA-256
```

---

# 20. Final result-audit gate

`RESULT_AUDIT_APPROVED` requires all of:

```text
scheduled_cells = 670
scientifically_resolved_cells = 670

scientific_cell_locks = 670
published_scientific_attempt_bundles = 670

cell_locks_without_matching_published_bundle = 0
published_bundles_without_matching_cell_lock = 0

publication_pending = 0
artifact_io_failed_unresolved = 0
missing_terminal_receipts = 0
checksum_failures = 0

duplicate_cell_resolutions = 0
missing_task_seed_cells = 0
unresolved_protocol_errors = 0
unresolved_pre_result_infrastructure_cells = 0
best_of_run_selection = 0
```

The canonical scientific result count is:

```text
SUCCESS + TASK_FAILURE = 670
```

Total attempt count may exceed 670 because pre-result infrastructure failures
are retained.

## 20.1 Lost staging

A completed scientific outcome whose immutable staging bytes are lost remains
unresolved. It cannot be replaced by a new trajectory within the same run.

## 20.2 CLOSE_FAILED_RECORDED

A close failure may coexist with an accepted scientific result only if:

```text
the complete artifact bundle is published
checksums and sequence validation pass
the fresh spawned process is confirmed exited
there is no cross-attempt environment or registry contamination
the close failure is recorded in local operational evidence
no new model attempt is made for the cell
```

Otherwise the operational state remains unresolved and result approval fails.

---

# 21. Failure taxonomy

## 21.1 Run-invalidating protocol configuration errors

```text
manifest hash/record/order mismatch
gamefile SHA-1 or SHA-256 mismatch
reset extra.gamefile mismatch
goal parser contract failure
illegal menu
non-terminal empty menu
run/schedule/config/protocol hash mismatch
rendered prompt token mismatch
```

## 21.2 Pre-result infrastructure errors

```text
environment constructor exception
reset exception
malformed reset batch
policy transport/HTTP failure
malformed policy response envelope
step exception
malformed step batch
done/won wrong type
score non-finite or wrong type
won=true and done=false
non-null step gamefile identity mismatch
```

These can create a new explicit attempt only while the cell has no scientific
outcome.

## 21.3 Post-result operational errors

```text
artifact publication failure
directory rename/fsync failure
close failure
terminal receipt failure
```

These never authorize a new model trajectory.

---

# 22. Test requirements

Normal tests use injected fake policy and fake environment only.

## 22.1 Manifest and identity tests

```text
wrong manifest hash
missing/extra/reordered record
duplicate task/gamefile
wrong split
missing or symlinked gamefile
SHA-1 mismatch
SHA-256 mismatch
reset extra.gamefile mismatch
```

## 22.2 Menu tests

```text
outer str/bytes/mapping/iterator rejected
inner str/bytes/mapping/iterator rejected
batch length not 1 rejected
duplicate commands preserved
menu order preserved
non-terminal empty menu rejected
terminal empty menu allowed
one immutable snapshot reused
```

## 22.3 Reset/step adapter tests

```text
reset batch malformed
reset gamefile required and latched
step gamefile missing accepted
step gamefile None accepted
step non-null gamefile mismatch rejected
step result not exactly four items
wrong outer lengths
observation not str
done/won not strict bool
score invalid/non-finite
all done/won combinations
close/process cleanup tracking
```

## 22.4 Runtime orchestration tests

```text
first-step success
format failure → off-list → success
three consecutive nonexecuted attempts
policy attempt 60
environment step 30
invalid menu before policy call
policy transport failure
env.step exception
reserved step is not rolled back
failed response does not enter M0
only accepted transitions enter M0
```

## 22.5 Sequence tests

```text
missing/reordered/duplicate trace
budget discontinuity
observation/menu discontinuity
feedback discontinuity
M0 mismatch
environment call count mismatch
public transition count mismatch
infrastructure trace with fabricated transition
termination inconsistency
```

## 22.6 Schedule and retry tests

```text
exact 670 cells
seed-major order
stable cell/attempt IDs
no retry after scientific lock
pre-result retry preserves all hashes
protocol error invalidates run
no best-of-run selection
all failed attempts retained
```

## 22.7 Artifact tests

```text
directory-level atomic publication
no-clobber
partial staging is not published
JSON/JSONL validation
fixed checksum ordering
cell-lock/bundle one-to-one mapping
publication retry uses identical bytes
lost staging remains unresolved
started and terminal receipt completeness
result audit gate rejects every orphan/pending/failure condition
```

Tests must not:

```text
create a real ALFWorld environment
call real vLLM
use a GPU
run the formal manifest
perform a real env.step
```

---

# 23. Scope exclusions

V1 does not implement:

```text
Phase-Critical Harness
phase inference
failure diagnosis
trajectory ranking
parallel environment batches
distributed scheduler
automatic hidden retry
training
LoRA
S1 P1–P20
inventory collection
formal E1 execution
```

V1 implements only:

```text
exact frozen task identity
exact model-visible input
exact generation request
exact environment interface
frozen Runtime Core orchestration
complete public evidence
correct retry and result resolution
auditable atomic artifacts
```

---

# 24. Governance sequence

```text
1. DESIGN_APPROVED_E1_ALFWORLD_EVALUATOR_V1
2. merge this design-only PR
3. write a detailed implementation plan
4. PLAN_APPROVED_E1_ALFWORLD_EVALUATOR_V1
5. write RED tests
6. implement in reviewed tasks
7. focused reviews
8. cumulative evaluator review
9. CODE_APPROVED_E1_ALFWORLD_EVALUATOR_V1
10. approve environment-only adapter smoke
11. exact-game/reset/menu/fixed-action smoke
12. audit environment-only smoke evidence
13. approve model-integrated smoke
14. 1–3 task vLLM engineering smoke
15. audit integrated smoke evidence
16. E1_DEV_EXECUTION_APPROVED
17. execute the formal 670-cell run
```

The first smoke does not call a model. The second smoke uses real vLLM.
Neither contributes to E1 results.

---

# 25. References

- vLLM 0.11.0 OpenAI protocol:
  https://docs.vllm.ai/en/v0.11.0/api/vllm/entrypoints/openai/protocol.html
- vLLM OpenAI-compatible server:
  https://docs.vllm.ai/en/v0.11.0/serving/openai_compatible_server.html
- Qwen2.5-3B-Instruct:
  https://huggingface.co/Qwen/Qwen2.5-3B-Instruct
- ALFWorld TextWorld environment implementation:
  https://github.com/alfworld/alfworld/blob/master/alfworld/agents/environment/alfred_tw_env.py
- TextWorld filter wrapper:
  https://textworld.readthedocs.io/en/1.6.2/_modules/textworld/envs/wrappers/filter.html
- TextWorld Gym batch utilities:
  https://textworld.readthedocs.io/en/latest/_modules/textworld/gym/utils.html
