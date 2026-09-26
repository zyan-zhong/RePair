# ANALYZER_V2_PAPER_EVIDENCE_CONTRACT_V1

## 1. Purpose

Freeze the paper-level tables, denominators, figures and claim boundaries before
formal Analyzer and F0/F1 outcomes are visible.

All reported numbers must be generated from content-addressed JSON/JSONL
artifacts and fixed analysis scripts. No manual transcription into tables.

## 2. Step-level trajectory table

Required columns:

```text
run_id
condition_id
task_id
gamefile_sha256
episode_id
seed

policy_identity_sha256
model_identity
code_head
config_sha256
prompt_sha256

model_call_index
observation_before
menu_sha256
executed_history_sha256
memory_exposure
memory_packet_sha256

raw_response_sha256
parsed_action
executed_action
admissibility
execution_status

environment_feedback_sha256
observation_after
state_changed
progress_events
budget_before
budget_after
done
success

input_tokens
output_tokens
latency_ms
cost
```

## 3. Mechanical evidence table

```text
episode_id
repeat_count
consecutive_repeat_count
max_repeat_run
ABAB_oscillation_count
destination_revisit_count
source_revisit_count
source_family_revisit_count
observation_unchanged_count
nothing_happens_count
no_effect_transition_count
progress_event_count
time_to_first_progress
time_since_last_progress
budget_exhaustion
```

## 4. Analyzer result table

```text
condition_id
analyzer_run_id
episode/group_id
failure_onset
critical_window
hypothesis_count
evidence_ref_count
counterevidence_ref_count
unsupported_fact_count
historical_experience_count
candidate_status
repair_kind
candidate_rank
confidence
uncertainty
abstained
input_tokens
output_tokens
latency
cost
```

## 5. Researcher decision ledger

```text
round_id
evidence_cutoff
candidate_bottlenecks
selected_bottleneck
rejected_candidates
deferred_candidates
selection_rationale
hypothesis
single_primary_change
selected_candidate_ids
verification_budget
stop_rule
result
lesson
next_decision
```

## 6. F0/F1 ledger

```text
source_state_id
candidate_repair_id
condition_id
paired_seed
pair_integrity
first_divergence
F0_success
F1_success
F0_steps
F1_steps
repair_cost
progress_vector
effect_label
infrastructure_status
```

## 7. Training ledger

```text
training_sample_id
candidate_repair_id
source_policy_identity
F0F1_label
chosen_or_rejected
dedup_group
training_arm
token_count
training_run_id
candidate_policy_identity
```

## 8. Final evaluation table

```text
policy
training_arm
Memory_ON_OFF
Harness_ON_OFF
task_id
task_family
success
steps
policy_calls
tokens
latency
failure_type
regression_from_prior_success
```

## 9. Cost ledger

```text
Analyzer API input/output tokens
Analyzer API cost
Researcher API shadow cost
environment branches
GPU hours
training walltime
human annotation decisions
human research decisions
cost per proposed candidate
cost per executable candidate
cost per Benefit
```

## 10. Primary figures and tables

Primary Analyzer downstream metric:

```text
Verified Benefit Rate
= number of Benefit candidates / number of proposed candidates
```

### Figure 1 — System

```text
Prioritize → Verify → Internalize → Accept
```

Memory has three governed views, but the primary repair path is:

```text
Failure Experience → Analyzer → candidate repair
```

### Figure 2 — Candidate funnel

```text
failures
→ hypotheses
→ proposed candidates
→ schema-valid
→ executable
→ Benefit/Harm/Neutral/Uncertain
→ training eligible
```

### Figure 3 — Research efficiency

```text
cumulative verified Benefits
vs candidate budget / environment calls / Analyzer tokens
```

A0–A3 and R0–R3 are separate comparisons.

### Figure 4 — Language confidence versus environment

```text
Analyzer confidence
LLM judge
Memory similarity
vs F0/F1 effect
```

### Table 1 — Policy-only result

All primary comparisons:

```text
Memory OFF
Harness OFF
```

Compare:

```text
π1
success SFT
unverified repairs
environment-valid repairs
Benefit-only
Benefit–Harm
π2-human
```

### Table 2 — Analyzer/Memory ablation

```text
A0 one-shot
A1 multi-hypothesis local
A2 hierarchical no history
A3 hierarchical with history
```

Primary columns use verified Benefit yield and cost, not prose ratings.

### Figure 5 — System versus policy gain

```text
π1 / π2
×
Memory/Harness ON/OFF
```

## 11. Denominators

Always publish exact denominators for:

```text
eligible failures
Analyzer calls attempted
valid Analyzer results
abstentions
proposed candidates
schema-valid candidates
executable candidates
F0/F1 registered
valid F0/F1 outcomes
Benefit/Harm/Neutral/Uncertain
training eligible
evaluation tasks
```

Infrastructure failures remain visible and never become scientific outcomes.

## 12. Independent unit

Primary independent unit:

```text
unique task/gamefile
```

Five F0/F1 repeats are repeated measures of one causal unit, not five tasks.

## 13. Statistical plan

- preregister primary A2–A1 and A3–A2 comparisons;
- task/gamefile-level bootstrap confidence intervals;
- paired task-level comparison for success outcomes;
- McNemar may supplement binary paired policy evaluation;
- median/IQR and paired differences for steps/tokens/cost;
- Holm correction for secondary multi-condition tests;
- report effect sizes and raw numerators/denominators.

## 14. Claim boundaries

### C1 — efficient repair discovery

Supported only by downstream verified outcomes and cost.

### C2 — verification is necessary

Supported by Harm/Neutral prevalence, false-promotion analysis and F0/F1
filtering.

### C3 — verified training evidence is better

Supported only by fair T0–T5 training/evaluation.

### C4 — capability is internalized

Supported only if:

```text
π2 Memory OFF + Harness OFF
>
π1 Memory OFF + Harness OFF
```

### Memory negative result

Permitted wording:

> Direct Memory exposure can materially change rollout dynamics, but the
> direction was heterogeneous and no task rescue was observed in the three
> exposed source states.

Do not use an outlier-driven mean step change as evidence of benefit.

## 15. Outcome-contingent claim downgrades

```text
A2 not better than A1
→ remove hierarchical downstream-value claim

A3 not better than A2
→ do not claim historical Failure Experience improves repair discovery

F0/F1 reveals little Harm/Neutral
→ describe verification as diagnostic rather than necessary filtering

verified data not better than unverified
→ downgrade training-signal claim

π2 OFF/OFF not better than π1
→ do not claim policy self-improvement
```
