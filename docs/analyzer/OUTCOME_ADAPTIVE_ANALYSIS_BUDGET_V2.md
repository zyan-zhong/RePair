# MECHANICAL_OUTCOME_ANALYSIS_SAMPLING_SCHEDULER_V1

## 0. Authority boundary

```text
NOT_AN_ANALYZER_SEMANTIC_METHOD_COMPONENT = true
NOT_USED_TO_DEFINE_U_REG = true
NOT_USED_TO_SELECT_RESEARCHER_BOTTLENECK = true
NOT_A_PAPER_METHOD_CLAIM = true
```

The registered 85/15, 70/30, and 55/45 allocations are retained only for
failure-priority offline API sampling and success-reference coverage. Formal
A0–A3 use the same failure-only `U_reg`.

## 1. Purpose

Freeze a deterministic, failure-priority allocation between failed and
successful trajectories. The allocation is selected from mechanical census
statistics only; no Analyzer or Researcher model chooses the regime.

## 2. Allowed regimes

```text
FAILURE_CRITICAL        failure=0.85 success=0.15
MIXED_PERFORMANCE       failure=0.70 success=0.30
HIGH_SUCCESS_REFINEMENT failure=0.55 success=0.45
```

Failure remains the majority in every regime.

## 3. Mechanical inputs

Only frozen aggregate fields are permitted:

```text
overall_task_success_count
overall_task_failure_count
per_family_success_count
per_family_failure_count
previously_successful_task_regression_count
budget_exhaustion_failure_count
critical_event_miss_count
unresolved_severe_failure_cluster_count
repeated_failure_mechanism_cluster_count
successful_repeat_flag_count
successful_no_effect_flag_count
successful_excessive_step_flag_count
successful_self_recovery_flag_count
```

Model-generated diagnoses, confidence, candidate count, or observed F0/F1
outcomes are forbidden inputs.

## 4. Threshold manifest

The allocator has no built-in permissive thresholds. Execution requires:

```text
MECHANICAL_ANALYSIS_BUDGET_THRESHOLDS_V1.json
```

with a human approval binding and these exact fields:

```text
schema_id
schema_version
census_manifest_sha256
failure_critical_overall_failure_floor
failure_critical_family_failure_floor
mixed_overall_failure_floor
mixed_family_failure_floor
high_success_overall_success_floor
high_success_min_family_success_floor
severe_regression_override_count
unresolved_severe_cluster_override_count
minimum_failure_items_per_failing_family
minimum_success_reference_items_per_family
approval_id
approval_sha256
```

Constraints:

- thresholds are frozen before any formal Analyzer output;
- high-success thresholds are stricter than mixed thresholds;
- any severe regression or severe cluster override forces
  `FAILURE_CRITICAL`;
- the manifest cannot be edited after formal Analyzer outcomes are visible.

## 5. Priority order

Before proportional allocation, reserve slots in this order:

```text
1. catastrophic or previously-successful-task regressions
2. repeated unresolved severe failure clusters
3. at least one failure slot for every task family with failures
4. remaining ordinary failures
5. success workflow references and regression guards
6. success efficiency candidates
```

Success items cannot consume optional slots until all registered failure floors
are met.

## 6. Deterministic selection

Within each priority stratum:

1. sort by frozen task/gamefile order;
2. preserve unique gamefiles;
3. select the first eligible items until the quota is filled;
4. record every eligible, selected, and excluded item with a reason;
5. never select by apparent repairability or model-estimated value.

## 7. Population prevalence separation

The full mechanical rollout census is the only source for policy-level
prevalence. The Analyzer sample is intentionally failure-oversampled and must not
be used to estimate:

```text
overall failure rate
mechanism prevalence in the policy population
success inefficiency prevalence
family-level policy success
```

Every paper table must label whether a denominator is:

```text
FULL_ROLLOUT_CENSUS
ANALYZER_ALLOCATED_SAMPLE
GOLD_ANNOTATION_PANEL
FORMAL_REPAIR_DISCOVERY_PANEL
```

## 8. Audit outputs

```text
ANALYSIS_BUDGET_SELECTION_MANIFEST_V1
```

records census and threshold hashes, chosen regime, reserved floors, selected
IDs, exclusion reasons, and final failure/success counts.

A model call is forbidden if this manifest is absent or invalid.
