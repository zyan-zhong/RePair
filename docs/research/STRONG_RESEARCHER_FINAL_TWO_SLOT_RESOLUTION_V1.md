# Strong Researcher Final Two-Slot Resolution V1

## Why only two slots remain

After the authority and classifier recoveries, seven of nine non-null,
Researcher-readable high-level evidence slots resolve to dedicated, schema-
bearing frozen artifacts. The only remaining slots are:

```text
policy_scorecard.policy_config_sha256
policy_scorecard.task_set_manifest_sha256
```

This stage does not reopen the seven resolved slots.

## Policy-config semantic alias

The sealed policy-lineage view says:

```text
policy_version = P4-R1-Q2-BAD-TRAIN17
policy_condition_manifest_sha256 =
457f4f58cd6733f863fa690e45c962f3fda3b2cf511d9961eb715b7a52c07e0b
```

The blind V1 field currently named `policy_config_sha256` carries the same SHA.
Historical P4 attempt artifacts also identify that SHA as
`policy_condition_manifest_sha256`; those attempt records are references, not
the manifest authority.

Resolution therefore requires two independent bindings:

```text
sealed policy lineage
    policy_condition_manifest_sha256 == target
    policy_version == P4-R1-Q2-BAD-TRAIN17

AND

dedicated policy-condition manifest
    exact file SHA == target
    OR
    registered policy_condition_manifest_sha256 == target
    and condition identity == P4-R1-Q2-BAD-TRAIN17
```

The model-readable view explicitly records that this is a semantic alias from
the legacy `policy_config_sha256` field to the policy-condition manifest.

## Task-set rule

The task-set target is:

```text
c21a280829623546eaa6ad7be4b472ba64fc267f2a290f6df39dafb41f01b448
```

The following never substitute for it:

```text
TASK_ACCESS_MANIFEST
split/task-access SHA
SCIENTIFIC_UNIT_IDENTITY_V1
per-task attempt artifacts
Human conversational knowledge
```

Accepted authority is only:

```text
exact readable file SHA == target
```

or:

```text
dedicated task-set manifest
with task_set_manifest_sha256 == target
```

If no such leaf exists, the stage stays blocked and exports all exact target
occurrences plus source-code candidates that mention the task-set hash field.
A deterministic reconstruction is not performed until the project's exact
registered task-set hash builder is located and reviewed.

## Preservation

The previous seven resolved slots must remain byte-equivalent in the stitched
hydration manifest. Human adjudication, Human PRE, repair portfolio, budget and
authority boundaries are unchanged.

If both final slots resolve, the existing generic hydration functions create:

```text
STRONG_RESEARCHER_BLIND_PRE_INPUT_V2
RESEARCH_PLANNER_REFERENCE_TRACE_V3
```

The default package stops for review before push, freeze or Strong API use.
