# P1–P4 Reduced Single-Round Distillation Pilot V1

## 1. Approval and status

Design approval:

`DESIGN_APPROVED_P1_P4_REDUCED_SINGLE_ROUND_DISTILLATION_PILOT_V1_Q2_ONLY_BAD_PRIMARY_MIX_SECONDARY`

Parent research protocol:

`Phase-Critical Harness-Guided Self-Improvement v3.3`

Current approved engineering base:

- repository main:
  `39ee3d78246239aac3844075c2ece7c3e94ec97d`;
- Runtime Core:
  frozen `RAW_WITH_MENU_V1`;
- evaluator:
  E1 ALFWorld evaluator V1;
- real integrated smoke:
  job `131758`;
- smoke application audit:
  three task attempts, three scientific cell locks,
  three published bundles, three terminal receipts,
  no `PUBLICATION_PENDING`, and no staging residue.

This document approves research design only.

It does not approve:

- implementation;
- external-model calls;
- π0 DEV rollout;
- model training;
- SELECT evaluation;
- confirmatory execution.

## 2. Research question

Can environment-replay-validated correction data proposed by a
strong offline model improve a local raw policy under Harness-OFF
evaluation?

A secondary question is:

Under an equal total loss-token budget, what performance–regression
trade-off is obtained by combining the same class of correction data
with π0-success-episode rehearsal data?

## 3. Pilot scope

The pilot consists of:

1. task-level access governance;
2. π0 DEV rollout;
3. strong-model-first offline diagnosis and candidate generation;
4. exact-state Q2 environment replay validation;
5. deterministic filtering and deduplication;
6. correction-only SFT;
7. correction-plus-success-rehearsal SFT;
8. Harness-OFF SELECT evaluation.

The pilot does not implement or claim:

- a formal Phase-Critical runtime intervention;
- Q3 critical-event verification;
- Q4 Benefit/Harm labels;
- causal first-critical-error identification;
- audited RL;
- Memory beyond M0;
- a cross-round Research Planner;
- final confirmatory generalization.

## 4. Permitted claim

If the primary condition passes the frozen SELECT gate, the pilot may
claim:

> Environment-replay-validated correction data proposed from real π0
> DEV failures produced a developmental Harness-OFF improvement over
> π0 under the frozen SELECT protocol.

The secondary condition may support only:

> Under an equal total loss-token budget, a correction-plus-success
> rehearsal recipe exhibited a measured performance–regression
> trade-off relative to correction-only training and π0.

The pilot may not claim:

- that the teacher identified the true causal root cause;
- that the teacher's first critical step is causally validated;
- that rehearsal has an isolated causal effect;
- that critical-event credit assignment is solved;
- that the result generalizes to an unexposed confirmatory test set.

## 5. System roles

### 5.1 π0 task policy

π0 is fixed as:

- Qwen2.5-3B-Instruct;
- frozen model revision;
- no project LoRA;
- `RAW_WITH_MENU_V1`;
- complete current admissible-command list;
- original environment order;
- Harness OFF;
- historical controllers OFF;
- `MEMORY_M0_V1`;
- 60 policy attempts;
- 30 environment steps;
- three consecutive non-executed attempts;
- maximum 256 Unicode code points per parsed action.

### 5.2 Factual evidence layer

The factual layer records only programmatically observable evidence:

- task and access identity;
- public task goal;
- current observation;
- complete admissible menu;
- raw model response;
- strict-parser status;
- exact menu membership;
- action submitted to the environment;
- public environment result;
- score, done and won;
- BudgetState;
- termination reason;
- trace, transition and artifact identities;
- infrastructure and publication status.

It may emit mechanical facts such as:

- parser failure;
- action not admissible;
- no environment transition;
- environment-step exhaustion;
- policy-attempt exhaustion;
- environment termination;
- infrastructure error.

It does not assign a complete semantic failure taxonomy.

### 5.3 Primary strong model

One exact provider, model version and request configuration is frozen in
`TeacherRuntimeManifestV1` before the first trajectory is sent.

The primary strong model may:

- diagnose one DEV failure;
- propose one failure type;
- propose one first critical step;
- propose one critical-state summary;
- propose one root cause;
- propose one corrected action;
- propose one recovery plan of at most four actions;
- propose one Harness or diagnostic hypothesis;
- perform cross-case descriptive synthesis.

The primary strong model is not:

- an online ALFWorld policy;
- an environment truth source;
- a Benefit/Harm labeler;
- a SELECT or TEST evaluator;
- a training-set acceptance authority.

### 5.4 Secondary provider audit

A second independently frozen provider/model performs a read-only audit
on a preregistered subset.

It:

- receives the original factual package;
- does not see the primary provider output;
- does not affect candidate acceptance;
- does not contribute training samples;
- reports diagnosis and candidate agreement/disagreement only.

### 5.5 Deterministic validation layer

The validation layer controls:

- schema compliance;
- task/access permissions;
- privilege and leakage checks;
- exact decision-state reconstruction;
- exact admissibility;
- environment replay;
- recovery-plan replay;
- budget accounting;
- deduplication;
- accepted/rejected provenance.

### 5.6 Human audit

Human review may:

- confirm a candidate;
- reject a candidate;
- flag ambiguity;
- identify a protocol defect.

Human review may not silently rewrite a teacher candidate.

Any human-modified training sample must use a separate provenance class
and is excluded from the primary teacher-data pilot unless separately
approved.

## 6. Data governance

### 6.1 Historical access audit

Before task assignment, every candidate task/gamefile receives one or
more historical-access flags:

- `NO_KNOWN_PRIOR_ACCESS`;
- `ACCESS_HISTORY_INCOMPLETE`;
- `AGGREGATE_ONLY`;
- `EXECUTED_NOT_INSPECTED`;
- `TRAJECTORY_INSPECTED`;
- `USED_FOR_METHOD_DESIGN`;
- `SENT_TO_EXTERNAL_MODEL`.

`NO_KNOWN_PRIOR_ACCESS` means that the audited project records contain
no known prior-access evidence. It is not proof that no access ever
occurred outside those records.

`ACCESS_HISTORY_INCOMPLETE` is required whenever the available records
cannot support a complete access determination. A task/gamefile with
this flag is ineligible for `CONFIRMATORY_SEALED`.

The audit records:

- task ID;
- gamefile identity;
- original dataset split;
- first known access date;
- access evidence;
- access flags;
- final access class.

### 6.2 Distillation access classes

`DISTILLATION_SPLIT_AND_ACCESS_V1` defines:

#### `DEV_VISIBLE`

Permitted:

- full trajectory inspection;
- strong-model calls;
- candidate generation;
- environment validation;
- training-data construction.

#### `SELECT_SUMMARY_ONLY`

Permitted:

- frozen Harness-OFF evaluation;
- preregistered aggregate and task-level metrics;
- model/recipe selection under this design.

Prohibited:

- teacher access;
- training;
- detailed failure-driven redesign during this pilot.

#### `CONFIRMATORY_SEALED`

Permitted only after a later method freeze and separate approval.

#### `HISTORICALLY_EXPOSED`

May be used for development or historical reporting according to its
recorded permissions, but cannot be silently presented as sealed test
evidence.

The current strict valid-unseen 134-task manifest is not automatically
classified as `CONFIRMATORY_SEALED`.

### 6.3 Task-level isolation

All seeds, trajectories, states, teacher calls, replay branches and SFT
samples from one task/gamefile remain in one access class.

State-level random splitting is prohibited.

## 7. Required manifests

### 7.1 `TaskAccessManifestV1`

Each row contains:

- schema ID/version;
- task ID;
- gamefile path and hashes;
- dataset split;
- task type;
- historical-access flags;
- access class;
- teacher-call permission;
- training permission;
- SELECT permission;
- confirmatory permission;
- provenance sources.

### 7.2 `PolicyConditionManifestV1`

Each policy condition contains:

- `policy_condition_id`;
- base model repository and revision;
- adapter/checkpoint path and content identity;
- training method;
- training run/config hash;
- tokenizer identity;
- chat-template identity;
- served model name;
- policy version;
- Memory version;
- Runtime Core identity;
- evaluator identity.

A π1 adapter or checkpoint must not be served under the frozen π0 model
identity.

### 7.3 `ConditionRunScheduleV1`

The schedule binds:

- task-access manifest hash;
- policy-condition manifest hash;
- evaluation seed schedule;
- task/replicate cells;
- output namespace;
- run schedule hash.

### 7.4 `TeacherRuntimeManifestV1`

The Python/schema type name is `TeacherRuntimeManifestV1`.

Serialized records use:

- `schema_id = "TEACHER_RUNTIME_MANIFEST_V1"`;
- `schema_version = 1`.

The teacher manifest freezes:

- provider;
- exact model/version;
- endpoint type;
- system/developer prompt hashes;
- response schema;
- tools disabled;
- web disabled;
- RAG disabled;
- temperature;
- top-p;
- maximum output tokens;
- number of candidates;
- schema retry count;
- timeout and transport retry policy;
- context limit;
- request/response hashing;
- external-call cost ceiling.

### 7.5 `DistillationDecisionStateV1`

A teacher-proposed critical state is represented by:

- source execution attempt ID;
- task/gamefile identity;
- source policy condition;
- critical model-call index;
- critical environment-step index;
- complete executed environment-action prefix;
- current observation and hash;
- current admissible menu and sequence hash;
- public goal and hash;
- M0 executed-transition state and hash;
- current interface feedback;
- complete BudgetState;
- remaining policy/environment budget;
- original prompt bytes and hash;
- source episode semantic hash;
- source attempt-bundle hash.

## 8. P1: π0 DEV rollout

P1 runs only tasks assigned to `DEV_VISIBLE`.

The rollout condition is:

`P4-R0-PI0`

Each failed scientific episode produces a factual package that references
the frozen evaluator artifacts:

- execution attempt ID;
- episode semantic SHA-256;
- attempt bundle SHA-256;
- scientific cell lock;
- terminal receipt;
- traces;
- public transitions;
- policy condition;
- task-access record.

Smoke-task artifacts are engineering evidence only unless their task
records are explicitly assigned to DEV.

## 9. P2: strong-model-first Distillation Harness

### 9.1 Per-case diagnosis

The teacher output uses hypothesis-marked fields:

- `teacher_proposed_failure_type`;
- `teacher_proposed_first_critical_step`;
- `teacher_proposed_critical_state_summary`;
- `teacher_proposed_critical_event`;
- `teacher_proposed_root_cause`;
- `evidence_step_indices`;
- `teacher_confidence`.

These are teacher hypotheses, not environment truth.

### 9.2 Candidate generation

For each failed episode:

- at most one critical state;
- at most one corrected action;
- at most one recovery plan;
- at most four recovery actions;
- no best-of-N;
- no post-validation repair loop;
- at most one schema-only formatting retry.

A rejected candidate remains rejected and is retained in the raw
candidate ledger.

### 9.3 Context-overflow contract

Silent input truncation is prohibited.

A trajectory that does not fit the frozen teacher context is assigned:

`REJECT_TEACHER_CONTEXT_OVERFLOW`.

V1 does not implement trajectory chunking, intermediate summarization or
multi-call synthesis for an overflowing per-case teacher input.

No episode-specific manual truncation is allowed.

### 9.4 Cross-case synthesis

The teacher receives structured DEV diagnosis records and may output:

- teacher-derived descriptive taxonomy;
- recurring critical-state patterns;
- recurring event/phase hypotheses;
- candidate Harness hypotheses;
- candidate data families;
- unresolved failure modes.

Cross-case synthesis is hypothesis generating only.

It cannot modify the runtime evaluator or Harness during this pilot.

### 9.5 Secondary-provider audit subset

Before inspecting primary-teacher outputs:

```text
audit_n =
min(
  total_failure_episodes,
  max(
    30,
    ceil(0.10 * total_failure_episodes)
  )
)
```

The subset is selected by a frozen deterministic algorithm stratified by:

- task family;
- mechanical failure/termination tag;
- trajectory-length quartile.

If fewer than 30 failures exist, all failures are audited.

## 10. P3: Q2 validation

### 10.1 Q0 schema gate

Checks:

- valid JSON;
- exact schema;
- required fields;
- field types;
- source episode identity;
- critical-step range.

### 10.2 Q1 access and grounding gate

Checks:

- source belongs to DEV;
- teacher call was permitted;
- no SELECT/TEST data;
- corrected action refers to the claimed source state;
- no hidden-state or answer-path fields;
- entities are grounded in online-visible evidence;
- provider/request provenance is complete.

### 10.3 Exact-state reconstruction

Q2 begins in a fresh environment process:

1. load the exact gamefile;
2. reset;
3. replay the source executed environment-action prefix;
4. compare every public transition;
5. rebuild non-executed policy-attempt budget and interface feedback;
6. reproduce M0;
7. verify observation, menu, prompt and BudgetState;
8. verify `DistillationDecisionStateV1`;
9. execute the proposed corrected action;
10. execute any recovery actions under the original remaining budget.

Any mismatch yields:

`REJECT_STATE_RECONSTRUCTION`.

### 10.4 Q2-A single-action acceptance

A single-action candidate requires:

- exact state reconstruction;
- corrected action is an exact current-menu member;
- environment step succeeds;
- no infrastructure error;
- submitted action is recorded;
- real next public state is recorded;
- no budget violation;
- no immediate terminal failure with `done == true` and `won == false`;
- mechanical contrast with the source π0 behavior under the rules below.

If the source π0 step called the environment, mechanical contrast
requires at least one of:

1. the teacher-corrected action differs from the original submitted
   environment action; or
2. the teacher branch public-transition tuple differs from the original
   branch public-transition tuple.

The public-transition tuple is exactly:

- next-observation SHA-256;
- next-menu sequence SHA-256;
- score;
- done;
- won.

If the source π0 step did not call the environment because of a parser
or exact-membership failure, no original environment transition exists.
The pairwise transition comparison is then not required, while every
other Q2-A condition remains mandatory.

A candidate with neither action nor transition contrast is rejected as:

`REJECT_NO_MECHANICAL_CONTRAST`.

An immediate terminal failure is rejected as:

`REJECT_IMMEDIATE_TERMINAL_FAILURE`.

### 10.5 Q2-R recovery acceptance

A recovery candidate requires:

- every action exact admissible in the state where it is executed;
- every next state produced by the real environment;
- no state-reconstruction mismatch;
- no repeated public-decision-state/action pair;
- total option cost within the original remaining budget;
- complete transition provenance.

The public decision-state hash is the canonical hash of:

- observation SHA-256;
- menu sequence SHA-256;
- M0 SHA-256;
- interface feedback;
- complete BudgetState.

If the recovery plan repeats an identical pair of:

`(public_decision_state_sha256, action)`

the entire recovery candidate is rejected as:

`REJECT_RECOVERY_PUBLIC_CYCLE`.

This rule is mechanical and makes no Q3 semantic-progress claim.

### 10.6 Q2 training acceptance

Primary training data may contain:

- accepted Q2-A single-action corrections;
- accepted Q2-R recovery state/action examples.

The accepted class is named:

`ENVIRONMENT_REPLAY_VALIDATED_CORRECTION`.

It must not be named:

- critical-event verified;
- causally beneficial;
- Benefit;
- audited advantage.

### 10.7 Q3 status

Q3 is:

`DEFERRED_PENDING_E3A_APPROVAL`.

No E3a event score is used as a training gate in this pilot.

### 10.8 Manual audit

Manual audit covers:

- all privilege violations;
- all reconstruction mismatches;
- all provider disagreements;
- at least 10% from each task family and acceptance/rejection class.

Manual review cannot convert a failed Q2 replay into an accepted teacher
sample.

## 11. Dataset construction

### 11.1 `D_Q2_BAD`

Contains only accepted environment-replay-validated state/action
examples.

The original π0 error is retained in provenance but is not a loss target.

A recovery trajectory is converted into separate real state/action SFT
examples after each actual environment transition.

### 11.2 `D_PI0_SUCCESS_REHEARSAL`

Contains only DEV π0 episodes with terminal success.

Each example:

- uses the original online-visible prompt;
- targets the actual exact action sent to the environment;
- includes no future result;
- retains mechanical behavior tags;
- is identified as a π0-success-episode rehearsal sample;
- is not called an optimal or expert trajectory.

### 11.3 Deduplication and distribution controls

The raw candidate ledger is immutable and complete.

Training-data construction performs:

1. exact decision-state/action deduplication;
2. same-task prefix and near-state clustering;
3. per-episode sample caps;
4. per-task sample caps;
5. task-family distribution reporting;
6. joint deduplication across correction and rehearsal pools.

The primary exact key includes:

- source policy version;
- task/gamefile identity;
- decision-state hash;
- corrected/executed action.

## 12. P4 training conditions

### 12.1 Condition names

#### `P4-R0-PI0`

No training.

#### `P4-R1-Q2-BAD`

Primary condition.

Training data:

`D_Q2_BAD`

#### `P4-R2-Q2-MIX`

Secondary recipe condition.

Training data:

- 50% target loss tokens from `D_Q2_BAD`;
- 50% target loss tokens from `D_PI0_SUCCESS_REHEARSAL`.

### 12.2 Fairness controls

R1 and R2 use:

- the same base checkpoint;
- the same trainable-parameter method;
- the same optimizer;
- the same learning rate;
- the same total target loss-token budget;
- the same effective batch size;
- the same update/checkpoint rule;
- the same training seed schedule;
- the same model-selection rule;
- the same evaluation protocol.

MIX has a smaller correction dose than BAD under equal total token
budget.

Therefore R1 versus R2 is explicitly a fixed-budget recipe comparison,
not an isolated rehearsal-effect estimate.

### 12.3 Training seeds

All preregistered training seeds enter the aggregate result.

Selecting the best training seed is prohibited.

Technical failures are handled according to a frozen incident policy and
must not be selectively excluded.

## 13. Harness-OFF SELECT evaluation

### 13.1 Conditions

Evaluate:

- `P4-R0-PI0`;
- `P4-R1-Q2-BAD`;
- `P4-R2-Q2-MIX`.

All conditions use identical:

- SELECT task manifest;
- evaluation seed schedule;
- complete menu;
- raw policy prompt;
- M0;
- Runtime Core;
- 30-step environment budget;
- evaluator semantics;
- artifact protocol.

Teacher models and runtime Harness components are absent.

### 13.2 Primary and secondary hypotheses

Primary:

`P4-R1-Q2-BAD` versus `P4-R0-PI0`

Secondary:

`P4-R2-Q2-MIX` versus `P4-R0-PI0`

R2 cannot replace the primary hypothesis after SELECT results are seen.

### 13.3 Frozen sampling rule

The complete training-seed and evaluation-seed schedules are frozen
before SELECT execution.

No seed is added in response to an interim confidence interval.

If the final interval crosses zero, the result is:

`INCONCLUSIVE`.

### 13.4 Primary endpoint

Primary endpoint:

task-level paired success effect.

For each task:

1. aggregate all frozen evaluation seeds within each training seed;
2. aggregate all frozen training seeds using the preregistered mean;
3. compare paired task outcomes;
4. compute a task-level paired bootstrap interval.

### 13.5 Secondary endpoints

Report:

- π0-success-cell retention;
- task-family success;
- protocol-failure rate;
- inadmissible-action rate;
- no-effect and repeated behavior;
- mean environment steps;
- policy attempts;
- latency;
- training and API cost;
- infrastructure and publication failures.

### 13.6 Primary GO rule

The primary condition reaches developmental GO only if all hold:

1. paired SELECT task-level success effect is positive;
2. 95% paired task-bootstrap lower bound is greater than zero;
3. at least 90% of π0-success task-seed cells are retained;
4. protocol/inadmissible failure does not increase by more than two
   absolute percentage points;
5. improvement appears in at least two task families;
6. no unresolved infrastructure or artifact-publication failure exists.

Otherwise the result is:

- `NO_GO`, if clearly below a required boundary; or
- `INCONCLUSIVE`, if statistical evidence is insufficient.

### 13.7 Secondary condition interpretation

R2 is reported as a secondary fixed-budget recipe analysis.

It cannot independently establish the primary pilot claim.

If both R1 and R2 perform well, promotion of a final π1 requires a
separate, preregistered selection decision after the primary pilot
result has been audited.

## 14. Outputs

The design requires the implementation plan to produce:

- historical access audit;
- task-access manifests and hashes;
- policy-condition manifests and hashes;
- condition schedules and hashes;
- factual failure packages;
- primary teacher requests/responses;
- secondary-provider audit records;
- cross-case synthesis;
- raw candidate ledger;
- accepted/rejected candidate ledger;
- decision-state records;
- replay evidence;
- Q2 BAD dataset manifest;
- π0-success rehearsal dataset manifest;
- training configs and logs;
- checkpoint/adapter identities;
- Harness-OFF SELECT artifacts;
- task-level metrics;
- regression report;
- cost report;
- final GO/NO-GO/INCONCLUSIVE audit.

## 15. Explicit prohibitions

Before a later design approval, this pilot must not:

- send SELECT or TEST data to a teacher;
- silently truncate teacher input;
- use best-of-N;
- repeatedly ask a teacher to repair rejected candidates;
- modify runtime Harness behavior based on teacher synthesis;
- use Q3/E3a claims;
- create Q4 Benefit/Harm labels;
- perform RL;
- introduce Memory beyond M0;
- run a Research Planner;
- inspect a sealed confirmatory task;
- select the best training seed;
- adaptively add SELECT seeds;
- rename a π1 condition as π0;
- claim final generalization from SELECT.

## 16. Approval gates after this design

After this design document is frozen:

1. the written design must be reviewed;
2. a file-level implementation plan must be written;
3. implementation requires separate code approval;
4. π0 DEV rollout requires separate execution approval;
5. external teacher calls require separate execution approval;
6. training requires separate execution approval;
7. SELECT evaluation requires separate execution approval;
8. all results require result-audit approval.
