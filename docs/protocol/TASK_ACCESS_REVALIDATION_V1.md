# TASK_ACCESS_REVALIDATION_V1

## Purpose

Revalidate—not redesign—the existing task/gamefile access classes before
Analyzer evidence is released.

## Core rules

- The existing task/gamefile assignment is authoritative.
- All seeds, states, continuations and F0/F1 branches for one gamefile remain in
  the same access class.
- Historical exposure cannot be erased or upgraded to sealed.
- Strong-model Analyzer calls are allowed only for development-visible tasks.
- Selection tasks expose only the registered summary surface.
- Sealed confirmatory tasks expose no detailed trajectory to Analyzer,
  Researcher, few-shot construction or training.
- Failure Memory valid-unseen remains historically exposed standard OOD, not
  fresh OOD.

## Required output per task/gamefile

```text
task_id
gamefile_sha256
existing_access_class
historical_exposure_flags
allowed_consumers
allowed_artifact_granularity
strong_model_allowed
training_allowed
f0f1_development_allowed
selection_summary_allowed
confirmatory_execution_allowed
source_manifest_path
source_manifest_sha256
revalidation_disposition
revalidation_reason
```

## Allowed dispositions

```text
CONFIRMED_UNCHANGED
DOWNGRADED_DUE_TO_HISTORICAL_EXPOSURE
BLOCKED_INCONSISTENT_SOURCE_AUTHORITY
BLOCKED_MISSING_SOURCE_AUTHORITY
```

No `UPGRADED_TO_SEALED` disposition exists.
