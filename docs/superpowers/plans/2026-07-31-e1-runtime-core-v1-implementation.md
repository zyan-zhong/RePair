# E1 Runtime Core V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox syntax for tracking.

**Goal:** Implement the pure, deterministic runtime core for E1
`RAW_WITH_MENU_V1` without importing ALFWorld, vLLM, model clients,
PyTorch or historical controllers.

**Architecture:** Four focused modules implement strict response parsing,
deterministic prompt construction, immutable dual-budget accounting and
pure runtime decisions. `ActionTrace` is extended compatibly after the
standalone components pass their own tests. The runtime core never calls
a model or `env.step()`.

**Tech Stack:** Python 3.12, standard library, frozen dataclasses, enums,
JSON, SHA-256, pytest.

## Global Constraints

- `max_policy_attempts = 60`
- `max_environment_steps = 30`
- `max_consecutive_nonexecuted_attempts = 3`
- `max_action_codepoints = 256`
- Every completed generation consumes one policy attempt.
- Format failure and inadmissible action consume no environment step.
- Stage 1–2 failures are `FORMAT_PROTOCOL_FAILURE`.
- Stage 3 failure is `ACTION_NOT_ADMISSIBLE`.
- Duplicate JSON members must be rejected.
- The only action normalization is `action.strip(" ")`.
- Matching is exact and case-sensitive.
- Complete-menu order, count and strings must be preserved.
- No implementation may import ALFWorld, vLLM, OpenAI, Torch or a
  historical controller.
- No task-specific correction, canonicalisation or nearest-action repair.
- Existing historical `ActionTrace` construction must remain compatible.
- Every task follows red → green → full regression → commit.

- Current memory contract is `MEMORY_M0_V1`: exactly the final
  eight executed environment transitions.
- Failed or nonexecuted policy responses never enter M0.
- No retrieval, summarisation, compression, learned writer or
  external memory store is implemented in Runtime Core V1.
- `CODE_APPROVED` does not imply `EXECUTION_APPROVED`.
- No ALFWorld, vLLM, GPU, model or all134 execution is authorised
  by completion of this plan.
- `SPLIT_AND_ACCESS_V1` must be frozen before any E1 execution
  approval.
- E1-Dev and E1-Confirmatory are separate stages with separate
  manifests, access rules and output-visibility policies.
- Closed-source distillation is outside Runtime Core V1.
- Research Planner and automatic policy-promotion rules are
  outside Runtime Core V1.

---

### Task 1: Strict Envelope Parser and Action Normalization

**Files:**
- Create: `src/pchsi/evaluation/raw_policy_parser.py`
- Create: `tests/evaluation/test_raw_policy_parser.py`

**Interfaces:**

```python
class ParserStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"

class FailureStage(str, Enum):
    ENVELOPE = "envelope"
    ACTION_NORMALIZATION = "action_normalization"

class ParserFailureCode(str, Enum):
    ENVELOPE_INVALID_JSON = "ENVELOPE_INVALID_JSON"
    ENVELOPE_TRAILING_DATA = "ENVELOPE_TRAILING_DATA"
    ENVELOPE_TOP_LEVEL_NOT_OBJECT = "ENVELOPE_TOP_LEVEL_NOT_OBJECT"
    ENVELOPE_DUPLICATE_MEMBER = "ENVELOPE_DUPLICATE_MEMBER"
    ENVELOPE_MEMBER_COUNT_INVALID = "ENVELOPE_MEMBER_COUNT_INVALID"
    ENVELOPE_MEMBER_NAME_INVALID = "ENVELOPE_MEMBER_NAME_INVALID"
    ENVELOPE_ACTION_NOT_STRING = "ENVELOPE_ACTION_NOT_STRING"
    ACTION_EMPTY = "ACTION_EMPTY"
    ACTION_MULTILINE = "ACTION_MULTILINE"
    ACTION_CONTROL_CHARACTER = "ACTION_CONTROL_CHARACTER"
    ACTION_TOO_LONG = "ACTION_TOO_LONG"

@dataclass(frozen=True, slots=True)
class RawPolicyParseResult:
    status: ParserStatus
    normalized_action: str | None
    failure_stage: FailureStage | None
    failure_code: ParserFailureCode | None

def parse_raw_policy_response(
    raw_response: str,
    *,
    max_action_codepoints: int = 256,
) -> RawPolicyParseResult:
    ...
```

- [ ] **Step 1: Write failing parser tests**

Tests must cover the accepted response:

```python
result = parse_raw_policy_response(' \n{"action":"  look  "}\t')
assert result.status is ParserStatus.SUCCESS
assert result.normalized_action == "look"
```

Parameterize rejection of:

```python
[
    'Here is my action: {"action":"look"}',
    '```json\n{"action":"look"}\n```',
    '{"action":"look"}{"action":"done"}',
    '["look"]',
    'null',
    '{"action":null}',
    '{"action":123}',
    '{"action":"look","reason":"inspect"}',
    '{"other":"look"}',
    '{"action":"look","action":"done"}',
    '{"action":NaN}',
    "\ufeff{\"action\":\"look\"}",
]
```

Add dedicated assertions for:

```python
'{"action":"   "}'                 # ACTION_EMPTY
'{"action":"look\\nnow"}'          # ACTION_MULTILINE
'{"action":"look\\u0001"}'         # ACTION_CONTROL_CHARACTER
'{"action":"' + "x" * 257 + '"}'   # ACTION_TOO_LONG
```

Add tests proving no repair:

```python
assert parse_raw_policy_response(
    '{"action":"Action: look"}'
).normalized_action == "Action: look"

assert parse_raw_policy_response(
    '{"action":"LOOK"}'
).normalized_action == "LOOK"
```

- [ ] **Step 2: Run tests and verify red state**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_raw_policy_parser.py
```

Expected failure: module or interface does not yet exist.

- [ ] **Step 3: Implement the strict parser**

Use a private object wrapper so JSON objects remain distinguishable from
arrays:

```python
@dataclass(frozen=True, slots=True)
class _JsonObject:
    pairs: tuple[tuple[str, object], ...]
```

Configure `json.JSONDecoder` with:

```python
object_pairs_hook=_build_object
parse_constant=_reject_nonstandard_constant
```

`_build_object` must examine the ordered pair stream and raise a private
duplicate-member exception before converting anything to a dictionary.

Algorithm:

```text
strip only " \t\r\n" around the full response
raw_decode exactly one JSON value
reject any unconsumed suffix
require _JsonObject
require exactly one pair
require key == "action"
require value type is str
trim action with strip(" ")
reject empty
reject LF or CR
reject U+0000–U+001F and U+007F–U+009F
reject len(action) > 256
return immutable success result
```

Do not accept `bytes`; the public input type is `str`.

- [ ] **Step 4: Run parser tests and full regression**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_raw_policy_parser.py

python -m pytest \
  -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add -- \
  src/pchsi/evaluation/raw_policy_parser.py \
  tests/evaluation/test_raw_policy_parser.py

git commit \
  -m "Implement strict E1 raw policy parser"
```

---

### Task 2: Deterministic Prompt Builder and Fixed Feedback

**Files:**
- Create: `src/pchsi/evaluation/raw_policy_prompt.py`
- Create: `tests/evaluation/test_raw_policy_prompt.py`

**Interfaces:**

```python
class InterfaceFeedbackCode(str, Enum):
    FORMAT_ERROR_V1 = "FORMAT_ERROR_V1"
    INVALID_ACTION_V1 = "INVALID_ACTION_V1"

FORMAT_ERROR_V1: str
INVALID_ACTION_V1: str

@dataclass(frozen=True, slots=True)
class ExecutedTransition:
    action: str
    resulting_observation: str

def build_raw_policy_prompt(
    *,
    public_task_goal: str,
    observation: str,
    executed_transitions: Sequence[ExecutedTransition],
    admissible_commands: Sequence[str],
    interface_feedback: InterfaceFeedbackCode | None,
) -> str:
    ...
```

#### v3.3 M0 canonicalisation contract

Task 2 also produces:

```python
def canonical_executed_transitions_json(
    executed_transitions: Sequence[ExecutedTransition],
) -> str:
    ...

def sha256_executed_transitions(
    executed_transitions: Sequence[ExecutedTransition],
) -> str:
    ...
```

The functions operate on only the final eight
`ExecutedTransition` values.

Canonical JSON uses:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    allow_nan=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

The canonical payload is a JSON array containing objects with
exactly these fields:

```json
{"action":"...","resulting_observation":"..."}
```

Add a golden test:

```python
transitions = (
    ExecutedTransition(
        action="look",
        resulting_observation="You see a desk.",
    ),
)

assert canonical_executed_transitions_json(
    transitions
) == (
    '[{"action":"look",'
    '"resulting_observation":"You see a desk."}]'
)

assert sha256_executed_transitions(
    transitions
) == (
    "af30775b5c2278a829632643ee4a6752c68b2d729d84d5dcb9871e2a097637aa"
)
```

This hash is the E1 `MEMORY_M0_V1` state hash. It introduces no
retrieval or summarisation behavior.

- [ ] **Step 1: Write failing prompt tests**

Freeze this exact section order:

```text
RAW_POLICY_PROMPT_V1
TASK_GOAL_JSON=<canonical JSON string>
CURRENT_OBSERVATION_JSON=<canonical JSON string>
EXECUTED_TRANSITIONS_JSON=<canonical compact JSON array>
VISIBLE_ADMISSIBLE_COMMANDS_JSON=<canonical compact JSON array>
INTERFACE_FEEDBACK_JSON=<canonical JSON string or null>
OUTPUT_REQUIREMENT={"action":"<command>"}
```

Canonical JSON uses:

```python
ensure_ascii=False
allow_nan=False
separators=(",", ":")
```

Tests must prove:

- task goal is repeated in every prompt;
- full observation is retained;
- command order is unchanged;
- only the final eight executed transitions remain;
- inputs that are not `ExecutedTransition` instances are rejected;
- raw failed responses have no accepted transition input field;
- `None` feedback serializes to `null`;
- feedback text is byte-identical to the approved constants;
- arbitrary caller-provided feedback strings are not accepted;
- two identical inputs produce byte-identical prompts.

- [ ] **Step 2: Run tests and verify red state**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_raw_policy_prompt.py
```

- [ ] **Step 3: Implement the prompt builder**

The feedback constants must be exactly:

```text
FORMAT_ERROR_V1:
Expected exactly one JSON object with exactly one string field:
{"action":"<command>"}
No environment action was executed.
```

and:

```text
INVALID_ACTION_V1:
The parsed action is not an exact member of the visible admissible-command menu.
No environment action was executed.
```

Map the enum to constants internally. Never accept an unrestricted feedback
string.

Slice history with:

```python
history = tuple(executed_transitions)[-8:]
```

Serialize transition records as:

```json
{"action":"...","resulting_observation":"..."}
```

- [ ] **Step 4: Run prompt and full tests**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_raw_policy_prompt.py

python -m pytest \
  -q
```

- [ ] **Step 5: Commit Task 2**

```bash
git add -- \
  src/pchsi/evaluation/raw_policy_prompt.py \
  tests/evaluation/test_raw_policy_prompt.py

git commit \
  -m "Implement deterministic E1 raw policy prompt"
```

---

### Task 3: Immutable Dual-Budget State Machine

**Files:**
- Create: `src/pchsi/evaluation/budget.py`
- Create: `tests/evaluation/test_budget.py`

**Interfaces:**

```python
class BudgetAttemptOutcome(str, Enum):
    ACTION_EXECUTED = "ACTION_EXECUTED"
    FORMAT_PROTOCOL_FAILURE = "FORMAT_PROTOCOL_FAILURE"
    ACTION_NOT_ADMISSIBLE = "ACTION_NOT_ADMISSIBLE"

class EpisodeTerminationReason(str, Enum):
    ENVIRONMENT_TERMINATED = "ENVIRONMENT_TERMINATED"
    POLICY_ATTEMPT_BUDGET_EXHAUSTED = "POLICY_ATTEMPT_BUDGET_EXHAUSTED"
    ENVIRONMENT_STEP_BUDGET_EXHAUSTED = "ENVIRONMENT_STEP_BUDGET_EXHAUSTED"
    CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED = (
        "CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED"
    )
    PROTOCOL_CONFIGURATION_ERROR = "PROTOCOL_CONFIGURATION_ERROR"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"

@dataclass(frozen=True, slots=True)
class BudgetLimits:
    max_policy_attempts: int = 60
    max_environment_steps: int = 30
    max_consecutive_nonexecuted_attempts: int = 3

@dataclass(frozen=True, slots=True)
class BudgetState:
    policy_attempt_count: int = 0
    environment_step_count: int = 0
    protocol_failure_count: int = 0
    inadmissible_action_count: int = 0
    consecutive_nonexecuted_attempt_count: int = 0

def can_start_policy_attempt(
    state: BudgetState,
    limits: BudgetLimits,
) -> bool:
    ...

def apply_completed_attempt(
    state: BudgetState,
    outcome: BudgetAttemptOutcome,
    limits: BudgetLimits,
) -> BudgetState:
    ...

def resolve_nonexecuted_termination(
    state: BudgetState,
    limits: BudgetLimits,
) -> EpisodeTerminationReason | None:
    ...

def resolve_after_environment(
    state: BudgetState,
    limits: BudgetLimits,
    *,
    infrastructure_error: bool,
    environment_terminated: bool,
) -> EpisodeTerminationReason | None:
    ...
```

- [ ] **Step 1: Write failing budget tests**

Prove:

- generation 60 is allowed when count is 59;
- generation 61 is rejected when count is 60;
- environment step 30 is allowed when count is 29;
- no transition may produce environment count 31;
- format failure increments policy, protocol and consecutive counts;
- inadmissibility increments policy, inadmissibility and consecutive counts;
- executed action increments policy and environment counts and resets
  consecutive count;
- alternating format/inadmissibility failures reach three;
- third invalid attempt at policy attempt 60 resolves to consecutive
  exhaustion;
- infrastructure error precedes all other termination causes;
- environment termination precedes environment budget exhaustion;
- environment budget precedes policy-attempt exhaustion.

- [ ] **Step 2: Run tests and verify red state**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_budget.py
```

- [ ] **Step 3: Implement immutable transitions**

`apply_completed_attempt()` must reject calls when no policy attempt remains.

An `ACTION_EXECUTED` transition must also reject calls when no environment
step remains.

Every returned state must be newly constructed and must validate:

```text
all counters >= 0
policy_attempt_count <= max_policy_attempts
environment_step_count <= max_environment_steps
```

- [ ] **Step 4: Run budget and full tests**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_budget.py

python -m pytest \
  -q
```

- [ ] **Step 5: Commit Task 3**

```bash
git add -- \
  src/pchsi/evaluation/budget.py \
  tests/evaluation/test_budget.py

git commit \
  -m "Implement E1 dual budget state machine"
```

---

### Task 4: Menu Contract, Admissibility and Pure Runtime Decisions

**Files:**
- Create: `src/pchsi/evaluation/runtime_core.py`
- Create: `tests/evaluation/test_runtime_core.py`

**Interfaces:**

```python
class AttemptOutcome(str, Enum):
    ACTION_EXECUTED = "ACTION_EXECUTED"
    FORMAT_PROTOCOL_FAILURE = "FORMAT_PROTOCOL_FAILURE"
    ACTION_NOT_ADMISSIBLE = "ACTION_NOT_ADMISSIBLE"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"

class AdmissibilityStatus(str, Enum):
    NOT_CHECKED = "not_checked"
    EXACT_MEMBER = "exact_member"
    NOT_ADMISSIBLE = "not_admissible"

class AttemptFailureStage(str, Enum):
    ENVELOPE = "envelope"
    ACTION_NORMALIZATION = "action_normalization"
    ADMISSIBILITY = "admissibility"
    INFRASTRUCTURE = "infrastructure"

class MenuFailureCode(str, Enum):
    POLICY_MENU_COUNT_MISMATCH = (
        "POLICY_MENU_COUNT_MISMATCH"
    )
    POLICY_MENU_SEQUENCE_MISMATCH = (
        "POLICY_MENU_SEQUENCE_MISMATCH"
    )
    HARNESS_MENU_COUNT_MISMATCH = (
        "HARNESS_MENU_COUNT_MISMATCH"
    )
    HARNESS_MENU_SEQUENCE_MISMATCH = (
        "HARNESS_MENU_SEQUENCE_MISMATCH"
    )
    MENU_COMMAND_NOT_STRING = (
        "MENU_COMMAND_NOT_STRING"
    )
    MENU_COMMAND_EMPTY = "MENU_COMMAND_EMPTY"
    MENU_COMMAND_BOUNDARY_SPACE = (
        "MENU_COMMAND_BOUNDARY_SPACE"
    )
    MENU_COMMAND_MULTILINE = (
        "MENU_COMMAND_MULTILINE"
    )
    MENU_COMMAND_CONTROL_CHARACTER = (
        "MENU_COMMAND_CONTROL_CHARACTER"
    )
    MENU_COMMAND_TOO_LONG = (
        "MENU_COMMAND_TOO_LONG"
    )

@dataclass(frozen=True, slots=True)
class MenuValidationResult:
    valid: bool
    failure_code: MenuFailureCode | None
    sequence_sha256: str | None

@dataclass(frozen=True, slots=True)
class RuntimeDecision:
    budget_before: BudgetState
    budget_after: BudgetState
    parse_result: RawPolicyParseResult
    attempt_outcome: AttemptOutcome
    failure_stage: AttemptFailureStage | None
    failure_code: ParserFailureCode | RuntimeFailureCode | None
    normalized_action: str | None
    admissibility_status: AdmissibilityStatus
    feedback_code: InterfaceFeedbackCode | None
    should_call_env: bool
    candidate_environment_action: str | None
    termination_reason: EpisodeTerminationReason | None

def validate_menu_contract(
    *,
    policy_visible_commands: Sequence[str],
    harness_visible_commands: Sequence[str],
    environment_commands: Sequence[str],
    max_action_codepoints: int = 256,
) -> MenuValidationResult:
    ...

def process_completed_generation(
    *,
    raw_response: str,
    visible_admissible_commands: Sequence[str],
    budget_state: BudgetState,
    budget_limits: BudgetLimits = BudgetLimits(),
    max_action_codepoints: int = 256,
) -> RuntimeDecision:
    ...

def finalize_environment_result(
    decision: RuntimeDecision,
    *,
    environment_terminated: bool,
    infrastructure_error: bool,
) -> RuntimeDecision:
    ...
```

#### v3.3 protocol-precondition closure

Add the frozen runtime failure enum:

```python
class RuntimeFailureCode(str, Enum):
    ACTION_NOT_ADMISSIBLE = "ACTION_NOT_ADMISSIBLE"
    ENVIRONMENT_STEP_FAILED = "ENVIRONMENT_STEP_FAILED"
```

Add a pre-call result that closes the mapping between detailed
menu errors and public episode termination:

```python
@dataclass(frozen=True, slots=True)
class ProtocolPreconditionResult:
    menu_validation: MenuValidationResult
    budget_before: BudgetState
    budget_after: BudgetState
    should_call_policy: bool
    termination_reason: EpisodeTerminationReason | None

def validate_runtime_preconditions(
    *,
    policy_visible_commands: Sequence[str],
    harness_visible_commands: Sequence[str],
    environment_commands: Sequence[str],
    budget_state: BudgetState,
    budget_limits: BudgetLimits = BudgetLimits(),
    max_action_codepoints: int = 256,
) -> ProtocolPreconditionResult:
    ...
```

Frozen behavior:

```text
validate_menu_contract() runs before every model call.

invalid menu:
  should_call_policy = false
  termination_reason = PROTOCOL_CONFIGURATION_ERROR
  budget_after == budget_before
  no policy attempt
  no process_completed_generation()
  detailed MenuFailureCode retained

valid menu but policy budget exhausted:
  should_call_policy = false
  termination_reason = POLICY_ATTEMPT_BUDGET_EXHAUSTED
  budget_after == budget_before

valid and budget available:
  should_call_policy = true
  termination_reason = null
```

`process_completed_generation()` must accept:

```python
precondition_result: ProtocolPreconditionResult
```

and reject a call unless:

```python
precondition_result.should_call_policy is True
```

Tests must prove:

- invalid menus consume no counter;
- invalid menus cannot enter generation processing;
- detailed `MenuFailureCode` is retained;
- the public termination is exactly
  `PROTOCOL_CONFIGURATION_ERROR`;
- valid preconditions preserve the exact menu sequence hash.

For an off-list parsed action:

```text
failure_stage = ADMISSIBILITY
failure_code = RuntimeFailureCode.ACTION_NOT_ADMISSIBLE
```

For an environment-call failure after a valid runtime decision:

```text
failure_stage = INFRASTRUCTURE
failure_code = RuntimeFailureCode.ENVIRONMENT_STEP_FAILED
```

A valid action reserves one environment step before the evaluator
calls `env.step()`. If `env.step()` raises an infrastructure error,
the reserved environment-step count remains consumed and the episode
is invalidated. It is not converted into a policy failure or retried
for free.

- [ ] **Step 1: Write failing runtime-core tests**

Menu tests must reject:

- policy/environment string mismatch;
- Harness/environment mismatch;
- ordering mismatch;
- leading or trailing U+0020;
- LF, CR, C0 and C1 controls;
- empty command;
- command longer than 256 code points;
- non-string command.

Confirm invalid menu validation does not modify any `BudgetState`.

Runtime tests must prove:

- parser failure produces `FORMAT_PROTOCOL_FAILURE`;
- parser failure carries the exact envelope or normalization
  failure stage and code;
- parser failure has `NOT_CHECKED` admissibility;
- off-list valid JSON produces `ACTION_NOT_ADMISSIBLE`;
- off-list failure carries the `ADMISSIBILITY` stage and
  `ACTION_NOT_ADMISSIBLE` failure code;
- off-list action has successful parser status and no parser error;
- case-only mismatch remains inadmissible;
- exact member sets `should_call_env=True`;
- valid action is returned unchanged;
- no sorting or nearest-action lookup occurs;
- third mixed nonexecuted attempt terminates;
- valid execution clears the consecutive counter;
- fixed feedback codes are selected correctly;
- `finalize_environment_result()` applies the approved precedence.

- [ ] **Step 2: Run tests and verify red state**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_runtime_core.py
```

- [ ] **Step 3: Implement menu validation**

Hash command sequences with the existing:

```python
sha256_string_sequence()
```

from `action_trace.py`.

Compare tuples directly. Do not use sets or sorted copies.

Return an internal failure code while the public outcome remains
`PROTOCOL_CONFIGURATION_ERROR`.

- [ ] **Step 4: Implement runtime decision flow**

Fixed order:

```text
require available policy attempt
parse Stage 1–2
apply format-failure budget transition if parsing fails
otherwise perform exact Stage-3 membership
apply inadmissibility budget transition if absent
otherwise reserve one environment step
return immutable decision
```

For a valid action, do not finalize episode termination until
`finalize_environment_result()` receives the environment result.

- [ ] **Step 5: Run runtime and full tests**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_runtime_core.py

python -m pytest \
  -q
```

- [ ] **Step 6: Commit Task 4**

```bash
git add -- \
  src/pchsi/evaluation/runtime_core.py \
  tests/evaluation/test_runtime_core.py

git commit \
  -m "Implement pure E1 runtime decisions"
```

---

### Task 5: Extend Immutable ActionTrace Compatibly

**Files:**
- Modify: `src/pchsi/evaluation/action_trace.py`
- Modify: `tests/evaluation/test_action_trace.py`
- Test: `tests/evaluation/test_runtime_core.py`

**Interfaces:**

Append optional fields to `ActionTrace`:

```python
attempt_outcome: str | None = None
failure_stage: str | None = None
failure_code: str | None = None
normalized_action: str | None = None
admissibility_status: str | None = None
feedback_code: str | None = None
policy_attempt_count_before: int | None = None
policy_attempt_count_after: int | None = None
environment_step_count_before: int | None = None
environment_step_count_after: int | None = None
protocol_failure_count: int | None = None
inadmissible_action_count: int | None = None
consecutive_nonexecuted_attempt_count: int | None = None
episode_termination_reason: str | None = None
```

#### v3.3 trace and provenance compatibility

Append optional fields to `TraceProvenance`:

```python
split_and_access_version: str | None = None
split_name: str | None = None
access_mode: str | None = None
policy_version: str | None = None
seed: int | None = None
memory_version: str | None = None
memory_state_sha256: str | None = None
```

E1-Dev and E1-Confirmatory share Runtime Core but use distinct
values for `split_name`, `access_mode` and manifests.

For the E1 baseline:

```text
policy_version = pi0
memory_version = MEMORY_M0_V1
```

`memory_state_sha256` is generated only by
`sha256_executed_transitions()` from Task 2.

Append optional environment-result fields to `ActionTrace`:

```python
submitted_environment_action: str | None = None
resulting_observation: str | None = None
resulting_observation_sha256: str | None = None
environment_event_flags: FrozenJsonObject = EMPTY_METADATA
```

Extend `ExecutionStatus` with:

```python
ENVIRONMENT_ERROR = "environment_error"
```

Frozen infrastructure-error semantics:

```text
attempt_outcome = INFRASTRUCTURE_ERROR
failure_stage = infrastructure
failure_code = ENVIRONMENT_STEP_FAILED
execution_status = environment_error
should_call_env was true
environment_step_index is present
submitted_environment_action is present
final_executed_action is null
resulting_observation is null
environment_step_count_after =
    environment_step_count_before + 1
episode_termination_reason = INFRASTRUCTURE_ERROR
```

Add explicit tests for:

- old `TraceProvenance` construction without new fields;
- old `ActionTrace` construction without new fields;
- E1-Dev provenance;
- E1-Confirmatory provenance;
- the M0 golden hash;
- invalid 64-character SHA-256 metadata;
- environment infrastructure failure;
- no fabricated resulting observation after infrastructure failure;
- deterministic JSON serialization with all v3.3 fields.

- [ ] **Step 1: Write failing trace tests**

Test:

- all old trace constructors still work unchanged;
- format failure stores Stage 1/2 code and no environment-step index;
- admissibility failure has parser success and `parser_error is None`;
- executed action stores exact before/after counters;
- supplied counters cannot decrease;
- environment count increases by zero or one only;
- policy count increases by exactly one for completed generations;
- deterministic `to_json()` includes the new fields.

- [ ] **Step 2: Run trace tests and verify red state**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_action_trace.py
```

- [ ] **Step 3: Extend ActionTrace**

Add all new dataclass fields after existing required fields so they can
retain defaults.

Update `build()` with optional keyword parameters and update `to_dict()`.

Apply coherence validation only when new runtime-core fields are supplied,
preserving readability of frozen historical traces.

- [ ] **Step 4: Run trace, runtime and full tests**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_action_trace.py \
  tests/evaluation/test_runtime_core.py

python -m pytest \
  -q
```

- [ ] **Step 5: Commit Task 5**

```bash
git add -- \
  src/pchsi/evaluation/action_trace.py \
  tests/evaluation/test_action_trace.py \
  tests/evaluation/test_runtime_core.py

git commit \
  -m "Extend action trace for E1 runtime attribution"
```

---

### Task 6: Test-Only Fake Environment End-to-End Integration

**Files:**
- Create:
  `tests/evaluation/test_runtime_core_fake_environment.py`

**Scope:**

This task creates no production evaluator or environment adapter.
The fake environment exists inside the test file only.

**Test-only interface:**

```python
@dataclass
class FakeEnvironment:
    observation: str
    admissible_commands: tuple[str, ...]
    transitions: list[ExecutedTransition]
    fail_next_step: bool = False

    def step(
        self,
        action: str,
    ) -> tuple[str, dict[str, bool]]:
        if self.fail_next_step:
            raise RuntimeError(
                "synthetic environment failure"
            )

        if action not in self.admissible_commands:
            raise AssertionError(
                "runtime called fake env with off-list action"
            )

        next_observation = (
            f"Executed: {action}"
        )

        return (
            next_observation,
            {"state_changed": True},
        )
```

- [ ] **Step 1: Write the end-to-end test driver**

The test performs exactly this sequence:

```text
initial observation and complete ordered menu
→ validate three-party menu contract
→ build prompt with MEMORY_M0_V1
→ malformed policy response
→ FORMAT_PROTOCOL_FAILURE
→ build same-state prompt with FORMAT_ERROR_V1
→ valid JSON containing an off-list action
→ ACTION_NOT_ADMISSIBLE
→ build same-state prompt with INVALID_ACTION_V1
→ valid exact menu member
→ runtime returns should_call_env=true
→ test driver alone calls fake_env.step()
→ append executed transition to M0
→ clear interface feedback
→ complete immutable trace
```

Required assertions after the first response:

```python
assert decision.attempt_outcome is (
    AttemptOutcome.FORMAT_PROTOCOL_FAILURE
)
assert decision.budget_after.policy_attempt_count == 1
assert decision.budget_after.environment_step_count == 0
assert history == ()
```

Required assertions after the second response:

```python
assert decision.attempt_outcome is (
    AttemptOutcome.ACTION_NOT_ADMISSIBLE
)
assert decision.parse_result.status is ParserStatus.SUCCESS
assert decision.parse_result.failure_code is None
assert decision.budget_after.policy_attempt_count == 2
assert decision.budget_after.environment_step_count == 0
assert history == ()
```

Required assertions after the third response:

```python
assert decision.attempt_outcome is (
    AttemptOutcome.ACTION_EXECUTED
)
assert decision.should_call_env is True
assert decision.candidate_environment_action == (
    visible_commands[0]
)
assert decision.budget_after.policy_attempt_count == 3
assert decision.budget_after.environment_step_count == 1
assert (
    decision.budget_after
    .consecutive_nonexecuted_attempt_count
    == 0
)
```

The test driver then calls `fake_env.step()` and appends exactly one
`ExecutedTransition`.

It must prove:

- menu order remains byte-identical;
- observation is unchanged during the two nonexecuted attempts;
- no failed raw response enters M0;
- only the successful environment transition enters M0;
- feedback clears after successful execution;
- M0 hash changes only after the executed transition;
- three immutable attempt traces are serializable.

- [ ] **Step 2: Add infrastructure-error integration test**

Set:

```python
fake_env.fail_next_step = True
```

Process a valid exact action and confirm:

```python
assert decision.should_call_env is True
assert decision.budget_after.environment_step_count == (
    decision.budget_before.environment_step_count + 1
)
```

After `fake_env.step()` raises, finalize the result and assert:

```python
assert finalized.attempt_outcome is (
    AttemptOutcome.INFRASTRUCTURE_ERROR
)
assert finalized.failure_stage is (
    AttemptFailureStage.INFRASTRUCTURE
)
assert finalized.failure_code is (
    RuntimeFailureCode.ENVIRONMENT_STEP_FAILED
)
assert finalized.termination_reason is (
    EpisodeTerminationReason.INFRASTRUCTURE_ERROR
)
```

No transition enters M0, no resulting observation is fabricated and
no free retry occurs.

- [ ] **Step 3: Run the fake-environment tests**

```bash
python -m pytest \
  -q \
  tests/evaluation/test_runtime_core_fake_environment.py
```

- [ ] **Step 4: Run the complete regression suite**

```bash
python -m pytest \
  -q
```

- [ ] **Step 5: Commit Task 6**

```bash
git add -- \
  tests/evaluation/test_runtime_core_fake_environment.py

git commit \
  -m "Add fake-environment E1 runtime integration tests"
```

---

### Task 7: Final Verification and Documentation Seal

**Files:**
- Modify: `docs/code_map.md`
- Modify: `docs/experiments/EXPERIMENT_LEDGER.md`
- Modify: `configs/protocols/raw_with_menu_v1.json`

#### v3.3 metadata and governance seal

Task 7 must record these distinct statuses:

```text
runtime_core_implemented_pending_code_approval
runtime_core_code_approved_execution_not_approved
split_and_access_v1_frozen_pending_execution_approval
e1_dev_execution_approved
```

A generic `approved` status is prohibited.

`docs/code_map.md` must identify as explicitly out of scope:

```text
ALFWorld evaluator
vLLM or model clients
closed-source distillation
SFT and RL
Memory beyond MEMORY_M0_V1
Research Planner
automatic policy-promotion gate
E1-Dev or E1-Confirmatory results
```

`docs/experiments/EXPERIMENT_LEDGER.md` must state:

```text
Runtime Core implemented and unit/fake-environment tested;
CODE_APPROVED pending;
execution not approved;
SPLIT_AND_ACCESS_V1 not yet frozen.
```

The implementation PR must contain no all134 manifest execution,
no rollout output and no closed-source request/output artifact.

- [ ] **Step 1: Update code and experiment status**

Record the four runtime modules and four new test modules in
`docs/code_map.md`.

Change E1 ledger status to:

```text
Runtime core implemented and unit-tested; evaluator and execution pending.
```

Change machine protocol status to:

```text
runtime_core_implemented_pending_code_approval
```

Do not mark E1 as executed.

- [ ] **Step 2: Run full verification**

```bash
python -m pytest \
  -q

python -m compileall \
  -q \
  src \
  tests

python -m json.tool \
  configs/protocols/raw_with_menu_v1.json \
  > /dev/null

git diff \
  --check
```

- [ ] **Step 3: Verify forbidden imports are absent**

```bash
if grep -RInE \
  '(^|[[:space:]])(import|from)[[:space:]]+(alfworld|vllm|openai|torch)' \
  src/pchsi/evaluation/raw_policy_parser.py \
  src/pchsi/evaluation/raw_policy_prompt.py \
  src/pchsi/evaluation/budget.py \
  src/pchsi/evaluation/runtime_core.py
then
  echo "ERROR: forbidden runtime dependency"
  exit 1
fi
```

- [ ] **Step 4: Verify scope**

Expected implementation files:

```text
src/pchsi/evaluation/raw_policy_parser.py
src/pchsi/evaluation/raw_policy_prompt.py
src/pchsi/evaluation/budget.py
src/pchsi/evaluation/runtime_core.py
tests/evaluation/test_raw_policy_parser.py
tests/evaluation/test_raw_policy_prompt.py
tests/evaluation/test_budget.py
tests/evaluation/test_runtime_core.py
```

Prohibit:

```text
scripts/evaluate_raw_with_menu_v1.py
ALFWorld rollout output
vLLM startup scripts
model weights
experimental results
```

- [ ] **Step 5: Commit documentation seal**

```bash
git add -- \
  configs/protocols/raw_with_menu_v1.json \
  docs/code_map.md \
  docs/experiments/EXPERIMENT_LEDGER.md

git commit \
  -m "Seal E1 runtime core implementation metadata"
```

- [ ] **Step 6: Final branch audit**

```bash
git status \
  --short

git log \
  --oneline \
  --decorate \
  origin/main..HEAD

git diff \
  --stat \
  origin/main...HEAD

git diff \
  --check \
  origin/main...HEAD
```

Expected:

- clean worktree;
- seven focused commits: five source/test commits, one test-only fake-environment integration commit and one metadata-seal commit;
- no evaluator, model execution or result artifacts;
- all tests passing.

## Execution Handoff

Completion of this plan permits only the following sequence:

```text
Runtime Core TDD implementation
→ unit tests
→ fake-environment end-to-end tests
→ static and semantic code audit
→ CODE_APPROVED_E1_RUNTIME_CORE_V1
→ freeze SPLIT_AND_ACCESS_V1
→ separate evaluator design and code review
→ separate execution-readiness audit
→ EXECUTION_APPROVED_E1_DEV
→ E1-Dev rollout
→ P1 taxonomy and E3a verifier
→ closed-source distillation in a separate scope
→ π1 Harness-OFF SELECT acceptance
→ separately governed E1-Confirmatory execution
```

The following implication is explicitly false:

```text
CODE_APPROVED
⇒ EXECUTION_APPROVED
```

Runtime Core completion must not trigger:

- all134 execution;
- valid-unseen detailed badcase inspection;
- closed-source model calls;
- model training;
- Research Planner execution;
- automatic candidate-policy promotion.

E1-Dev permits development-visible trajectory analysis under its
frozen access manifest.

E1-Confirmatory uses a separately sealed manifest and cannot be
used for prompt, verifier, threshold, data or training decisions.

The current memory condition remains:

```text
MEMORY_M0_V1
= final eight executed environment transitions
```

Any M1/M2/M3 memory mechanism requires a separate M-Study,
specification and approval process.

After this amended plan is approved, implementation must proceed
task-by-task with a review checkpoint after every commit.

No model, ALFWorld or GPU execution is authorised by plan approval.
