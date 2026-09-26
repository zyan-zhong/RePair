# COGNITIVE_ROLE_TRACE_AND_LOCAL_SUPERVISION_V1

## 1. Purpose

Preserve every external strong-model Analyzer and Training Researcher call from
the first formal request and materialize governed local-supervision datasets
without creating a second trajectory store or a second task-access system.

## 2. Reused authorities

Reuse:

```text
ANALYZER_EVIDENCE_PACK_V1
DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1
DISTILLATION_TASK_ACCESS_MANIFEST_V1
ANALYZER_MEMORY_PACK_V1
RESEARCHER_MEMORY_PACK_V1
same-state F0/F1 result manifests
existing request/response evidence patterns
```

## 3. Common trace envelope

```text
COGNITIVE_ROLE_TRACE_V1
```

Required identity:

```text
role = ANALYZER | TRAINING_RESEARCHER
analysis_objective
round_id
policy_version
evidence_cutoff
task_id
gamefile_sha256
task_family
access_class
evidence_pack_sha256
mechanical_evidence_sha256
memory_pack_sha256 | null
memory_snapshot_sha256 | null
```

Provider-call evidence:

```text
provider
model
model_version
request_date
request_id
prompt_template_id
prompt_sha256
request_contract_sha256
output_schema_id
output_schema_sha256
reasoning_configuration
raw_request_sha256
raw_response_sha256
raw_request_pointer
raw_response_pointer
parse_status
refusal_status
infrastructure_status
input_tokens
output_tokens
latency_ms
cost_amount
cost_currency
```

Adjudication:

```text
human_disposition = ACCEPT | REVISE | REJECT | DEFER
human_revision_sha256 | null
revision_diff_sha256 | null
revision_reason | null
unsupported_fact_refs[]
missing_evidence_refs[]
crosscheck_disposition
```

Downstream binding:

```text
candidate_ids[]
verification_result_sha256s[]
optimization_result_sha256s[]
training_sample_ids[]
final_inclusion_status
final_inclusion_reason
```

## 4. Immutable three-layer record

Always retain:

```text
Layer 1: raw external-model output
Layer 2: adjudicated structured output
Layer 3: downstream environment outcome
```

Human revision never overwrites the raw response.

## 5. Analyzer supervision target

Primary target:

```text
adjudicated structured analysis
```

Auxiliary labels include:

```text
evidence grounding
unsupported-fact flags
abstention
cross-check disposition
verified Benefit/Harm/Neutral/Uncertain
repair effect type
success-optimization effect type
```

Raw prose is not the sole target.

## 6. Researcher supervision target

Retain both selected and rejected/deferred directions:

```text
candidate bottlenecks
selected bottleneck
rejected alternatives
selection rationale
single principal change
experiment budget
support/refutation criteria
post-experiment result
promote/rollback/hold
lesson
next-round implication
```

The pre-experiment record is frozen before outcomes and cannot be rewritten after
results are visible.

## 7. Materialized datasets

```text
LOCAL_ANALYZER_SUPERVISION_DATASET_V1
LOCAL_RESEARCHER_SUPERVISION_DATASET_V1
```

Each record references original evidence by hash. Trajectory bytes are not
copied into a new store.

## 8. Split and leakage rules

- task/gamefile is the split unit;
- the gold panel is excluded from local Analyzer training;
- formal repair-discovery and confirmatory tasks cannot become local-training
  examples;
- the strong model is called only where the existing task-access manifest allows;
- local shadow evaluation uses disjoint task/gamefiles;
- provider outputs rejected for privilege or leakage remain preserved but are
  never training targets.

## 9. Transition stages

```text
Stage A: external primary + local shadow
Stage B: distilled local Analyzer primary candidate + external disagreement audit
Stage C: validated local Analyzer primary + routine external calls removed
```

Environment verification remains independent at every stage.


## 10. Researcher supervision prerequisite

`LOCAL_RESEARCHER_SUPERVISION_DATASET_V1` may be materialized only from frozen
Human/API Researcher pre/post records governed by
`HUMAN_TRAINING_RESEARCHER_TEMPLATE_V1`. Analyzer artifacts alone cannot create,
infer, or fabricate a Researcher target. Pre-decision and post-outcome records
remain physically separate to prevent hindsight leakage.
