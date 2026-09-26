# E1 Runtime Core V1 Design

## Status

Approved design:

```text
DESIGN_APPROVED_E1_RUNTIME_CORE_V1_60_30_3_256
```

This specification defines the pure runtime core for E1
`RAW_WITH_MENU_V1`.

It does not implement:

- ALFWorld environment construction;
- vLLM serving;
- HTTP model calls;
- GPU execution;
- E1 rollout;
- Phase-Critical Harness logic;
- result aggregation.

## Scientific objective

The runtime core must preserve three distinct capabilities:

1. following the required JSON action interface;
2. selecting an exact action from the visible legal-action menu;
3. producing a valid environment transition.

These must not be collapsed into one `parser_error` category.

## Pure component architecture

Planned implementation modules:

```text
src/pchsi/evaluation/raw_policy_parser.py
src/pchsi/evaluation/raw_policy_prompt.py
src/pchsi/evaluation/budget.py
src/pchsi/evaluation/runtime_core.py
```

Planned tests:

```text
tests/evaluation/test_raw_policy_parser.py
tests/evaluation/test_raw_policy_prompt.py
tests/evaluation/test_budget.py
tests/evaluation/test_runtime_core.py
tests/evaluation/test_action_trace.py
```

These modules must not import ALFWorld, vLLM, OpenAI clients,
PyTorch or any project-specific controller.

## Stage 0: evaluator preconditions

Before a policy call, the evaluator must establish:

```text
policy_visible_admissible_commands
=
harness_visible_admissible_commands
=
environment_admissible_commands
```

Equality includes:

- identical strings;
- identical ordering;
- identical count;
- identical canonical sequence SHA-256.

Sorting, filtering, deduplication and truncation are prohibited.

Every environment-provided command must also satisfy:

- Python type is `str`;
- length is between 1 and 256 Unicode code points;
- no leading or trailing U+0020;
- no U+000A or U+000D;
- no C0 or C1 control character.

A violation is:

```text
PROTOCOL_CONFIGURATION_ERROR
```

It occurs before the model call, consumes no policy attempt,
invalidates the episode for scientific analysis and cannot be attributed
to the policy.

Full-menu context overflow is also a protocol-configuration failure.
Silent menu truncation is forbidden.

## Stage 1: envelope parsing

Input is the complete raw model response.

Surrounding JSON transport whitespace is allowed only from:

```text
U+0020 SPACE
U+0009 TAB
U+000A LINE FEED
U+000D CARRIAGE RETURN
```

After accounting for transport whitespace, the response must contain
exactly one complete JSON document.

The top-level JSON value must:

- be an object;
- contain exactly one member;
- contain no duplicate member;
- use the member name `action`;
- contain a string-valued `action`.

Examples rejected at Stage 1:

```text
Here is my action: {"action":"look"}

```json
{"action":"look"}
```

{"action":"look"}{"action":"done"}
["look"]
{"action":null}
{"action":123}
{"action":"look","reason":"inspect"}
{"action":"look","action":"done"}
```

Python's ordinary last-member-wins handling is prohibited.
Duplicate members must be detected from the ordered member-pair stream.

Non-standard JSON constants such as `NaN` and `Infinity` are rejected.

Stage-1 failure codes:

```text
ENVELOPE_INVALID_JSON
ENVELOPE_TRAILING_DATA
ENVELOPE_TOP_LEVEL_NOT_OBJECT
ENVELOPE_DUPLICATE_MEMBER
ENVELOPE_MEMBER_COUNT_INVALID
ENVELOPE_MEMBER_NAME_INVALID
ENVELOPE_ACTION_NOT_STRING
```

Every Stage-1 failure maps to the public attempt outcome:

```text
FORMAT_PROTOCOL_FAILURE
```

## Stage 2: action normalization

Stage 2 does not receive or inspect the admissible-action list.

The only permitted normalization is:

```text
action.strip(" ")
```

This removes U+0020 from the beginning and end only.

It must not:

- lowercase or casefold;
- correct spelling;
- perform fuzzy matching;
- select a nearest command;
- extract one line from multiline output;
- remove an `Action:` prefix;
- canonicalise verbs or templates;
- repair an object or receptacle name.

Validation order is fixed:

1. reject an empty value after trimming;
2. reject U+000A or U+000D;
3. reject any C0 or C1 control character;
4. reject length greater than 256 Unicode code points.

Stage-2 failure codes:

```text
ACTION_EMPTY
ACTION_MULTILINE
ACTION_CONTROL_CHARACTER
ACTION_TOO_LONG
```

Every Stage-2 failure maps to:

```text
FORMAT_PROTOCOL_FAILURE
```

## Stage 3: exact admissibility validation

Stage 3 receives the normalized action and the complete visible menu.

The sole acceptance rule is equivalent to:

```python
normalized_action in policy_visible_admissible_commands
```

Matching is:

- exact;
- case-sensitive;
- order-preserving with respect to menu storage;
- free from canonicalisation and repair.

A Stage-3 failure is:

```text
ACTION_NOT_ADMISSIBLE
```

It is not a parser failure.

For an inadmissible action:

- `parser_status` remains successful;
- `parser_error` is `null`;
- `env.step()` is not called;
- no environment step is consumed;
- one policy attempt is consumed.

Casefold admissibility may be retained as offline audit metadata only.
It must never control online execution, feedback or retry decisions.

## Fixed model-visible feedback

Stage-1 or Stage-2 failure exposes exactly:

```text
FORMAT_ERROR_V1:
Expected exactly one JSON object with exactly one string field:
{"action":"<command>"}
No environment action was executed.
```

Stage-3 failure exposes exactly:

```text
INVALID_ACTION_V1:
The parsed action is not an exact member of the visible admissible-command menu.
No environment action was executed.
```

The model-visible feedback must not contain:

- the internal failure code;
- a recommended action;
- a nearest action;
- phase information;
- controller reasoning;
- a corrected JSON response;
- an object or receptacle correction.

The feedback is part of the declared runtime interface and must be
identical in R0, R2, F0 and F1.

## Prompt and history behavior

Every policy attempt receives:

- the public task goal;
- the complete current observation;
- the latest eight executed environment transitions;
- the complete admissible-action list in environment order;
- either no feedback or one fixed interface-feedback block.

A failed raw response is not inserted into executed-transition history.

Executed history records only:

```text
action sent to env
→ resulting observation
```

After a successful environment action:

- interface feedback is cleared;
- the executed transition is appended;
- the eight-transition window is applied.

## Dual-budget state

Frozen limits:

```text
max_policy_attempts = 60
max_environment_steps = 30
max_consecutive_nonexecuted_attempts = 3
max_action_codepoints = 256
```

Runtime counters:

```text
policy_attempt_count
environment_step_count
protocol_failure_count
inadmissible_action_count
consecutive_nonexecuted_attempt_count
```

A completed model generation increments:

```text
policy_attempt_count += 1
```

A Stage-1 or Stage-2 failure performs:

```text
protocol_failure_count += 1
consecutive_nonexecuted_attempt_count += 1
environment_step_count unchanged
no env.step()
```

A Stage-3 failure performs:

```text
inadmissible_action_count += 1
consecutive_nonexecuted_attempt_count += 1
environment_step_count unchanged
no env.step()
```

A valid action performs:

```text
consecutive_nonexecuted_attempt_count = 0
environment_step_count += 1
env.step(normalized_action)
```

Policy attempt 60 is permitted when the pre-call count is 59.

Environment step 30 is permitted when the pre-step count is 29.

## Attempt outcomes

Frozen attempt-level outcomes:

```text
ACTION_EXECUTED
FORMAT_PROTOCOL_FAILURE
ACTION_NOT_ADMISSIBLE
INFRASTRUCTURE_ERROR
```

Frozen episode-level termination reasons:

```text
ENVIRONMENT_TERMINATED
POLICY_ATTEMPT_BUDGET_EXHAUSTED
ENVIRONMENT_STEP_BUDGET_EXHAUSTED
CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
PROTOCOL_CONFIGURATION_ERROR
INFRASTRUCTURE_ERROR
```

Provider or environment infrastructure failure invalidates the episode.
The runtime core must not silently retry it as a policy failure.

## Termination precedence

After an attempt, terminal causes are resolved in this order:

1. infrastructure error;
2. environment termination or success;
3. environment-step budget exhausted after an executed action;
4. three consecutive nonexecuted attempts;
5. policy-attempt budget exhausted.

Therefore, if policy attempt 60 is also the third consecutive invalid
attempt, the recorded terminal reason is:

```text
CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
```

while all exhausted counters remain present in the audit record.

## Trace extension

Every completed model generation produces one immutable attempt trace.

`ActionTrace` will be extended with:

```text
attempt_outcome
failure_stage
failure_code
normalized_action
admissibility_status
feedback_code
policy_attempt_count_before
policy_attempt_count_after
environment_step_count_before
environment_step_count_after
consecutive_nonexecuted_attempt_count
```

Stage-1 and Stage-2 failure:

```text
parser_status = failed
parser_error = internal failure code
attempt_outcome = FORMAT_PROTOCOL_FAILURE
```

Stage-3 failure:

```text
parser_status = success
parser_error = null
attempt_outcome = ACTION_NOT_ADMISSIBLE
```

Executed action:

```text
parser_status = success
parser_error = null
attempt_outcome = ACTION_EXECUTED
```

Budget exhaustion detected before a new model call is stored in the
episode runtime summary rather than fabricating a model-attempt trace.

New trace fields must be added compatibly so frozen historical trace
construction remains readable and existing ActionTrace tests remain valid.

## Pure runtime-core output

For each completed generation, runtime-core returns a deterministic
immutable decision containing:

```text
updated budget state
attempt outcome
parser result
normalized action or null
exact admissibility result
fixed feedback code or null
should_call_env
candidate environment action or null
terminal reason or null
trace metadata
```

Runtime-core itself never calls `env.step()`.

The later evaluator is responsible for:

1. calling runtime-core;
2. calling `env.step()` only when `should_call_env` is true;
3. supplying the resulting observation;
4. completing and persisting the trace.

## Test contract

### Parser tests

Tests must prove acceptance of:

- the exact one-member object;
- permitted surrounding JSON whitespace;
- U+0020 trimming around the action.

Tests must prove rejection of:

- prose before or after JSON;
- Markdown fences;
- concatenated JSON documents;
- array, scalar or null top-level values;
- missing, additional or incorrectly named members;
- duplicate `action` members;
- non-string actions;
- empty actions;
- multiline actions;
- C0 and C1 controls;
- actions longer than 256 code points.

Tests must demonstrate that no lowercase, casefold, prefix removal,
spelling repair or fuzzy matching occurs.

### Admissibility tests

Tests must prove:

- exact menu member passes;
- case-only mismatch fails;
- whitespace-normalized exact member passes;
- off-list action returns `ACTION_NOT_ADMISSIBLE`;
- off-list action does not become `parser_error`;
- the visible menu is not sorted, filtered or truncated.

### Evaluator-precondition tests

Tests must reject:

- policy/environment menu mismatch;
- Harness/environment menu mismatch;
- ordering mismatch;
- command longer than 256 code points;
- command containing a control character;
- command containing leading or trailing U+0020.

Precondition failure must occur before any policy attempt.

### Budget tests

Tests must prove:

- every completed generation consumes one policy attempt;
- format failure consumes no environment step;
- inadmissible action consumes no environment step;
- executed action consumes one environment step;
- an executed action resets the consecutive counter;
- alternating format and admissibility failures still reach three;
- policy attempt 60 is allowed;
- environment step 30 is allowed;
- no attempt 61 is allowed;
- no environment step 31 is allowed;
- simultaneous third invalid attempt and attempt 60 uses the frozen
  termination precedence.

### Feedback and prompt tests

Tests must prove:

- feedback strings match byte-for-byte constants;
- internal failure codes are not exposed to the model;
- failed raw responses do not enter executed history;
- successful execution clears feedback;
- only the latest eight executed transitions are retained;
- the complete menu remains in environment order.

### Trace tests

Tests must prove:

- format and schema failure retain detailed parser attribution;
- admissibility failure is independent of parser failure;
- counter values before and after the attempt are correct;
- nonexecuted attempts have no environment-step index;
- executed attempts have exactly one environment-step index;
- serialization remains deterministic;
- historical trace construction remains compatible.

## Approval gates

This specification authorises design documentation only.

Required next gates:

```text
SPEC_APPROVED_E1_RUNTIME_CORE_V1_60_30_3_256
→ implementation plan
→ TDD implementation
→ CODE_APPROVED_E1_RUNTIME_CORE_V1
```

No model or ALFWorld execution is authorised by this document.
