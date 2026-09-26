# RAW_WITH_MENU_V1

## Purpose

`RAW_WITH_MENU_V1` is the controller-free execution protocol used by
R0, R2, matched F0/F1 continuation and Harness-removal evaluation.

## Frozen E1 policy model

```text
model = Qwen/Qwen2.5-3B-Instruct
revision = aa8e72537993ba99e69dfaafa59ed015b17504d1
project-specific adapter = none
ALFWorld-specific fine-tuning = false
```

The historical V3PlannerPhase LoRA is prohibited in E1.

## Policy input

Every attempt receives:

1. the public task goal;
2. the complete current observation;
3. the most recent eight executed environment transitions;
4. the complete admissible-action list in environment order;
5. either no interface feedback or one frozen feedback message.

Failed model responses are not inserted into executed-transition history.

## Complete-menu invariant

```text
policy_visible_admissible_commands
=
harness_visible_admissible_commands
=
environment_admissible_commands
```

Equality includes exact strings, order, count and sequence SHA-256.

Sorting, filtering, deduplication and truncation are prohibited.

Context overflow caused by the complete menu is a protocol-configuration
failure, not permission to truncate the menu.

## Stage 1: envelope parsing

The complete response must be one JSON document whose top-level value is
an object containing exactly one non-duplicate member:

```json
{"action":"<command>"}
```

Prose, Markdown fences, concatenated JSON, additional members, duplicate
members and non-string action values are rejected.

## Stage 2: action normalization

The only permitted operation is:

```text
action.strip(" ")
```

The result must be nonempty, at most 256 Unicode code points, contain no
carriage return or line feed and contain no C0/C1 control character.

No case repair, spelling repair, fuzzy matching, prefix removal,
canonicalisation or object/receptacle correction is permitted.

## Stage 3: admissibility validation

The normalized action must be an exact, case-sensitive member of the
complete visible admissible-command list.

An off-list action is:

```text
ACTION_NOT_ADMISSIBLE
```

It is not a parser failure, does not call `env.step()` and does not
consume an environment step.

## Fixed interface feedback

Format/schema failure exposes only `FORMAT_ERROR_V1`.

Exact-membership failure exposes only `INVALID_ACTION_V1`.

Internal failure codes, recommended actions, nearest actions, phase
information and controller reasoning are never shown to the policy.

The existence and content of these feedback messages are part of the
declared runtime interface and must be identical across R0, R2, F0 and F1.

## Dual budget

```text
max_policy_attempts = 60
max_environment_steps = 30
max_consecutive_nonexecuted_attempts = 3
max_action_codepoints = 256
```

Every completed model generation consumes one policy attempt.

Format/schema failure and action inadmissibility consume no environment
step and do not call `env.step()`.

A valid action consumes one environment step and resets the consecutive
nonexecuted-attempt counter.

The 60th policy attempt and 30th environment step are permitted.
Attempt 61 and environment step 31 are prohibited.

## Trace and attribution

Stage-1 and Stage-2 failures are recorded as:

```text
FORMAT_PROTOCOL_FAILURE
```

Stage-3 failures are recorded as:

```text
ACTION_NOT_ADMISSIBLE
```

Successful environment actions are recorded as:

```text
ACTION_EXECUTED
```

Parser status and parser error remain independent from admissibility status.

Each model attempt records budget counts before and after the attempt,
normalized action, failure stage/code, feedback code and terminal status.

## Infrastructure failures

Provider, runtime or environment infrastructure failure invalidates the
episode for scientific analysis. It cannot be silently converted into a
policy failure or retried for free.

## Approval status

```text
DESIGN_APPROVED_E1_RUNTIME_CORE_V1_60_30_3_256
```

Runtime-core implementation, evaluator execution and E1 rollout remain
separately gated.
