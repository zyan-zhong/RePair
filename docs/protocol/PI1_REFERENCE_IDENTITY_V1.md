# PI1_REFERENCE_IDENTITY_V1

## Status

```text
PROTOCOL = FROZEN
CONCRETE_IDENTITY = NOT_YET_MATERIALIZED
IDENTITY_SOURCE = SEALED_EXISTING_MANIFESTS_ONLY
```

## Purpose

Bind every Analyzer, F0/F1 and training artifact to one exact π1 realization.
The protocol must not guess a checkpoint from a directory name or use "latest".

## Required identity fields

```text
logical_policy_id
checkpoint_instance_id
base_model_id
base_model_artifact_sha256
adapter_id
adapter_artifact_sha256
tokenizer_identity
tokenizer_artifact_sha256
chat_template_sha256
policy_runtime_manifest_path
policy_runtime_manifest_sha256
decoding_contract_sha256
raw_policy_prompt_protocol_sha256
runtime_core_commit
evaluator_commit
training_config_path
training_config_sha256
training_data_manifest_path
training_data_manifest_sha256
training_seed
reference_evaluation_manifest_path
reference_evaluation_manifest_sha256
materialization_source_artifact_sha256s
identity_sha256
```

## Materialization rules

1. Read only sealed repository/evidence manifests.
2. Resolve one concrete checkpoint; ambiguity is a hard failure.
3. Reject symlinks and non-regular identity inputs.
4. Recompute every referenced file SHA-256.
5. Require the logical policy and concrete checkpoint identities to agree with
   existing TraceProvenance/EpisodeArtifact evidence.
6. Do not infer missing hashes.
7. Write a new content-addressed identity artifact outside the old sealed run.
8. The identity artifact does not modify or supersede the original manifests.

## Prohibited shortcuts

```text
choose Train17 because it was previously primary without checking manifests
use branch HEAD as model identity
bind only adapter path without base/tokenizer/chat-template identity
reuse π0 evidence as π1 evidence
silently accept multiple candidate checkpoints
```
