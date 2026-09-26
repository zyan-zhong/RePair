# HIERARCHICAL_ANALYZER_V2_OUTPUT_CONTRACT_V1

## 1. Purpose

Freeze typed outcome-aware semantic outputs while preserving authority separation
among deterministic facts, semantic hypotheses, executable proposals,
environment effects, and training/promotion decisions.

All artifacts are canonical JSON, no-clobber, content-addressed, and bound to one
run manifest.

## 2. Route availability and information boundary

Every run binds:

```text
route_status = SCIENTIFIC_OUTCOME_AVAILABLE | INFRASTRUCTURE_UNAVAILABLE | PROTOCOL_INVALID | EVIDENCE_INCOMPLETE
scientific_use = PRIVILEGED_OFFLINE_ANALYSIS
analysis_time_information_boundary = POST_EPISODE_DEV_ONLY
```

Only `SCIENTIFIC_OUTCOME_AVAILABLE` may carry `trajectory_outcome` and enter a
semantic lane.

## 3. Run manifest

```text
ANALYZER_RUN_MANIFEST_V1
```

Required identity, provider/model/request/prompt/schema/decoding hashes, input
and output artifact hashes, Memory packet hashes, token/latency/cost evidence,
execution completeness, scientific-use class, and final manifest hash.

`scientific_use` is one of:

```text
SCHEMA_DEVELOPMENT_FIXTURE
PILOT_EXCLUDED_FROM_FORMAL_CLAIM
FORMAL_DEVELOPMENT_EXPERIMENT
LOCAL_SHADOW_EVALUATION
```

## 4. Common local result

```text
ANALYZER_LOCAL_RESULT_V1
```

Required common fields:

```text
analyzer_run_id
condition_id
trajectory_outcome = FAILURE | SUCCESS
analysis_objective = FAILURE_DIAGNOSIS | SUCCESS_QUALITY
evidence_pack_sha256
policy_identity_sha256
task_id
gamefile_sha256
source_attempt_bundle_sha256
raw_response_sha256
validated_result_sha256
```

Exactly one lane payload is non-null.

## 5. Failure local payload

```text
failure_analysis:
  relevant_start_call_index
  error_instances[]:
    error_instance_id
    rank
    trigger_call_index
    lifecycle_status = ACTIVE | CLEAN_RESOLUTION | COSTLY_RESOLUTION |
                       LATENT_ACTIVE | DOWNSTREAM_SYMPTOM
    resolution_start/end | null
    terminal_impact
    supporting_evidence_refs[]
    counterevidence_refs[]
    alternative_explanation_ids[]
    criticality_proposal
    confidence
    uncertainty
  proposed_critical_error_instance_id | null
  critical_window_start/end
  recovery_region_start/end | null
  terminal_consequence_call_index
  local_repairs[]
  abstained
  abstain_reason | null
```

## 6. Success local payload

```text
success_analysis:
  progress_instances[]
  necessary_decisions[]
  critical_success_transitions[]
  useful_exploration[]
  self_recovery_events[]
  redundancy_candidates[]
  avoidable_detours[]
  no_effect_candidates[]
  workflow_template
  regression_guard_transitions[]
  success_optimization_candidates[]
  abstained
  abstain_reason | null
```

Each item cites evidence and records uncertainty. `redundancy_candidates` and
`success_optimization_candidates` require environment verification.

## 7. Group manifest

```text
ANALYZER_GROUP_MANIFEST_V1
```

Records group type, member local/evidence hashes, task family, mechanical
signature, progress/outcome signature, grouping code/config hashes, and
`outcome_blind_selection=true`.

Each member is an `ErrorInstanceMembershipV1` binding one local-result hash, one
error-instance ID, one evidence-pack hash, one mechanical signature, and one
task/gamefile inference cluster. An episode may contribute multiple memberships.

Group type:

```text
FAILURE_MECHANISM_GROUP
SUCCESS_WORKFLOW_GROUP
CROSS_OUTCOME_MATCHED_GROUP
```

## 8. Group result

```text
ANALYZER_GROUP_RESULT_V1
```

Contains recurring mechanisms or workflows, support/counterexample references,
scope, applicability/non-applicability, historical comparison, repair or
optimization templates, member inclusion/exclusion, known risks, abstention,
and raw/validated hashes.

A3 requires exactly one frozen Memory packet, including an explicit
`NO_APPLICABLE_MEMORY` packet when no record applies. A0–A2 require none.

Optional `source_conditioned_repairs[]` bind one member error instance, exact
source-state/menu hashes, executable bytes or ABSTAIN, evidence refs, rank, and
uncertainty. Abstract templates alone are not executable; C/P/X cannot rewrite
these bytes.

## 9. Component attribution and profile

```text
ANALYZER_COMPONENT_PROFILE_V1
```

Required:

```text
semantic_attribution_artifact_sha256
principal_component
secondary_components[]
supporting_evidence_refs[]
uncertainty
raw_response_sha256
validated_result_sha256
principal_deficit | null
secondary_deficits[]
demonstrated_strengths[]
fragile_strengths[]
self_recovery_capabilities[]
supporting_group_refs[]
counterexample_refs[]
uncertainty
```

## 10. Policy behavior profile

```text
POLICY_BEHAVIOR_PROFILE_V1
```

Contains failure burden, success quality, regression risk, optimization
opportunity, family coverage, candidate bottlenecks, historical NO-GO overlap,
and uncertainty. It contains no selected principal change, budget, training
method, or promotion recommendation.

## 11. Cross-check result

```text
ANALYZER_CROSSCHECK_RESULT_V1
```

Required:

```text
source_claim_ref
disposition = ACCEPT | DOWNGRADE_SCOPE | REQUIRE_ABSTENTION | REJECT
support_refs[]
contradiction_refs[]
missing_evidence_refs[]
alternative_explanations[]
current_trajectory_support
historical_memory_support
current_memory_conflict
reason
raw_response_sha256
validated_result_sha256
```

Cross-check is a sidecar; original outputs remain immutable.

## 12. Failure repair candidate

```text
ANALYZER_REPAIR_CANDIDATE_V1
```

Binds source state, policy, Memory, source hypotheses/evidence, exact action or
1–4 action option, termination, budget/return-control rules, rank, uncertainty,
known risks, cross-check disposition, and candidate hash.

Only exact executable action or short-option statuses enter F1.

## 13. Success optimization candidate

```text
ANALYZER_SUCCESS_OPTIMIZATION_CANDIDATE_V1
```

Binds the successful source trajectory, targeted step/window, proposed removal,
replacement, or compression, preserved-success requirement, efficiency metric,
regression guards, evidence, uncertainty, and candidate hash.

No candidate is labeled redundant or beneficial before environment testing.

## 14. Success workflow and regression guard

```text
SUCCESS_WORKFLOW_REFERENCE_V1
REGRESSION_GUARD_V1
```

The workflow reference records necessary transitions and useful exploration. The
guard records state/evidence conditions that later training/evaluation must not
break.

## 15. Repair effect decomposition trace

```text
REPAIR_EFFECT_DECOMPOSITION_TRACE_V1
```

Records deterministic state/observation/menu/history/budget deltas for D0–D4
without inferring a causal mechanism.

## 16. Repair-effect decomposition result

```text
REPAIR_EFFECT_DECOMPOSITION_RESULT_V1
```

Required fields:

```text
decomposition_id
source_state_sha256
candidate_repair_sha256
preregistered_cohort_manifest_sha256
D0_result_ref
D1_result_ref
D2_prefix_result_refs[]
D3_matched_perturbation_result_ref
D4_history_attenuation_result_ref
full_repair_benefit_retained
minimal_sufficient_prefix_length | null
minimal_sufficient_effect_type = SPECIFIC_SINGLE_ACTION_EFFECT |
                                 MINIMAL_PREFIX_EFFECT |
                                 COMPOSITIONAL_OPTION_EFFECT |
                                 UNRESOLVED
matched_perturbation_reproduced_benefit
history_context_dependence = SUPPORTED | NOT_SUPPORTED | UNRESOLVED
specificity_control_passed
csvry_eligible
confound_flags[]
mechanism_label = SPECIFIC_SINGLE_ACTION_EFFECT |
                  MINIMAL_PREFIX_EFFECT |
                  COMPOSITIONAL_OPTION_EFFECT |
                  HISTORY_CONTEXT_DEPENDENT |
                  NONSPECIFIC_PERTURBATION_EFFECT |
                  BUDGET_OR_EXTRA_OBSERVATION_CONFOUNDED |
                  UNRESOLVED_MULTI_CHANNEL_EFFECT
result_sha256
```

`csvry_eligible=true` requires membership in the frozen decomposition cohort, a
valid D0–D4 evidence bundle, and no infrastructure-missing branch.
`specificity_control_passed=true` requires D1 Benefit retention, D3 failure to
reproduce the same Benefit, and a non-null D2 shortest-tested-sufficient action/prefix
classification; `minimal` is allowed only after all shorter prefixes are definitively non-Benefit. D4 is retained as a separate context-dependence result.

## 17. Cognitive role trace

```text
COGNITIVE_ROLE_TRACE_V1
```

Follows `COGNITIVE_ROLE_TRACE_AND_LOCAL_SUPERVISION_V1` and binds every external
Analyzer/Researcher call, human adjudication, cross-check, and downstream effect.

## 18. Parser prohibitions

Reject:

- duplicate/unknown fields;
- unsupported indices or evidence IDs;
- untyped facts/hypotheses;
- Benefit/Harm/Neutral/Uncertain claims;
- direct training/promotion decisions;
- hidden-state repairs;
- automatic fuzzy action correction;
- success optimization without preserved-success requirement;
- cross-check that overwrites source outputs;
- incomplete provider trace/provenance.
