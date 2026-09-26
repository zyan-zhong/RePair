# ANALYZER_GOLD_PANEL_PROTOCOL_V1

## 1. Purpose

Create disjoint human-labeled development panels for failure localization and
success-quality analysis before formal repair-discovery experiments.

Neither panel creates environment-effect labels or policy-training data.

## 2. Data layers

### Schema fixtures

Three registered Memory source cases for schema/prompt development only.

### Failure gold panel

```text
target 36 unique failed episodes
minimum 30
approximately six per task family where eligible
```

### Success reference panel

```text
12 unique successful episodes
approximately two per task family where eligible
```

### Fresh effect panels

Formal failure repair discovery and success optimization use fresh train-side
items disjoint by task/gamefile from fixtures and gold panels.

## 3. Common eligibility

An episode is eligible only if:

- exact attempt bundle and rebinding validate;
- frozen π1 identity matches;
- task access allows development-visible analysis;
- all evidence hashes exist;
- gamefile is unique within the panel;
- it is not a held-out evaluation trajectory.

Failure and success panels additionally require their registered terminal
outcome.

## 4. Deterministic selection

Within each outcome and task family:

1. sort by frozen task/gamefile order;
2. select first unique gamefiles until quota;
3. preserve complete eligibility/exclusion census;
4. freeze the panel manifest before annotation.

Manual selection by apparent repairability, cleanliness, or narrative value is
forbidden.

## 5. Failure annotation fields

```text
relevant_start_call_index
error_instances[]:
  trigger_call_index
  lifecycle_status
  resolution_region
  terminal_impact
  evidence_refs[]
  counterevidence_refs[]
primary_critical_error_instance_id | null
critical_window_start/end
recovery_region_start/end | null
terminal_consequence_call_index
primary_mechanism_family
secondary_mechanism_families[]
alternative_explanations[]
repairability
annotator_confidence
```


Failure annotation never forces a unique root cause. Annotators may select
`MULTI_CAUSAL`, `INDETERMINATE`, or `INSUFFICIENT_EVIDENCE`; all original and
adjudicated lifecycle labels remain preserved.

## 6. Success annotation fields

```text
progress_instances[]
necessary_decisions[]
critical_success_transitions[]
useful_exploration[]
self_recovery_events[]
redundancy_candidates[]
avoidable_detours[]
workflow_start/end
regression_guard_transitions[]
annotator_confidence
```

A redundancy annotation is a human hypothesis for evaluation, not an effect
label. Removal safety requires environment testing.

## 7. Double annotation

Independently double-annotate 20%–25% of each panel, with at least eight failed
episodes and at least three successful episodes where panel size permits.

Report pre-adjudication agreement from `ANALYZER_METRIC_REGISTRY_V1`.

Disagreements are resolved using evidence only, without Analyzer outputs, Memory,
or future environment effects. Preserve both original labels and the adjudicated
label.

## 8. Leakage controls

Neither panel may be used for:

- local Analyzer training;
- A3 Memory construction;
- Researcher prioritization;
- formal Benefit denominators;
- π2 policy training.

Any future local Analyzer training/evaluation split is disjoint by task/gamefile.

## 9. GO gate

Proceed only if evidence completeness, annotation schema stability,
mechanical-reference validation, inter-annotator agreement, and fail-closed
output parsing pass before formal Analyzer calls.
