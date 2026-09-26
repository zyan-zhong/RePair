# HUMAN_TRAINING_RESEARCHER_TEMPLATE_V2

## 1. Purpose

Provide the human reference procedure for the first complete π1→π2 research
round and the supervision target for later Research Planner localization.

The Researcher prioritizes experiments. It does not generate mechanical facts,
execute actions, label F0/F1 outcomes or decide promotion.

Pre-decision and post-result records are separate immutable artifacts.

## 2. Allowed inputs

```text
π1 identity
evidence cutoff manifest
failure census
mechanical evidence summaries
Analyzer local/group results
candidate repair pool
historical Failure Experience
Memory negative result
π0→π1 NO-GO
previous F0/F1 results
training/evaluation history
resource and cost ledger
aggregate held-out metrics only
```

Detailed sealed evaluation trajectories are forbidden.

## 3. PRE-DECISION RECORD V2

Must be completed, reviewed and content-hashed before selected experiment
outcomes are visible.

### Identity and cutoff

```text
schema_id
schema_version
research_decision_id
round_id
current_policy_identity_sha256
evidence_cutoff_timestamp
evidence_cutoff_manifest_sha256
allowed_data_access
researcher_identity
pre_decision_status
```

### Observed facts

For every fact:

```text
fact_id
statement
evidence_refs[]
authority
scope
```

Facts must cite deterministic or registered outcome authority.

### Uncertainties

```text
uncertainty_id
statement
missing_evidence
decision_relevance
resolution_plan
```

### Candidate bottlenecks

For each candidate:

```text
bottleneck_id
statement
mechanism_scope
supporting_evidence_refs[]
counterevidence_refs[]
historical_experience_refs[]
task_family_coverage
estimated_verification_cost
estimated_training_relevance
risk
priority_score_components
```

### Selected principal bottleneck

```text
selected_bottleneck_id
selection_rationale
why_now
why_not_other_candidates
single_falsifiable_hypothesis
single_principal_change
```

Only one principal scientific change is allowed.

### Rejected and deferred alternatives

```text
candidate_id
disposition = REJECTED | DEFERRED
reason
required_future_evidence
repeat_of_prior_no_go
```

Recording unselected directions is mandatory.

### Experiment portfolio

```text
candidate_pool_manifest_sha256
selection_condition
selected_candidate_ids[]
selection_budget
verification_budget
API_token_budget
environment_branch_budget
GPU_budget
human_review_budget
```

### Frozen protocol

```text
baseline
intervention
fixed_variables[]
sample_definition
primary_endpoint
secondary_diagnostics[]
support_criterion
refutation_criterion
stop_condition
allowed_infrastructure_recovery
forbidden_adaptations_after_results[]
```

### Training plan

May be null before sufficient Benefits exist.

```text
training_decision_status
eligible_label_types
candidate_training_arms
same_base_checkpoint
training_token_budget
seed_plan
evaluation_plan
promotion_gate
```

### Hash and approval

```text
pre_decision_sha256
human_approval
approval_timestamp
```

## 4. POST-RESULT RECORD V2

Created only after the frozen experiment manifest is complete.

### Linkage

```text
research_decision_id
pre_decision_sha256
executed_experiment_manifest_sha256
evidence_cutoff_manifest_sha256
```

### Protocol integrity

```text
all_selected_candidates_accounted_for
all_arms_published
pair_integrity
prompt_frozen
budget_integrity
access_integrity
leakage_audit
infrastructure_incidents[]
```

### Results

```text
primary_endpoint_value
primary_numerator
primary_denominator
secondary_diagnostics
Benefit_count
Harm_count
NeutralSuccess_count
NeutralFailure_count
Uncertain_count
InfrastructureInvalid_count
task_family_coverage
cost_summary
```

### Interpretation

```text
hypothesis_status =
  SUPPORTED | NOT_SUPPORTED | INCONCLUSIVE | INVALID_PROTOCOL

alternative_explanations[]
unexpected_evidence[]
claim_disposition
```

### Training and promotion recommendation

```text
training_decision =
  BUILD_VERIFIED_DATA | HOLD | DO_NOT_TRAIN

recommended_training_arms[]
excluded_evidence[]
promotion_recommendation =
  NOT_APPLICABLE | EVALUATE_CANDIDATE | HOLD | ROLLBACK
```

These are recommendations only. Programmatic gates retain authority.

### Learning

```text
lesson
what_not_to_repeat
research_memory_writeback_refs[]
next_round_implication
post_result_sha256
```

The post-result record cannot edit the pre-decision rationale.

## 5. Researcher selection experiment

Conditions:

```text
R0_FIFO
R1_FREQUENCY_ONLY
R2_HUMAN_TEMPLATE_V2
R3_STRONG_API_SHADOW
```

R3 runs only after the R2 pre-decision artifact is frozen. R3 cannot modify the
current reference round.

All conditions receive:

- the same candidate pool;
- the same visible evidence;
- the same verification budget;
- the same cost accounting;
- no future F0/F1 outcomes.

Primary metrics:

```text
Benefits per selected candidate budget
Harm count
Neutral count
environment calls per Benefit
unique task families covered
duplicate mechanism rate
repeated-NO-GO rate
single-change compliance
human revision rate for R3
```

## 6. Coordination with Analyzer

The Researcher may:

- prioritize Analyzer candidates;
- request an executable instantiation of a trainable rule;
- defer weakly grounded candidates;
- select task-family coverage.

It may not:

- modify Analyzer raw outputs;
- change candidate actions;
- turn abstention into a candidate;
- label a candidate as Benefit/Harm;
- request selective reruns after seeing unfavorable outcomes.

## 7. Coordination with Verifier

The Researcher freezes:

- candidate portfolio;
- pair budget;
- primary endpoint;
- repeat rule;
- stop condition.

The Verifier publishes outcomes independently.

## 8. Coordination with training

Training begins only after:

```text
verified F0/F1 manifest sealed
training eligibility audit passed
task/gamefile contamination audit passed
training arm/config frozen
```

The Researcher cannot switch training method after seeing policy evaluation
unless a new research decision is created.

## 9. Historical evidence requirements

The first reference round must explicitly include:

```text
π0→π1 long-horizon NO-GO
Failure Memory Q1–Q3 NOT_SUPPORTED
three direct Memory exposure cases
post-hoc trajectory dynamics
cost and infrastructure incidents
```

This prevents repetition of the one-case/one-action correction route without
new evidence.

## 10. Deferred automation

The Human Researcher remains primary for π1→π2.

Strong API and local Researcher may run in shadow mode. Autonomous control of
π2→π3 requires a successful, independently audited π1→π2 GO.
