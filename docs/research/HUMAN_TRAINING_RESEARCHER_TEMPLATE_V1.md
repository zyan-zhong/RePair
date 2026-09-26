# HUMAN_TRAINING_RESEARCHER_TEMPLATE_V1

## Purpose

Provide the human reference procedure that later Research Planner training must
imitate. Pre-decision and post-result records are separate immutable artifacts.

## PRE-DECISION RECORD

```text
research_decision_id
round_id
current_policy_identity
allowed_data_access
evidence_package_sha256s
candidate_bottlenecks
candidate_bottleneck_evidence
candidate_counterevidence
historical_research_experiences
selected_principal_bottleneck
rejected_candidates_and_reasons
deferred_candidates_and_reasons
single_primary_change
candidate_repairs_or_experiments
experiment_budget
stop_rule
success_criterion
failure_criterion
forbidden_adaptations_after_results
pre_decision_sha256
```

The human must select one principal scientific change. Multiple candidates can
be retained, but cannot silently become multiple simultaneous method changes.

## POST-RESULT RECORD

```text
research_decision_id
pre_decision_sha256
executed_experiment_manifest_sha256
protocol_integrity
result_summary
Benefit_Harm_Neutral_Uncertain_census
cost_and_resource_summary
claim_disposition
training_decision
promotion_recommendation
rollback_recommendation
lesson
next_round_implication
post_result_sha256
```

The post-result record cannot edit the pre-decision rationale.

## Authority boundary

The template organizes evidence and decisions. It does not create mechanical
facts, F0/F1 outcomes, training results or promotion authority.
