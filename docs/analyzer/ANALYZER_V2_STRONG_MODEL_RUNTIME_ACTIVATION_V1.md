# ANALYZER_V2_STRONG_MODEL_RUNTIME_ACTIVATION_V1

## Status

```text
RUNTIME_ACTIVATION_DESIGN = FROZEN_HANDOFF
STRONG_MODEL_EXECUTION = NOT_AUTHORIZED
ENVIRONMENT_EXECUTION = NOT_AUTHORIZED
POLICY_TRAINING = NOT_AUTHORIZED
REUSES_P2_PROVIDER_ASSETS = true
```

This handoff begins only after Tasks 1–16 receive fixed-head human code approval.
It does not add a seventeenth implementation task and does not rebuild the
provider client.

Before any strong-model call, freeze one runtime manifest containing:

```text
provider and model/version
reasoning/decoding configuration
L, G, C/P, and X prompt template IDs and SHA-256
input evidence projection and access class
output schema IDs and SHA-256
token limits and context-overflow behavior
Memory exposure by condition
one-call/retry/post-send ambiguity contract
request/response raw-byte preservation
request ID, usage, latency, and cost evidence
challenger identity
local-shadow identity
source-conditioned repair production rule
scientific_use = PRIVILEGED_OFFLINE_ANALYSIS
analysis_time_information_boundary = POST_EPISODE_DEV_ONLY
```

The runtime must reuse the first-round P2 transport, provenance, refusal,
strict-structured-output, no-clobber, and ambiguous-post-send controls. Each
semantic stage writes raw and validated artifacts separately. No runtime stage
may create Benefit/Harm, a training label, or a promotion decision.

Formal execution remains blocked until:

```text
ANALYZER_DETERMINISTIC_SCIENTIFIC_INFRASTRUCTURE_CODE_APPROVED
ANALYZER_V2_RUNTIME_MANIFEST_APPROVED
PROMPT_AND_SCHEMA_HASHES_FROZEN
TASK_ACCESS_REVALIDATED
MODEL_CALL_EXECUTION_APPROVED
```
