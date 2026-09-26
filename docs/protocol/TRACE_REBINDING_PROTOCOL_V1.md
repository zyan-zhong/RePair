# TRACE_REBINDING_PROTOCOL_V1

## Design decision

Analyzer-era identities are added through an immutable content-addressed
sidecar. Existing PolicyCallEvidenceV1, ActionTrace, PublicTransitionRecordV1,
EpisodeArtifact and bundle bytes are never rewritten.

This is required because historical attempt bundles and scientific authorities
already bind their exact bytes.

## Input bundle

A formal Analyzer bundle must contain:

```text
attempt.json
action_traces.jsonl
policy_calls.jsonl
public_transitions.jsonl
SHA256SUMS
```

Legacy bundles without `policy_calls.jsonl` may remain historical evidence but
cannot enter the formal Analyzer localization experiment.

## Sidecar output

`TRAJECTORY_REBINDING_MANIFEST_V1` contains:

```text
schema_id
schema_version
source_attempt_bundle_path
source_attempt_bundle_sha256
source_episode_semantic_sha256
source_file_bindings
policy_identity_sha256
task_access_revalidation_sha256

analyzer_run_id
analyzer_condition
analyzer_evidence_pack_id
analyzer_evidence_sha256

memory_pack_id
memory_snapshot_id
memory_pack_sha256

research_decision_id
candidate_repair_ids

paired_state_id
f0f1_arm
pair_seed
repair_registration_sha256

training_sample_ids
result_manifest_ids

alignment_census
revalidation_status
manifest_sha256
```

Nullable fields are explicit and remain null until the corresponding stage
exists. A future-stage identifier must never be fabricated just to satisfy the
schema.

## Exact alignment requirements

```text
policy_call.model_call_index == action_trace.model_call_index
policy_call goal/prompt/observation/menu/raw response == action_trace values
policy_call budget_before == action_trace before counters
executed ActionTrace environment_step_index/action == PublicTransition
all model-call indices contiguous from zero
all transition environment-step indices unique and increasing
episode.trace_count == action trace count
episode.public_transition_count == transition count
policy call count == action trace count
episode.environment_call_trace_count is recomputable
initial/final observations bind to episode hashes
SHA256SUMS covers exact bundle files
all source identities match the sidecar task/policy binding
```

## Continuity chains

The revalidator must prove:

```text
post observation/menu of executed step n
==
pre observation/menu of executed step n+1

executed history at call k
==
ordered public transitions before call k

budget_after trace k
==
budget_before trace k+1
```

Nonexecuted policy attempts may occur between environment steps and must remain
in the evidence chain.

## Failure behavior

Any mismatch produces a typed blocked disposition. It never repairs, sorts,
drops or reorders source evidence.
