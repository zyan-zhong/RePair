# OUTCOME_AWARE_HIERARCHICAL_ANALYZER_V2_IMPLEMENTATION_PLAN_REVIEW_V1

## Review status

```text
PLAN_BRANCH = plan/outcome-aware-hierarchical-analyzer-v2-v1
PLAN_STATUS = REVIEW_CANDIDATE
PLAN_MERGED_TO_MAIN = false
IMPLEMENTATION_STARTED = false
FORMAL_ANALYZER_EXECUTION_AUTHORIZED = false
ANALYZER_MODEL_CALLS_AUTHORIZED = false
ENVIRONMENT_EXECUTION_AUTHORIZED = false
POLICY_TRAINING_AUTHORIZED = false
```

## Reviewer checklist

### 1. Reuse and scope

- [ ] The plan reuses `ANALYZER_EVIDENCE_PACK_V1`, Memory role packs, canonical JSON, task access, F0/F1, training evidence, and evaluation infrastructure.
- [ ] It does not rebuild Runtime Core, the trajectory collector, Memory, verifier, trainer, or promotion gate.
- [ ] A0–A3 remain the failure-repair main experiment.
- [ ] Success-quality analysis remains a distinct pilot.
- [ ] Repair-effect decomposition remains downstream of formal Benefits.

### 2. Scientific attribution

- [ ] A1 local outputs are generated once and reused byte-for-byte by A2/A3.
- [ ] Local analysis is Memory-blind.
- [ ] A3 Memory is frozen, bounded, and attached only above the local lane.
- [ ] The deterministic projector cannot invent or repair executable actions.
- [ ] Duplicate candidates share execution evidence without collapsing discovery provenance.
- [ ] Primitive actions and short options are stratified.

### 3. Outcome-aware design

- [ ] Environment outcome, not a model, selects failure vs success lane.
- [ ] Failure outputs represent multiple error lifecycles rather than one forced linear onset.
- [ ] Success outputs distinguish necessary progress, useful exploration, self-recovery, and redundancy candidates.
- [ ] Success redundancy remains unverified until environment testing.
- [ ] Success optimization has a distinct effect-label namespace.

### 4. Failure-priority budget

- [ ] Only mechanical census inputs select the regime.
- [ ] Ratios are exactly 85/15, 70/30, and 55/45.
- [ ] Severe regression/cluster overrides force failure-critical mode.
- [ ] Every failing task family receives a frozen minimum failure quota.
- [ ] Analyzer-allocated samples are never used as population-prevalence denominators.

### 5. Metrics and statistics

- [ ] The literature audit accurately distinguishes localization, lifecycle, grounded-output, verified-training, process-efficiency, redundancy, and judge-reliability metrics.
- [ ] Every metric defines numerator, denominator, unit, missingness treatment, uncertainty method, and claim status.
- [ ] EVRY is the primary C1 endpoint and keeps every eligible state in the denominator.
- [ ] failure/protected-cohort Harm, ProposalCoverage, VBP, formal verifier environment steps per repaired unit, and EVRY@B are mandatory companions; no arbitrary weighted composite replaces them.
- [ ] EVRY@B uses common preregistered budgets and cumulative unique source states.
- [ ] The specificity-confirmed subset (internal CSVRY) is limited to the preregistered D0–D4 cohort and reports cohort coverage.
- [ ] Abstention, no-candidate, invalid, unsupported, and non-executable outputs cannot improve EVRY.
- [ ] Infrastructure, Harm, Neutral, and Uncertain rows remain visible.
- [ ] Task/gamefile is the primary independent unit.
- [ ] Repeated branches are not treated as independent samples.
- [ ] Task-level paired bootstrap, effect sizes, and Holm-adjusted secondary comparisons are implemented.
- [ ] Cost, latency, token, environment-call, human-decision, and reproducibility ledgers are present.
- [ ] Runtime and paper language says `project-proposed`, not `first-ever`, until final related-work review.

### 6. External-to-local transition

- [ ] Raw provider output, human/cross-check adjudication, and environment outcome are separate immutable layers.
- [ ] Existing task access and historical exposure manifests are reused.
- [ ] Rejected, abstained, Harm, and unsupported examples are preserved as typed supervision or exclusion evidence.
- [ ] Gold evaluation and local-supervision training are disjoint by task/gamefile.

### 7. Repair-effect decomposition

- [ ] D0–D4 are fully registered.
- [ ] D2 tests every prefix of a bounded option.
- [ ] D3 matched controls are selected mechanically before outcomes.
- [ ] D4 preserves the real post-intervention state while attenuating history detail.
- [ ] The plan does not overclaim complete causal mediation.

### 8. Engineering process

- [ ] Every task has a RED test, GREEN implementation, verification command, and single-purpose commit.
- [ ] File paths and public interfaces are explicit.
- [ ] No `TBD`, `TODO`, silent heuristic, or “implement similarly” instruction remains.
- [ ] Fixed-head source review occurs before any model/environment execution.
- [ ] Implementation ends with all execution authorities still false.

## Approval tokens

Approve only by recording:

```text
PLAN_APPROVED_OUTCOME_AWARE_HIERARCHICAL_ANALYZER_V2_V1
```

Request changes with:

```text
PLAN_CHANGES_REQUIRED_OUTCOME_AWARE_HIERARCHICAL_ANALYZER_V2_V1
```

Approval authorizes implementation planning execution only. It does not authorize strong-model calls, ALFWorld execution, F0/F1 scientific runs, policy training, or merge to `main`.


## Independent metric-review incorporation

```text
COMMON_REGISTERED_UNIVERSE = U_reg
FORMAL_K = 1_OR_ABSTAIN
EVRY = PRIMARY_REPAIR_DISCOVERY_ENDPOINT
EVRY_OPERATIONAL_AND_AVAILABLE = BOTH_REQUIRED
HARM = FAILURE_COHORT_PLUS_PROTECTED_BASELINE_COHORT
PROPOSAL_COVERAGE = MANDATORY
VBP = ALL_FORMALLY_PROPOSED_CANDIDATES
VERIFICATION_COST = FORMAL_ENV_STEPS_PER_REPAIRED_UNIQUE_UNIT
EVRY_AT_B_PRIMARY_X = FORMAL_ENVIRONMENT_STEPS
SPECIFICITY = SECONDARY_NOT_TRAINING_GATE
TERMINAL_CONSEQUENCE = MECHANICAL_NOT_SEMANTIC_SCORE
```

The plan remains 16 independently reviewable tasks. No production implementation
or scientific execution is authorized by this review package.


## Independent metric-review integration

```text
COMMON_REGISTERED_UNIVERSE = U_reg
FORMAL_CANDIDATE_BUDGET = K1_OR_ABSTAIN
PROTECTED_BASELINE_COHORT = REQUIRED_FOR_STRONG_HARM_CLAIM
EVRY_OPERATIONAL_AND_AVAILABLE = REQUIRED
VERIFICATION_COST_PRIMARY_UNIT = FORMAL_ENVIRONMENT_STEPS_PER_REPAIRED_UNIQUE_UNIT
CSVRY_ROLE = SECONDARY_SPECIFICITY_ONLY
WEIGHTED_COMPOSITE_SCORE = FORBIDDEN
```


## H1–H7 targeted hardening disposition

```text
H1 = ADOPTED
H2 = PARTIALLY_ADOPTED_SCHEDULER_RETAINED_WITH_NARROW_AUTHORITY
H3 = ADOPTED_ERROR_INSTANCE_MULTI_MEMBERSHIP
H4 = ADOPTED_EXPLICIT_C_STAGE_PRODUCER
H5 = PARTIALLY_ADOPTED_G_STAGE_SOURCE_CONDITIONED_NO_EXTRA_CALL
H6 = ADOPTED_SINGLE_METRIC_SOURCE_OF_TRUTH
H7 = ADOPTED_SEPARATE_RUNTIME_ACTIVATION_GATE
TASK13 = SECONDARY_NON_BLOCKING
TASK14 = POST_BENEFIT_SECONDARY
```

The plan is eligible for human approval after fixed-head publication. It does
not authorize implementation execution, strong-model calls, F0/F1, training, or
merge to main.
