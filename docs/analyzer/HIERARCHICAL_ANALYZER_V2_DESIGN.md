# HIERARCHICAL_ANALYZER_V2_DESIGN

## 0. Status and authority

```text
STATUS = OUTCOME_AWARE_DESIGN_FREEZE_CANDIDATE_V3
DESIGN_REVIEWED_IN_CHAT = true
DESIGN_MERGED_TO_MAIN = false
FORMAL_ANALYZER_EXECUTION_AUTHORIZED = false
ANALYZER_MODEL_CALLS_AUTHORIZED = false
ENVIRONMENT_EXECUTION_AUTHORIZED = false
POLICY_TRAINING_AUTHORIZED = false
BENEFIT_HARM_AUTHORITY = ENVIRONMENT_VERIFIER_ONLY
PROMOTION_AUTHORITY = INDEPENDENT_PROMOTION_GATE_ONLY
MAIN_CLAIM_CREATED = false
```

This revision consumes the sealed reference-loop evidence foundation and the
already governed Persistent Failure Experience Library. It does not reopen the
Memory implementation, rebuild the trajectory collector, alter the same-state
F0/F1 authority, call an Analyzer model, execute ALFWorld, train a policy, or
merge the design into `main`.

## 1. Scientific role in the π1→π2 reference loop

The Analyzer is an outcome-aware behavior analyst. It answers different
questions for failed and successful trajectories while preserving one common
mechanical evidence substrate.

### Failed trajectory objective

```text
Which errors occurred?
Which errors remained active, were resolved, or were only downstream symptoms?
Which mechanism is most consistent with the final failure?
Which small executable repair is worth testing?
When should the system abstain?
```

### Successful trajectory objective

```text
Which decisions were necessary for success?
Which exploration steps were useful rather than wasteful?
Where did the policy recover from an earlier mistake?
Which steps are only candidates for redundancy or compression?
Which successful transitions must be protected from regression?
```

The Analyzer does **not** answer:

```text
Did a repair help?
Was a successful step truly removable?
Is the intervention safe?
Should a candidate enter training?
Should π2 be promoted?
```

Those decisions remain with deterministic execution checks, the same-state
Environment Verifier, the verified training evidence builder, and the
independent promotion gate.

The intended contribution is not longer analysis prose. The intended evidence
is improved downstream verified-repair discovery, safe success-preserving
optimization, and higher-quality structured supervision under a frozen budget.

## 2. Existing assets reused without rebuilding

### 2.1 Evidence foundation

Every condition consumes the existing immutable:

```text
ANALYZER_EVIDENCE_PACK_V1
```

It already binds policy identity, task/gamefile/seed identity, complete policy
calls, observations, full admissible menus, executed history, prompts, raw
responses, parser/execution status, public transitions, environment outcomes,
budgets, deterministic mechanical evidence, trajectory rebinding, and
historical lineage.

The common evidence pack is identical across A0–A3. This revision adds no second
collector and no second runtime.

### 2.2 P2 one-case Analyzer assets

Reuse the provider request/response evidence, strict output handling,
critical-step localization, bounded correction, bounded recovery, abstention,
and fail-closed post-send behavior. Do not import the old restricted evidence
view as a truth source.

### 2.3 Hierarchical post-hoc assets

Reuse the approved semantic decomposition:

```text
trajectory-local events
→ recurring mechanisms
→ matched groups
→ task-family scope
→ capability/component profile
→ global challenge profile
→ independent cross-check
```

Historical prose is not fact authority. Every V2 claim must bind current
content-addressed evidence and preserve counterexamples.

### 2.4 Persistent Failure Experience Library

Reuse:

```text
ANALYZER_MEMORY_PACK_V1
RESEARCHER_MEMORY_PACK_V1
```

including provenance, applicability, non-applicability, counterexamples,
effect history, task-access controls, and the registered negative direct-to-
policy result. Memory is an evidence substrate, not a reasoning agent and not an
environment-effect judge.

### 2.5 Existing access and distillation governance

Reuse the existing historical-access audit and task-access manifest. Do not
create a parallel teacher-access system. External Analyzer/Researcher traces
must bind the existing task/gamefile split and access class.

## 3. Outcome router and mechanical sampling authority

Every Analyzer use is privileged offline analysis and binds:

```text
scientific_use = PRIVILEGED_OFFLINE_ANALYSIS
analysis_time_information_boundary = POST_EPISODE_DEV_ONLY
```

A deterministic route-availability gate first distinguishes:

```text
SCIENTIFIC_OUTCOME_AVAILABLE
INFRASTRUCTURE_UNAVAILABLE
PROTOCOL_INVALID
EVIDENCE_INCOMPLETE
```

Only a scientifically available episode may be routed from the authoritative
environment terminal result into a semantic lane:

```text
trajectory_outcome = FAILURE
→ FAILURE_DIAGNOSIS_LANE

trajectory_outcome = SUCCESS
→ SUCCESS_QUALITY_LANE
```

The strong model never decides which lane is used and never decides how much
failure-versus-success budget the round receives.

Large-scale offline sampling is selected mechanically through:

```text
MECHANICAL_OUTCOME_ANALYSIS_SAMPLING_SCHEDULER_V1
```

This scheduler is not an Analyzer semantic method component, does not define the
formal failure `U_reg`, does not choose the Training Researcher bottleneck, and
is not a paper method claim.

with three allowed allocations:

```text
FAILURE_CRITICAL       = 85% failure / 15% success
MIXED_PERFORMANCE      = 70% failure / 30% success
HIGH_SUCCESS_REFINEMENT= 55% failure / 45% success
```

Failure analysis remains the majority in every regime. Severe regressions,
repeated unresolved mechanisms, and family-specific failure floors override
success-optimization sampling. Exact regime thresholds must be frozen in a
human-approved mechanical threshold manifest before any formal Analyzer result
is visible. Code has no permissive default threshold.

The complete mechanical census remains the prevalence authority. The
failure-oversampled Analyzer cohort is never used to estimate population-level
failure or success prevalence.

## 4. Five semantic levels with four controlled model-call stages

The final semantic hierarchy is:

```text
Mechanical facts
        ↓
L — Local Outcome Lifecycle
        ↓
G — Cross-Trajectory Mechanism / Workflow Grouping
        ↓
C — Component / Capability Attribution
        ↓
P — Policy Behavior Profile
        ↓
X — Independent Cross-check
        ↓
Deterministic Candidate Projector
        ↓
Human Training Researcher
```

This is not five model calls per episode. Execution is compressed into four
controlled stages:

| Stage | Unit | Purpose |
|---|---|---|
| L | one episode | local failure lifecycle or success-quality analysis |
| G | one outcome-blind group | recurring mechanism or reusable workflow |
| C/P | one batch of frozen groups | capability attribution and policy profile |
| X | shortlisted hypotheses/candidates only | challenge, scope correction, abstention |
| Projector | deterministic | register executable candidates and guards |

## 5. L — Local Outcome Lifecycle

### 5.1 Failure lane

The local result contains multiple `error_instances[]`, not one assumed linear
root-error chain. Each error instance records:

```text
trigger and evidence
active / resolved / latent / downstream-symptom status
resolution region
budget or state residue
terminal impact
criticality proposal
competing mechanisms
counterevidence
candidate repair or ABSTAIN
```

The Analyzer may propose criticality. Only F0/F1 can create verified critical
effect evidence.

### 5.2 Success lane

The local result contains:

```text
progress_instances[]
necessary_decisions[]
critical_success_transitions[]
useful_exploration[]
self_recovery_events[]
redundancy_candidates[]
avoidable_detours[]
no_effect_candidates[]
workflow_template
regression_guard_transitions[]
uncertainty
```

A `redundancy_candidate` is not a removable-step truth label. It is only a
registered hypothesis requiring a success-preserving environment test.

### 5.3 Common local requirements

Every semantic statement cites immutable evidence IDs. Facts, semantic
hypotheses, repair proposals, registered boundaries, and effect evidence remain
typed separately. Local analysis is Memory-blind for A0–A3 local passes.

## 6. G — Cross-Trajectory Synthesis

Two group types are permitted:

```text
FAILURE_MECHANISM_GROUP
SUCCESS_WORKFLOW_GROUP
```

and a deterministic matched view may align successful and failed trajectories
of the same task family/mechanical state signature.

Failure grouping operates on content-addressed `ErrorInstanceMembershipV1` rows binding `(episode, error_instance_id)` memberships rather than one episode-level onset. One episode may contribute
several error instances and several groups. Primary keys are mechanical: task
family, error-instance signature, progress/precondition state, lifecycle/
resolution state, and terminal-footprint class. Model-generated mechanism prose
is not a primary grouping key. Failure groups aggregate recurrence, conflicting
evidence, task-family scope, applicability, non-applicability, repair templates,
and source-conditioned repair proposals for exact member states.

Success groups aggregate necessary workflows, useful exploration, self-recovery,
candidate inefficiencies, and regression guards.

Cross-outcome comparison is used to test hypotheses such as:

```text
successful trajectories transition phases after acquisition
failed trajectories continue searching after acquisition
```

The group pass cannot rewrite local results, hide disagreement, or convert
absence of a claim into missing data.

## 7. C — Component / Capability Attribution

Before gold annotation, freeze a finite behavior-capability taxonomy:

```text
INTERFACE_AND_PROTOCOL
OBSERVATION_AND_STATE_GROUNDING
TASK_DECOMPOSITION_AND_PLANNING
SEARCH_AND_NAVIGATION
OBJECT_IDENTIFICATION
OBJECT_ACQUISITION
PRECONDITION_AND_ACTION_SEQUENCING
STATE_TRANSFORMATION_AND_MANIPULATION
GOAL_AND_PHASE_PROGRESS_TRACKING
RECOVERY_AND_BACKTRACKING
TERMINATION_AND_SUCCESS_RECOGNITION
BUDGET_AND_RESOURCE_MANAGEMENT
UNKNOWN_OR_CROSS_COMPONENT
```

A controlled C-stage semantic call produces
`ANALYZER_COMPONENT_ATTRIBUTION_V1`: one principal component, zero or more
secondary components, evidence references, uncertainty, and raw/validated
response hashes. Deterministic profile code only aggregates validated
attributions and zero-claim denominators; it never infers components from prose.
C produces both deficits and strengths:

```text
principal_deficit
secondary_deficits[]
demonstrated_strengths[]
fragile_strengths[]
self_recovery_capabilities[]
```

C does not choose the next training method.

## 8. P — Policy Behavior Profile

P creates:

```text
POLICY_BEHAVIOR_PROFILE_V1
├── FAILURE_BURDEN_PROFILE
├── SUCCESS_QUALITY_PROFILE
├── REGRESSION_RISK_PROFILE
└── OPTIMIZATION_OPPORTUNITY_PROFILE
```

It reports component burden, family coverage, recurrence stability,
counterexample density, repairability, uncertainty, success-quality burden,
regression guards, and historical NO-GO overlap.

It may produce a candidate bottleneck list, but it cannot select the principal
bottleneck, the single primary change, the experiment budget, the training
method, or a promotion decision. Those belong to the Training Researcher.

## 9. X — Independent Cross-check

X is a sidecar and never silently rewrites an earlier result. It consumes the
original claim and frozen evidence, then emits one of:

```text
ACCEPT
DOWNGRADE_SCOPE
REQUIRE_ABSTENTION
REJECT
```

It records support, contradiction, missing evidence, alternative explanations,
and whether support came from the current trajectory or historical Memory.

For success optimization, X must actively search for evidence that an apparently
redundant step provided information, established a precondition, or enabled later
recovery.

## 10. Deterministic projection outputs

The projector emits four output families:

```text
FAILURE_REPAIR_CANDIDATE
SUCCESS_EFFICIENCY_CANDIDATE
SUCCESS_WORKFLOW_REFERENCE
REGRESSION_GUARD
```

It may resolve evidence IDs, bind source states, validate exact menu membership,
validate option length and termination, bind policy/Memory/Analyzer identities,
and apply X dispositions.

It cannot invent actions, alter executable bytes, alter semantic rank,
convert abstention into a candidate, or claim Benefit/Harm. Higher-level G output
may contain source-conditioned K=1/ABSTAIN repairs bound to exact member states
and menus. C/P/X may rank, downgrade, or reject them but cannot rewrite their
bytes. An abstract template without a source-conditioned executable repair
projects to ABSTAIN. No unequal extra proposal call is added only to A2/A3.

## 11. A0–A3 main repair-discovery experiment remains failure-only

| Condition | Local stage | Higher-level stage | Historical experience |
|---|---|---|---|
| A0 | one-shot, one explanation | none | none |
| A1 | up to three competing hypotheses | none | none |
| A2 | exact frozen A1 local results | G→C/P→X | none |
| A3 | exact frozen A1 local results | same G→C/P→X contract | one frozen Analyzer Memory packet |

Therefore:

```text
A2 − A1 = incremental value of hierarchy
A3 − A2 = incremental value of governed historical experience
```

The main A0–A3 table is not mixed with success optimization because candidate
semantics, effect labels, and primary endpoints differ.

### 11.1 Common repair budget

Frozen across A0–A3:

```text
same strong model/provider
same common evidence
same eligible source states
same maximum hypotheses
same maximum candidate count
same maximum executable action count
same total environment-step budget
same number of allowed new observations
same F0/F1 runner
same outcome definition
```

Only executable action/option bytes enter F1. Analyzer prose, diagnosis,
confidence, Memory explanation, and natural-language guidance are never passed
to the Task Policy as part of F1.

Primitive actions and short options are stratified in all reports. Identical
source-state/action/termination candidates are deduplicated and share one
environment result.

## 12. Separate success-optimization pilot

A small pilot evaluates successful trajectories without diluting A0–A3:

```text
12 unique successful episodes
× best frozen Analyzer condition
× at most one success-efficiency candidate
```

Labels are:

```text
SUCCESS_PRESERVED_EFFICIENCY_GAIN
SUCCESS_PRESERVED_NO_MEANINGFUL_GAIN
SUCCESS_REGRESSION
SUCCESS_EFFECT_UNCERTAIN
```

A gain requires preserved task success plus a registered improvement in steps,
policy calls, tokens, latency, repeated/no-effect actions, or another frozen
cost measure. A success regression is reported as such and may also be mapped to
high-level Harm statistics while preserving its original label.

If the pilot cannot safely distinguish useful exploration from redundancy,
success analysis is retained only for workflow references and regression guards.

## 13. Repair Effect Decomposition

A0–A3 measures total intervention effect, not the internal causal mechanism of a
repair. A separate narrow experiment is therefore required for 8–12 distinct
verified Benefit candidates:

```text
D0 baseline continuation
D1 full registered repair
D2 tested-prefix interventions
D3 mechanically matched perturbation
D4 history-attenuated continuation
```

The experiment distinguishes:

```text
SPECIFIC_SINGLE_ACTION_EFFECT
MINIMAL_PREFIX_EFFECT  # only after every shorter prefix is definitively non-Benefit
COMPOSITIONAL_OPTION_EFFECT
HISTORY_CONTEXT_DEPENDENT
NONSPECIFIC_PERTURBATION_EFFECT
BUDGET_OR_EXTRA_OBSERVATION_CONFOUNDED
UNRESOLVED_MULTI_CHANNEL_EFFECT
```

These are operational mechanism labels, not a claim of fully identified natural
direct and indirect causal effects.

## 14. External strong-model trace and local supervision

Every formal external Analyzer and Researcher call is stored from the first
call. The project reuses existing trajectory, access, and provenance assets and
adds only a typed role trace:

```text
COGNITIVE_ROLE_TRACE_V1
```

It binds:

```text
role and analysis objective
round/policy/evidence cutoff
task/gamefile/access class
provider/model/version/request ID
prompt/schema/request/response hashes
raw response pointer
parse/refusal/infrastructure status
tokens/latency/cost
human accept/revise/reject/defer
revision diff and reason
cross-check disposition
downstream F0/F1 or optimization outcome
final supervision inclusion/exclusion
```

The raw external response is immutable. The primary local-training target is the
adjudicated structured analysis, with downstream environment outcomes retained
as a separate evidence layer.

Materializers create the already planned:

```text
LOCAL_ANALYZER_SUPERVISION_DATASET_V1
LOCAL_RESEARCHER_SUPERVISION_DATASET_V1
```

without copying trajectories into a second store or rebuilding task-access
governance.

## 15. Metric completeness and claim alignment

`ANALYZER_METRIC_TARGETED_HARDENING_V2` and
`ANALYZER_METRIC_REGISTRY_V1` are the only metric source of truth.

The formal C1 display contains:

```text
EVRY_reg and EVRY_avail
failure-cohort Harm
protected-baseline-cohort Harm
ProposalCoverage
Verified Benefit Precision (VBP)
formal verifier environment steps per repaired unique U_reg unit
EVRY@B
```

All rates report raw numerator/denominator, task/gamefile-clustered uncertainty,
and infrastructure/method-failure counts. No weighted composite is allowed.
Final paper authority remains π2 versus π1 task success with Memory OFF and
Harness OFF.

The D0–D4 cohort reports a secondary `specificity-confirmed repair yield`
(internal compatibility ID `CSVRY`). D2 says `shortest tested sufficient prefix`
unless every shorter prefix is definitively non-Benefit. The trace is
`RepairEffectDecompositionTraceV1`; no full causal-mediation claim is made.

## 16. Interfaces with downstream roles

### Human Training Researcher

Receives the frozen candidate pool, behavior profile, evidence/counterevidence,
coverage, cost, historical NO-GO, and verifier outcomes. It selects a bounded
verification/training portfolio but cannot alter Analyzer outputs.

### Environment Verifier

Receives only registered executable candidates or success-optimization
interventions. It is the sole Benefit/Harm/Neutral/Uncertain authority.

### Failure Experience Library

Receives semantic hypotheses and workflow references as candidate records. It
requires deterministic governance and environment effect evidence before any
promotion.

### Verified Training Evidence Builder

Consumes only environment-labeled outcomes with exact policy/source identities.
Analyzer confidence alone never creates a label.

## 17. Failure handling

Fail closed on:

- noncanonical evidence;
- policy or access mismatch;
- Memory outside A3;
- unsupported evidence reference;
- benefit/harm language in Analyzer outputs;
- hidden-state or unavailable-tool repairs;
- action absent from the live source menu;
- option longer than the registered limit;
- success candidate without preserved-success verification;
- unapproved budget thresholds;
- selective deletion of abstention, invalid, Harm, Neutral, Uncertain, or
  infrastructure outcomes;
- external trace lacking raw response/provenance binding.

All raw responses and rejected outputs are preserved.

## 18. GO / NO-GO gates

### Localization and grounding gate

Proceed only if evidence citation precision, unsupported-fact rate, localization,
counterevidence handling, candidate validity, and calibrated abstention satisfy
the frozen pilot thresholds.

### Hierarchy-value gate

Support hierarchy only if A2 improves paired Benefit yield per eligible state or
environment calls per Benefit over A1, not merely prose completeness.

### Historical-experience gate

Support historical experience only if A3 improves downstream verified outcomes
over A2 under reported token/cost overhead.

### Success-quality gate

Support success optimization only if success is preserved and efficiency gains
are verified with low regression.

### Mechanism gate

Only use single-action language when decomposition supports a specific action or
minimal prefix. Otherwise report a compositional, context-dependent, nonspecific,
or unresolved intervention effect.

## 19. Infrastructure completion and runtime handoff

Tasks 1–16 close deterministic scientific infrastructure only. Their completion
status is `ANALYZER_DETERMINISTIC_SCIENTIFIC_INFRASTRUCTURE_CODE_APPROVED`.
Strong-model activation is governed separately by
`ANALYZER_V2_STRONG_MODEL_RUNTIME_ACTIVATION_V1`.

## 20. Deferred work

Not authorized here:

```text
formal model calls
formal environment execution
local Analyzer as primary
Analyzer self-training
automatic Research Planner control
π2 training
π2→π3 loop
unified Policy/Analyzer/Researcher checkpoint
merge into main
```


## Metric targeted hardening V2

`ANALYZER_METRIC_TARGETED_HARDENING_V2` is normative for the formal repair
comparison. A0–A3 share one preregistered exact-state universe `U_reg`; the
formal candidate budget is K=1 or ABSTAIN. EVRY remains the C1 primary endpoint,
but final paper authority remains π2-vs-π1 task success with Memory OFF and
Harness OFF. Strong Harm claims require the separately preregistered protected
baseline cohort. Verification cost is measured primarily in formal verifier
environment steps per repaired unique unit. Specificity-confirmed D0–D4 results
are secondary and never gate an otherwise formal Benefit from training-data
consideration.
