# MECHANICAL_EVIDENCE_PROTOCOL_V1

## Authority

The extractor emits deterministic facts and explicit UNKNOWN values. It never
emits a failure mechanism, causal claim or repair recommendation.

## Layer A — generic episode facts

```text
policy_call_count
executed_environment_step_count
protocol_failure_count
inadmissible_action_count
nonexecuted_attempt_count
environment_error_count
exact_action_repeat_count
consecutive_exact_action_repeat_count
max_consecutive_exact_action_repeat_run
abab_action_oscillation_count
observation_unchanged_count
menu_unchanged_count
nothing_happens_count
no_effect_transition_count
budget_exhaustion
time_to_first_public_state_change
time_since_last_public_state_change
terminal_done
terminal_won
terminal_success
```

Definitions use exact strings and public evidence only. `Nothing happens.` is
an exact registered environment phrase, not a semantic similarity judgment.

## Layer B — ALFWorld registered event facts

These events require deterministic versioned rules and must be independently
tested:

```text
destination_revisit_count
source_revisit_count
source_family_revisit_count
inventory_change_events
goal_object_visible_events
goal_take_available_events
goal_object_acquired_events
required_treatment_completed_events
placement_completed_events
time_to_first_registered_progress
time_since_last_registered_progress
remaining_environment_budget
```

When parsing is unsupported or ambiguous, emit `UNKNOWN`; never let an LLM fill
the field.

`destination`, `source` and `source_family` use one frozen parser/ontology
version. Free-form model reason text is not an input.

## Layer C — paired facts

`first_behavioral_divergence` is not an episode-level field. It belongs to
`MECHANICAL_PAIRED_EVIDENCE_V1` and is computed only over registered comparable
pairs:

```text
shared_prefix_policy_call_count
shared_prefix_environment_step_count
first_action_divergence
first_executed_action_divergence
first_observation_divergence
first_menu_divergence
first_budget_divergence
pair_alignment_status
```

For F0/F1, the registered repair is the permitted intervention difference. A
difference before the registered intervention is a hard invalidation.

## Prohibited outputs

```text
model_confused
progress_blindness
critical_step
root_cause
repair_quality
Benefit
Harm
Neutral
Uncertain
```

Those belong to Analyzer hypotheses or the environment-verification authority.
