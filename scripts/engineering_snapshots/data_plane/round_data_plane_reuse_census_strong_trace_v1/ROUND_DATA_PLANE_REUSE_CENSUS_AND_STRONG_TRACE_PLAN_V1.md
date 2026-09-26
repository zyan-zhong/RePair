# Round Data Plane Reuse Census and Strong Trace Plan V1

> **Approval:** `APPROVE_TWO_PACKAGE_HUMAN_PRIORITY_AND_STRONG_TRACE_DATA_PLANE_CENSUS_V1`

**Goal:** Build a read-only, conservative inventory of existing project assets and Strong-role trace coverage before any new Round Data Plane implementation is proposed.

## Scope

- Inspect current repository state and local Git history.
- Inspect the current Human Reference Round artifact tree.
- Index existing schemas/modules/scripts by semantic role.
- Index Strong Analyzer and Strong Research Planner request/response/adjudication artifacts.
- Report candidate reuse and missing bindings.
- Make zero repository or experiment mutations.

## Required outputs

1. Repository ref index.
2. Existing asset index.
3. Semantic-role candidate map.
4. Strong role trace candidate index.
5. Reuse/gap matrix.
6. Duplicate-implementation risk report.
7. Human-readable summary.

## Strong Analyzer trace coverage

The census must look for and distinguish:

- evidence cutoff and input projection;
- provider request bytes;
- provider response bytes;
- logical call and transport attempts;
- A0/A1/A2/A3/X validated results;
- abstention/schema-invalid/semantic-invalid/refusal/censored outcomes;
- X/Human adjudication;
- later F0/F1 alignment;
- token, latency, cost, retry/no-retry fields;
- distillation eligibility.

## Strong Research Planner trace coverage

The census must look for and distinguish:

- Strong PRE and POST;
- bottleneck ranking;
- selected/rejected/deferred alternatives;
- repair portfolio/program;
- verification budget;
- conditional and final training policy;
- result interpretation and next-round recommendation;
- Human field adjudication;
- environment and training-result alignment;
- distillation eligibility.

## Implementation rule after census

No new registry/index/schema is implemented until the report confirms that an equivalent asset does not already exist. History-only candidates must be reviewed for selective reuse or adaptation before creating new files.
