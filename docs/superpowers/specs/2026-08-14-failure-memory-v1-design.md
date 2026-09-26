# Failure Memory V1 Design

## 1. Approval and status

Design status:

`DESIGN_APPROVED_FAILURE_MEMORY_V1`

Primary research strategy:

`EXTERNAL_PROCEDURAL_FAILURE_MEMORY_FIRST`

Primary policy state:

`FROZEN`

Required V1 improvement type:

`SYSTEM_LEVEL_MEMORY_ASSISTED_IMPROVEMENT`

Parametric policy internalization:

`DEFERRED_OPTIONAL_EXTENSION`

Repository design base:

`b30e188f70890ff808a874c05c0ddfcc98973a7c`

Final human approval:

`DESIGN_APPROVED_FAILURE_MEMORY_V1`

Approval date:

`2026-08-15`

Approved final-hardened design basis:

`6b84488ca08f730f11427dcd0f1611ad6408ceb7`

Authorization boundary:

```text
IMPLEMENTATION_PLAN = AUTHORIZED

MEMORY_BUILDER_IMPLEMENTATION = NOT_AUTHORIZED
MEMORY_RECORD_MATERIALIZATION = NOT_AUTHORIZED
MEMORY_ASSISTED_EXECUTION = NOT_AUTHORIZED
SCIENTIFIC_EXECUTION = NOT_AUTHORIZED
```

Historical Round-1 status:

```text
Round-1 execution                       = COMPLETE
Harness-OFF policy-improvement result  = COMPLETE_NO_GO
Canonical evidence/provenance closure  = IN_PROGRESS
Failure Memory                         = HOLD
```

This complete written design received explicit final human approval on 2026-08-15 under the decision token `DESIGN_APPROVED_FAILURE_MEMORY_V1`.

It does not approve:

- implementation;
- a Memory builder;
- Memory-record materialization;
- external model calls;
- retrieval-model download;
- ALFWorld execution;
- Memory-assisted policy execution;
- task-pool reveal;
- formal benchmark execution;
- policy training;
- parametric policy internalization;
- a Research Planner;
- autonomous live-system mutation.

The approved design may now be integrated into its parent documentation
branch and used as the authority for an implementation plan.

This approval authorizes implementation planning only. It does not
authorize implementation or scientific execution.

---

## 2. Primary research question

The primary question is:

> Can a frozen task policy improve as an agent system by accumulating,
> validating, retrieving and reusing provenance-grounded procedural
> experience from its own failures?

The primary V1 claim concerns:

```text
frozen policy
+
persistent external Failure Memory
+
controlled retrieval
+
versioned snapshots
```

It does not require policy-weight updates.

The design separates:

```text
system-level improvement
```

from:

```text
parametric policy improvement
```

Failure Memory V1 succeeds or fails on the former.

Parametric internalization is retained only as an optional later
extension.

---

## 3. Scientific claim boundary

Failure Memory V1 may support only claims established by the frozen
experiments.

Possible system-level claims include:

- a frozen policy benefits from bounded raw episodic experience;
- structured descriptive procedural experience adds value beyond a
  matched raw episodic view;
- gated recovery guidance adds value beyond descriptive procedural
  Memory;
- validated Failure Memory reduces repeated failures or improves task
  success;
- external Memory can accumulate across controlled rounds without
  uncontrolled negative transfer;
- versioned promotion, quarantine and rollback prevent harmful Memory
  from silently dominating later execution.

Failure Memory V1 may not claim:

- policy-weight improvement;
- parametric self-improvement;
- complete causal identification of a failure mechanism;
- that semantic Analyzer output is environment truth;
- that one positive source-state replay proves cross-task transfer;
- that historically exposed `valid_unseen` is a fresh confirmatory set;
- that `valid_seen` establishes OOD generalization;
- that mechanism-metric improvement equals task-performance
  improvement;
- that retrieved Memory was internally “understood” by the policy;
- that the Research Planner has been implemented or validated.

---

## 4. Primary scientific stages

Failure Memory V1 has four required stages.

### 4.1 Stage 0 — Memory quality, safety and retrieval development

Stage 0 establishes:

- source provenance;
- sequence fidelity;
- fact/hypothesis separation;
- Policy-view safety;
- access isolation;
- retrieval reproducibility;
- retrieval candidate selection;
- threshold selection;
- abstention behavior;
- prompt-interface perturbation;
- projection token and latency costs.

Stage 0 does not establish end-to-end task improvement.

### 4.2 Stage 1 — Frozen-policy Memory effect validation

Stage 1 contains:

1. single-record source-state paired replay;
2. train-only FM0–FM3 system-development evaluation.

It asks whether Failure Memory content has observable causal and
system-level value while policy weights remain frozen.

### 4.3 Stage 2 — Controlled multi-round external Memory improvement

Stage 2 keeps the policy frozen and evolves only the versioned external
Memory system:

```text
snapshot S0
→ new failure evidence
→ candidate Memory
→ verification
→ snapshot S1
→ new failure evidence
→ ...
```

It tests whether the agent system improves through accumulated and
curated failure experience without live condition drift.

### 4.4 Stage 3 — Frozen formal ID/OOD evaluation

After the complete method is frozen once, the same:

- policy;
- Memory snapshot;
- retrieval configuration;
- thresholds;
- projection schemas;
- FM0–FM3 definitions;
- runtime;
- budgets;
- evaluation implementation;

is used for:

```text
valid_seen  = project-held-out ID confirmation
valid_unseen = standard OOD benchmark, historically exposed
```

No method change is permitted between the two evaluation splits.

Result unblinding and method-level interpretation occur only after both
split executions are complete.

---

## 5. Out-of-scope primary requirement: policy internalization

The following path is not required for Failure Memory V1:

```text
validated Memory
→ training signal
→ policy training
→ Memory-OFF + Harness-OFF
```

It is preserved as:

`OPTIONAL_PARAMETRIC_INTERNALIZATION_EXTENSION`

Its future minimum boundary remains:

- only authorized Memory/effect evidence may become a training source;
- training inputs must remain policy-visible;
- Analyzer rationale must not be treated as factual truth;
- deployment must not require persistent Memory text;
- final authority must be Memory-OFF and Harness-OFF evaluation.

No implementation work for this extension is approved by this design.

---

## 6. System architecture

The V1 data flow is:

```text
immutable raw evidence
        ↓
SEQUENCE_FAILURE_EXPERIENCE_V1
        ↓
PROCEDURAL_FAILURE_MEMORY_RECORD_V1
        ↓
semantic annotations and typed relations
        ↓
descriptive and prescriptive eligibility gates
        ↓
MEMORY_RETRIEVAL_KEY_V1
        ↓
pre-materialized Policy views
        ↓
immutable Memory-library snapshot
        ↓
gated retrieval or direct frozen projection
        ↓
frozen task policy
```

The architecture separates:

- what actually happened;
- what sequence is relevant;
- what the Analyzer hypothesizes;
- what has been verified;
- what may be retrieved;
- what the Policy may see;
- what the Policy actually saw;
- what belongs to the active snapshot.

---

## 7. Raw Evidence Layer

The Raw Evidence Layer is the factual source of truth.

It references existing immutable or sealed evidence, including:

- task and gamefile identity;
- policy condition;
- policy calls;
- raw responses;
- strict parsing;
- attempted actions;
- executed environment actions;
- observations;
- complete admissible menus;
- interface feedback;
- score, done and won;
- BudgetState evolution;
- termination;
- provenance hashes;
- source bundle identity.

Rules:

```text
append only
no silent rewrite
no semantic promotion
no replacement by summary
```

A higher-level Memory record may reference raw evidence.

It may not replace it.

---

## 8. Sequence Failure Experience

One factual reconstructed experience uses:

`SEQUENCE_FAILURE_EXPERIENCE_V1`

It answers only:

> What happened in the registered failure sequence?

Required sections are:

### 8.1 Identity and source

- experience ID;
- source round;
- source condition;
- source task/gamefile;
- source bundle;
- source attempt;
- exact policy-call range;
- exact transition range;
- source-file hashes.

### 8.2 Relevant start

- registered decision region;
- required preceding calls;
- required preceding executed transitions;
- starting public state;
- starting budget and interface-feedback state.

### 8.3 Observed sequence

- every relevant policy attempt;
- raw or parsed action status;
- interface feedback;
- environment-executed actions;
- public observations;
- menu changes;
- state-change evidence;
- nonexecuted failures;
- repeated or oscillating behavior.

### 8.4 Failure development

- factual failure onset;
- continuation of the observed branch;
- accumulated observable consequences;
- terminal outcome;
- factual recovery when one was actually observed.

### 8.5 Source binding

Every factual element must resolve to source evidence.

This record must not contain untyped claims such as:

- “the model was confused”;
- “the true mechanism was progress blindness”;
- “the policy should have executed action X.”

Those belong to later semantic or recovery layers.

---

## 9. Procedural Failure Memory Record

One reusable Memory uses:

`PROCEDURAL_FAILURE_MEMORY_RECORD_V1`

It contains seven logical groups.

### 9.1 Provenance

- Memory ID;
- record version;
- source-experience IDs;
- source hashes;
- creation event;
- creator role;
- created snapshot candidate.

### 9.2 Factual-sequence binding

- relevant factual sequence;
- exact source pointers;
- fact authority;
- unresolved factual gaps.

### 9.3 Applicability boundary

- activation condition;
- continuation condition;
- revalidation condition;
- release condition;
- termination condition;
- non-applicability condition;
- policy-visible state-change trigger.

Release is a first-class boundary.

A Memory must say not only when it may begin to apply, but also when it
must stop influencing the current decision.

### 9.4 Semantic annotations

- candidate mechanism;
- capability component;
- task-family hypothesis;
- critical region;
- supporting evidence;
- counterevidence;
- alternative explanation;
- semantic confidence;
- origin Analyzer identity.

All semantic annotations remain:

`SEMANTIC_HYPOTHESIS`

They do not become environment truth by entering Memory.

Historical hierarchical authority remains:

```text
Levels 1–4 = semantic annotation inputs
Level 5    = REJECTED
Level 6    = INCOMPLETE
```

### 9.5 Recovery evidence

- proposed recovery;
- recovery origin;
- executability status;
- Policy-visibility status;
- paired-effect observations;
- known harm;
- unresolved ambiguity.

### 9.6 Effect and access state

The record stores independent dimensions:

```text
source_integrity
authority_type
descriptive_eligibility
repair_validity
effect_status
effect_evidence_scope
access_scope
lifecycle_status
evaluation_contamination_status
```

They must not be collapsed into one status field.

### 9.7 Relations and versions

Typed relations may include:

```text
DERIVED_FROM
SUPPORTS
CONTRADICTS
SIMILAR_TO
REFINES
SUPERSEDES
APPLIES_TO
COUNTEREXAMPLE_OF
VERIFIED_BY
HARMFUL_UNDER
```

Every relation also records:

- relation origin;
- authority type;
- source IDs;
- verification state;
- created version.

Semantic edges are not promoted to deterministic facts.

### 9.8 Procedural completeness gate

A reusable record must pass:

`PROCEDURAL_COMPLETENESS_GATE_V1`

The gate prevents a multi-step failure experience from collapsing into:

```text
bad action
→ corrected action
```

A record must preserve a registered temporal failure process.

At minimum, the canonical record must establish:

- a nonempty source-sequence binding;
- a registered relevant start;
- ordered attempts, transitions or nonexecuted policy events;
- observable feedback, state-change evidence or explicit
  no-state-change/repetition evidence;
- development of the wrong, stale or ineffective branch;
- an observable consequence, termination or registered unresolved
  outcome;
- an activation boundary;
- a release or termination boundary;
- an explicit non-applicability disposition.

The non-applicability disposition is either:

- one or more registered non-applicability conditions; or
- an explicit unresolved/none-identified status that blocks
  overgeneralized promotion.

A revalidation boundary is required whenever later public feedback or a
visible state change may alter applicability.

Recovery guidance must not be the only substantive Policy-visible
content.

A record fails the gate when its substantive meaning can be represented
only as:

```text
do not execute X
execute Y instead
```

without preserving the relevant process, feedback, state boundary and
applicability/release conditions.

Failure disposition:

```text
PROCEDURAL_COMPLETENESS_NOT_ESTABLISHED
→ STAGING_OR_OFFLINE_ONLY
→ NOT_RETRIEVAL_ELIGIBLE
```

The gate evaluates procedural completeness.

It does not promote semantic hypotheses to factual authority.

---

## 10. Retrieval Key and Policy Views

A canonical Memory record produces separate frozen artifacts.

```text
PROCEDURAL_FAILURE_MEMORY_RECORD_V1
        ├── MEMORY_RETRIEVAL_KEY_V1
        ├── FM1_MATCHED_RAW_EPISODIC_VIEW_V1
        ├── FM2_DESCRIPTIVE_POLICY_PROJECTION_V1
        └── FM3_PRESCRIPTIVE_POLICY_PROJECTION_V1
```

Retrieval representation and Policy-visible representation are different
objects.

### 10.1 Retrieval Key

`MEMORY_RETRIEVAL_KEY_V1` is used only for candidate retrieval.

It may contain:

- validated access scope;
- lifecycle state;
- required or forbidden feedback codes;
- recent-action repetition signature;
- recent nonexecuted-attempt signature;
- visible state-change signature;
- required visible markers;
- forbidden visible markers;
- frozen semantic retrieval text.

It must not contain:

- recovery procedure;
- effect status;
- promotion status;
- Benefit/Harm label;
- source task ID as a semantic shortcut;
- exact current action;
- oracle path.

The same retrieval key and ranked record identity are used across FM1,
FM2 and FM3.

Therefore FM2 versus FM1 tests Policy-visible representation under
matched retrieval, not end-to-end retriever superiority.

### 10.2 FM1 matched raw view

FM1 uses a deterministic bounded raw/sequence view.

Its construction freezes:

- source experience ID;
- exact call range;
- exact transition range;
- window-expansion rule;
- Policy-visible sanitization rule;
- token ceiling;
- view SHA-256.

LLM rewriting and post-result excerpt selection are forbidden.

### 10.3 FM2 descriptive projection

The Policy-visible fields are:

```json
{
  "activation_cues": [],
  "failure_pattern": [],
  "revalidate_on": [],
  "release_cues": [],
  "non_applicability_cues": [],
  "recovery_procedure": []
}
```

In FM2:

```text
recovery_procedure = []
```

### 10.4 FM3 prescriptive projection

FM3 uses the same six-field schema.

For the same Memory-record version, the following FM2 and FM3 bytes must
be identical:

- `activation_cues`;
- `failure_pattern`;
- `revalidate_on`;
- `release_cues`;
- `non_applicability_cues`.

FM3 may differ only through:

`recovery_procedure`

The snapshot records:

- descriptive projection SHA-256;
- recovery projection SHA-256;
- full projection SHA-256.

A failed or unverified recovery does not automatically delete the
descriptive record from FM3.

It leaves:

```text
recovery_procedure = []
```

unless a source-integrity, access, leakage or critical-safety failure
invalidates the entire Policy view.

---

## 11. Policy-view safety

Policy projection is fixed canonical JSON.

Field order is frozen:

```text
activation_cues
failure_pattern
revalidate_on
release_cues
non_applicability_cues
recovery_procedure
```

Policy View must not contain:

- Memory ID;
- source task/gamefile;
- source seed;
- Analyzer identity;
- effect score;
- confidence score;
- promotion status;
- exact next action;
- exact current menu-item selection;
- hidden state;
- future outcome;
- oracle path;
- teacher-only reasoning.

V1 freezes:

```text
POLICY_VIEW_EXACT_NEXT_ACTION = FORBIDDEN
POLICY_VIEW_CURRENT_MENU_ITEM_SELECTION = FORBIDDEN
```

Field-aware action-oracle lint rejects:

- a complete current menu command in `recovery_procedure`;
- instructions to choose a numbered menu item;
- direct strict-action JSON;
- instructions to output a specified action;
- prompt-field spoofing;
- system-message spoofing;
- “ignore previous” or equivalent meta-instructions.

Projection generation occurs when a snapshot candidate is built.

Live projection generation or live LLM rewriting is forbidden in V1.

---

## 12. Memory-aware prompt interface

Historical `RAW_POLICY_PROMPT_V1` remains unchanged.

V1 introduces a separate interface:

`MEMORY_AUGMENTED_RAW_POLICY_PROMPT_V1`

The field order is:

```text
TASK_GOAL_JSON
CURRENT_OBSERVATION_JSON
EXECUTED_TRANSITIONS_JSON
RETRIEVED_FAILURE_EXPERIENCES_JSON
VISIBLE_ADMISSIBLE_COMMANDS_JSON
INTERFACE_FEEDBACK_JSON
OUTPUT_REQUIREMENT
```

Persistent Memory is inserted:

```text
after MEMORY_M0_V1
before the complete admissible menu
```

The full admissible menu remains:

- complete;
- original order;
- unfiltered;
- unsorted;
- unrepaired;
- Policy visible.

The same Memory-aware interface is used for both branches.

```text
FM0 / Memory-OFF:
RETRIEVED_FAILURE_EXPERIENCES_JSON=[]

Memory-ON:
RETRIEVED_FAILURE_EXPERIENCES_JSON=[frozen projections]
```

The historical interface versus the empty-slot interface is evaluated
only as:

`INTERFACE_PERTURBATION_CHARACTERIZATION`

It is not a formal FM arm.

Severe protocol failure, off-list behavior, critical harm or major
pre-registered degradation caused by the empty interface fails the
interface design.

Minor observable differences are reported as interface effects.

---

## 13. Context budget

Hard ceilings are:

### Single-record source-state test

```text
record count = exactly 1
Memory tokens ≤ 256 Policy-tokenizer tokens
```

### Library-level Memory execution

```text
record count = 0..3
total Memory tokens ≤ 384 Policy-tokenizer tokens
```

These are hard ceilings, not necessarily the final operating budgets.

Operating budgets are selected on train development data and frozen
before either evaluation split is revealed.

Packing rules are:

```text
whole-record packing = required
mid-record truncation = forbidden
```

If the next complete record does not fit, packing stops.

It is forbidden to retain recovery guidance while truncating release or
non-applicability cues.

Actual:

- Memory tokens;
- total prompt tokens;
- record count;
- latency;

are reported for every condition.

Exact token matching between FM1, FM2 and FM3 is not required.

A later token-matched secondary ablation may separate structural benefit
from compression benefit.

---

## 14. Source-state reconstruction

The canonical V1 method is:

`A_PLUS_CANONICAL_PREFIX_REPLAY`

It consists of:

```text
environment prefix replay
+
Policy-state rehydration
+
fail-closed equivalence
```

### 14.1 Environment reconstruction

- bind exact task/gamefile;
- bind environment runtime identity;
- reset a fresh environment;
- replay exact historically executed environment actions;
- preserve exact action strings and order;
- compare every public transition.

For every replayed transition compare:

- observation SHA-256;
- menu-sequence SHA-256;
- score;
- done;
- won;
- environment-step index.

### 14.2 Policy-side rehydration

The replay also deterministically restores:

- `MEMORY_M0_V1`;
- interface feedback;
- BudgetState;
- policy-attempt count;
- environment-step count;
- consecutive nonexecuted count;
- model-call index.

Historical nonexecuted policy attempts are not regenerated by calling
the policy.

They are rehydrated from frozen evidence.

### 14.3 Source decision state fingerprint

`SOURCE_DECISION_STATE_FINGERPRINT_V1` proves that the two intervention
branches begin from the same reconstructed decision state.

It binds:

- source task and gamefile identity;
- source bundle and source policy condition;
- executed-prefix identity;
- current observation SHA-256;
- current menu-sequence SHA-256;
- `MEMORY_M0_V1` SHA-256;
- interface-feedback identity;
- BudgetState;
- model-call index;
- canonical historical non-Memory base-input SHA-256.

The historical non-Memory base input is the canonical Policy-visible
input before persistent-Memory interface content is inserted.

It excludes:

- persistent-Memory projection bytes;
- empty-versus-filled Memory state;
- final Memory-aware rendered-prompt SHA-256.

The required state identity is:

```text
historical source decision state
=
F0 reconstructed decision state
=
F1 reconstructed decision state
```

### 14.4 Branch prompt exposure identity

`BRANCH_PROMPT_EXPOSURE_IDENTITY_V1` records the intentional prompt-level
experimental difference.

It binds:

- source decision state fingerprint;
- Memory-aware interface version;
- branch role;
- empty-versus-filled projection state;
- projection IDs and versions;
- projection SHA-256;
- projection token count;
- final rendered-prompt SHA-256.

For the paired intervention:

```text
state(F0) = state(F1)

but

prompt(F0) != prompt(F1)
```

The prompt difference is the active experimental variable.

It is not a source-state reconstruction failure.

The historical prompt versus the common Memory-aware empty-slot prompt
is governed separately by:

`INTERFACE_PERTURBATION_CHARACTERIZATION`

### 14.5 Two independent reconstructions

Without an audited state clone, V1 constructs:

```text
independent F0 reconstruction
independent F1 reconstruction
```

Both must independently equal the historical source decision state
fingerprint.

They must also equal each other before persistent-Memory exposure.

Any state-fingerprint mismatch produces:

`SOURCE_STATE_RECONSTRUCTION_FAILED`

and no paired continuation is executed.

Policy-regenerated prefixes, approximate matching and unverified
snapshot restoration are forbidden.

A future audited full-stack environment clone may be used only after
canonical reconstruction passes.

It is an optimization, not reconstruction authority.

---

## 15. Memory-specific execution identity

Memory experiments must not masquerade as legacy E1 or SELECT
replicates.

V1 requires a separate execution context containing:

- Memory effect pair ID;
- branch role;
- Memory ID/version;
- source round;
- source bundle;
- source task;
- source policy condition;
- source call index;
- source decision fingerprint;
- policy checkpoint;
- `MEMORY_M0_V1` hash;
- observation hash;
- menu-sequence hash;
- budget identity;
- Memory snapshot ID;
- projection ID;
- continuation seed.

Recommended cell identity:

`MEMORY_BOUND_REPLAY_CELL_V1`

Branch role is exactly:

```text
MEMORY_OFF
MEMORY_ON
```

Legacy Runtime Core, 60/30/3 budgets, strict parser, exact menu
membership and historical E1/SELECT seed schedules remain unchanged.

Explicit request seed support is retained.

### 15.1 Failure Memory primary policy contract

V1 requires:

`FAILURE_MEMORY_PRIMARY_POLICY_CONTRACT_V1`

The frozen Round-1 checkpoint family is:

```text
P4-R1-Q2-BAD-TRAIN17
P4-R1-Q2-BAD-TRAIN31
P4-R1-Q2-BAD-TRAIN47
```

The primary-worker selection rule is frozen before Memory results exist:

```text
PRIMARY_WORKER_SELECTION_RULE
=
MINIMUM_POLICY_TRAINING_SEED
FROM_FROZEN_ROUND1_CHECKPOINT_SET
```

Therefore:

```text
PRIMARY_FROZEN_MEMORY_WORKER
=
P4-R1-Q2-BAD-TRAIN17
```

The selection rule must not use:

- Memory-effect results;
- retrieval results;
- FM0–FM3 results;
- source-state replay outcomes;
- post-hoc Memory Benefit/Harm evidence.

Before any Stage 0 execution, the policy contract must bind:

- frozen checkpoint-set identity;
- exact Train17 checkpoint and adapter identities;
- model manifest;
- tokenizer identity;
- runtime identity;
- decoding configuration;
- request seed contract.

The complete primary pipeline uses Train17 for:

- Stage 0 policy-facing development;
- Stage 1 library-level FM0–FM3 development;
- Stage 2 controlled multi-round Memory accumulation;
- Stage 3 complete FM0–FM3 formal evaluation.

Single-record source-state replay is different:

```text
SOURCE_RECORD_EFFECT_POLICY
=
ORIGINAL_SOURCE_CHECKPOINT
```

A Memory derived from a Train31 failure is first tested with Train31.

A Memory derived from a Train47 failure is first tested with Train47.

This preserves the local causal question:

> Could the policy that originally produced the failure have avoided
> that failure if it had received the registered Memory projection?

Train31 and Train47 form a preregistered secondary
policy-realization-robustness audit.

After the method, snapshot, retriever, thresholds and projections are
fully frozen, each secondary checkpoint runs:

```text
FM0_NO_PERSISTENT_MEMORY
vs
FM3_GATED_PRESCRIPTIVE_MEMORY
```

under the same final frozen Memory system.

The secondary audit is:

```text
PREREGISTERED
NO_METHOD_FEEDBACK
NO_BEST_OF_CHECKPOINT
ALL_RESULTS_REPORTED
```

It must run regardless of whether the Train17 result is favorable.

Agreement supports policy-realization robustness.

Disagreement is reported as:

`POLICY_INSTANCE_SENSITIVE_MEMORY_EFFECT`

and may not be hidden by selecting the best checkpoint.


---

## 16. Single-record effect verification

The first effect test occurs at the source failure state.

Pairing freezes:

```text
same source decision state
same policy weights
same MEMORY_M0_V1
same observation and menu
same BudgetState
same decoding configuration
same continuation seed
same Memory snapshot
same Memory-aware prompt interface
```

The only active experimental difference is:

```text
empty Memory array
vs
one pre-frozen projection
```

Record-level testing uses:

`DIRECT_FROZEN_PROJECTION`

Live retrieval is forbidden.

### 16.1 Verification-target preregistration

Before F0/F1 execution, freeze:

`MEMORY_RECORD_VERIFICATION_TARGET_V1`

It includes:

- Memory ID;
- tested applicability region;
- source state identity;
- primary local effect target;
- supporting metrics;
- hard-harm conditions;
- observation horizon;
- terminal follow-up rule;
- continuation seed;
- adjudication rule.

The primary endpoint may not be selected after observing results.

Environment depth is supporting-only by default.

### 16.2 Effect evidence

Effect scope is recorded separately:

```text
UNTESTED
SOURCE_STATE_PAIRED
REPLICATED_CONTEXT
CROSS_TASK_REPLICATED
FRESH_TASK
LIBRARY_LEVEL
```

Effect status is:

```text
POSITIVE
HARM
NEUTRAL
CONFLICTING
UNCERTAIN
```

A positive source-state result permits only:

```text
PRESCRIPTIVE_ELIGIBLE_DEV
+
SAME_TASK_DEV_ALLOWED
```

It does not imply:

- cross-task access;
- fresh evaluation eligibility;
- universal Benefit;
- transferable-memory verification;
- method-level validation.

### 16.3 Seed and replication

Default record replication is:

`ONE_SOURCE_BOUND_FROZEN_CONTINUATION_SEED`

Multi-seed replication is not a default promotion gate.

Additional replication is triggered by:

- behavioral harm;
- ambiguity;
- stochastic disagreement;
- borderline adjudication.

Stronger reusability evidence is sought through:

```text
cross-context
→ cross-task
→ fresh-task
```

Multi-seed testing is secondary stochastic-robustness evidence.

All executed replications count.

Best-of-seed selection and dropping negative branches are forbidden.

---

## 17. Harm adjudication

Effect priority is:

```text
1. critical harm
2. behavioral harm
3. preregistered primary effect
4. supporting mechanism metrics
5. cost
```

### 17.1 Critical harm

Examples include:

- future leakage;
- hidden-state leakage;
- oracle answer path;
- menu manipulation;
- protocol violation;
- forbidden privileged information.

One confirmed critical-harm observation causes fail-closed Policy-view
ineligibility.

### 17.2 Behavioral harm signal

Examples include:

- Memory-OFF success becoming Memory-ON failure;
- a new stable pathological loop;
- repeated-error worsening;
- inadmissibility worsening;
- severe budget or path degradation.

The first observation produces:

```text
BEHAVIORAL_HARM_SIGNAL
→ QUARANTINE
→ targeted replication/review
```

Confirmed harm produces:

```text
HARM_VERIFIED
→ DISABLED
```

Later positive observations must not overwrite the original harm
evidence.

Effect history is append-only.

---

## 18. Dual eligibility gates

### 18.1 Descriptive eligibility

A descriptive Policy view must pass:

1. source integrity;
2. sequence fidelity;
3. procedural completeness;
4. authority typing;
5. access safety;
6. applicability, release and conflict checks;
7. retrieval reproducibility and context budget.

Access safety contains independent checks for:

- Policy visibility;
- evaluation contamination.

Passing produces:

`RETRIEVAL_ELIGIBLE_DESCRIPTIVE`

Descriptive Memory may not directly select the current action.

### 18.2 Prescriptive eligibility

A prescriptive view must first pass all descriptive gates, then pass:

1. repair executability;
2. Policy-visible prescription;
3. source-state paired effect/harm test.

Possible dispositions are:

```text
positive + no harm
→ PRESCRIPTIVE_ELIGIBLE_DEV

behavioral harm
→ QUARANTINE + targeted replication

critical harm
→ FAIL_CLOSED

neutral
→ OFFLINE_ONLY

uncertain
→ STAGING

conflicting
→ QUARANTINE
```

Record-level promotion is not library-level scientific validation.

---

## 19. Retrieval design

V1 uses:

`HYBRID_GATED_RETRIEVAL_V1`

The retrieval pipeline is:

```text
current Policy-visible state
        ↓
access / lifecycle / safety hard filters
        ↓
mechanically checkable cue filters
        ↓
frozen candidate retrieval
        ↓
deterministic scoring/ranking
        ↓
release / non-applicability / conflict checks
        ↓
APPLICABLE / UNCERTAIN / NOT_APPLICABLE
        ↓
whole projections or abstain
```

Hard filters may use only objective, mechanically checkable,
Policy-visible or access-governance facts.

They may not infer an unobserved phase or subgoal.

V1 forbids:

- online LLM reranking;
- online Analyzer applicability judging;
- live projection rewriting;
- dynamic threshold changes;
- evaluation-time retriever learning.

`UNCERTAIN`, `CONFLICTING` and `NOT_APPLICABLE` produce:

```text
retrieve_count = 0
```

### 19.1 Query boundary

The query may use:

- public task goal;
- current observation;
- `MEMORY_M0_V1`;
- current interface feedback;
- deterministic recent-sequence signatures;
- preregistered menu features.

The complete menu remains in the Policy prompt.

Its raw full text is not included in semantic embedding by default.

### 19.2 Reproducibility

The same:

```text
query
snapshot
retrieval configuration
```

must produce the same:

- hard-filter candidate set;
- embeddings or lexical representation;
- scores;
- ranking;
- tie-break;
- selected records;
- projection bytes.

---

## 20. Retriever-selection protocol

The final retriever is not selected by cache availability.

Stage 0 preregisters a small candidate set:

```text
R1 = deterministic lexical retrieval
R2 = frozen dense retrieval
R3 = deterministic lexical+dense hybrid
```

The dense candidate may use:

```text
intfloat/e5-base-v2
revision f52bf8ec8c7124536f0efb74aca902b2995e5bcd
```

only after the complete artifact is materialized and frozen.

The current partial cache does not constitute a valid model freeze.

The dense contract, if selected, must freeze:

- exact model revision;
- exact files and hashes;
- tokenizer;
- loader;
- pooling;
- normalization;
- query/passage prefixes;
- maximum length;
- device and numeric runtime;
- embedding matrix identity.

No retrieval candidate may use `valid_seen` or `valid_unseen` for
selection.

### 20.1 Selection rule

Selection is lexicographic.

First require:

```text
zero critical leakage
zero access violations
zero known harmful-Memory eligibility
```

Then minimize:

- wrong-Memory exposure;
- unresolved-conflict exposure.

Then maximize:

- applicable-Memory recall.

If candidates remain equivalent, prefer:

```text
higher justified abstention
→ lower token/latency cost
→ simpler retriever
```

Safety errors cannot be offset by recall or latency.

### 20.2 Gold labels

Gold applicability labels are independent of the retriever.

They combine:

- deterministic access and safety facts;
- frozen human-reviewed train-DEV applicability labels;
- environment-grounded paired evidence where available.

Analyzer and retriever agreement alone is not a gold label.

The candidate search space, selection objective, constraints, tie-break
and freeze point are registered before selection begins.

---

## 21. Task and access governance

The current deterministic design input is:

`MEMORY_TASK_ACCESS_MANIFEST_CANDIDATE_V2_1`

Candidate SHA-256:

`6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a`

It is a design input, not execution authorization.

The split unit is:

`CANONICAL_TASK_GAMEFILE_GROUP`

The train partition method is:

`TASK_FAMILY_STRATIFIED_SHA256_DETERMINISTIC`

No outcome, policy performance or Memory effect is used for partitioning.

### 21.1 Train Memory-source pool

```text
TRAIN_MEMORY_SOURCE = 2367 tasks
```

Permitted uses include:

- Memory-source construction development;
- sequence-builder development;
- projection-builder development;
- optional future parametric-internalization training-source candidacy.

It is the only permitted active Memory source for formal benchmark
snapshots.

### 21.2 Train retrieval-development pool

```text
TRAIN_RETRIEVAL_DEV = 1186 tasks
```

It is disjoint from `TRAIN_MEMORY_SOURCE`.

Permitted uses include:

- retrieval threshold development;
- gold applicability development;
- hard-positive/negative construction;
- release/conflict/abstention calibration;
- retrieval error analysis.

New experience from this pool is:

`SHADOW_ONLY_NO_ACTIVE_BANK_WRITEBACK`

It may not enter the current active Memory source bank.

Before use, this 1186-task pool must be deterministically partitioned
by canonical task/gamefile group into three mutually exclusive roles:

```text
RETRIEVER_CALIBRATION_DEV

RETRIEVER_SELECTION_VALIDATION

MULTIROUND_FROZEN_DEV_PANEL
```

`RETRIEVER_CALIBRATION_DEV` may be used to develop thresholds,
abstention rules and conflict/release calibration.

`RETRIEVER_SELECTION_VALIDATION` may be used to select among the frozen
lexical, dense and hybrid retriever candidates.

`MULTIROUND_FROZEN_DEV_PANEL` is a read-only Stage 2 evaluation panel.

It may not select the retriever, tune thresholds or write back into the
active Memory bank.

The three roles must:

- contain disjoint canonical task/gamefile groups;
- use a deterministic task-family-stratified assignment;
- freeze their exact counts and manifest identities before use;
- prohibit active-bank writeback from all query/evaluation roles.

No task used to calibrate a retriever may also serve as the independent
retriever-selection validation unit.

No task used for either retrieval-development role may also serve as
the Stage 2 frozen development panel.

### 21.3 `valid_seen`

```text
valid_seen = 140 tasks
```

Scientific role:

`PROJECT_HELD_OUT_ID_CONFIRMATION`

Compatibility access-class identity:

`VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED`

“Project held out” means that these tasks were withheld from the
project's Failure Memory construction, Analyzer development, retriever
selection, threshold tuning and promotion-policy development.

It does not claim that the frozen base model was never exposed to
ALFWorld data during pretraining or public-data ingestion.

Before reveal, all of the following must already be frozen:

- Memory schema;
- Policy projections;
- retrieval keys;
- retriever candidates and selected retriever;
- thresholds;
- token budget;
- promotion policy;
- FM0–FM3;
- active snapshot;
- policy;
- runtime and evaluation package.

Formal evaluation writeback is forbidden.

### 21.4 `valid_unseen`

```text
valid_unseen = 134 tasks
```

Role:

`STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED`

It remains the standard ALFWorld OOD benchmark.

It is not:

- a clean fresh confirmatory set;
- a fresh OOD claim;
- method-selection data;
- a formal active Memory source.

Historical use is permitted only for clearly labeled mechanism
development such as source-state replay.

Formal benchmark snapshots remain train-only.

Formal benchmark writeback and readback are forbidden.

### 21.5 Formal evaluation package

`valid_seen` and `valid_unseen` use the same frozen:

- method;
- policy;
- active Memory snapshot;
- retriever;
- thresholds;
- FM definitions;
- runtime;
- evaluation code.

No method change is permitted between the two split executions.

### 21.6 Fresh OOD

A clean fresh OOD population is not currently available.

The strongest independent OOD generalization claim requires a separately
generated or external population with its own generation, access and
freeze contract.

It is optional and not a V1 design blocker.

### 21.7 Task-access regeneration gate

Execution requires:

`TASK_ACCESS_REGENERATION_GATE_V1`

The V2.1 access candidate is reproducible only under the following exact
contract.

Canonical gamefile-group identity:

```text
relative_gamefile
=
UTF-8 dataset-relative path using "/" separators

gamefile_sha256
=
SHA-256 of exact gamefile bytes

task_gamefile_group_id
=
SHA256(
  "ALFWORLD_TASK_GAMEFILE_GROUP_V1\0"
  + relative_gamefile
  + "\0"
  + gamefile_sha256
)
```

Train assignment score:

```text
split_score
=
SHA256(
  "MEMORY_TASK_ACCESS_V2_1\0"
  + task_gamefile_group_id
)
```

Within each task family:

1. sort by `(split_score, task_gamefile_group_id)`;
2. compute retrieval-DEV count as `ceil(n_family / 3)`;
3. assign the first `ceil(n_family / 3)` groups to
   `TRAIN_RETRIEVAL_DEV`;
4. assign the remaining groups to `TRAIN_MEMORY_SOURCE`.

The canonical integer implementation of `ceil(n / 3)` is:

```text
(n + 2) // 3
```

Manifest serialization is:

- UTF-8;
- one canonical JSON object per line;
- keys sorted;
- `ensure_ascii=false`;
- separators `(",", ":")`;
- records sorted by
  `(split, task_type, task_gamefile_group_id)`;
- one LF after every record.

Regeneration must reproduce:

```text
TRAIN_MEMORY_SOURCE   = 2367
TRAIN_RETRIEVAL_DEV   = 1186
valid_seen            = 140
valid_unseen          = 134
```

and the preserved historical design-candidate SHA-256:

`6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a`

This digest is historical provenance only:

`PRESERVED_HISTORICAL_DESIGN_CANDIDATE`

It is not an execution authority.

The SHA-authority correction approved under:

`DESIGN_APPROVED_FAILURE_MEMORY_TASK_ACCESS_SHA_AUTHORITY_CORRECTION_V1`

proposes the exact-contract protected-regeneration execution authority:

`260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea`

The correction changes only authority/provenance binding. The following
remain unchanged:

- task membership;
- canonical task/gamefile-group identity;
- train partition semantics;
- task-family stratification;
- role semantics;
- population counts;
- canonical protected serialization.

Execution-authority regeneration must reproduce:

```text
TRAIN_MEMORY_SOURCE   = 2367
TRAIN_RETRIEVAL_DEV   = 1186
valid_seen            = 140
valid_unseen          = 134
```

and exact-contract protected SHA-256:

`260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea`

A mismatch blocks implementation-dependent scientific execution. There
is no compatibility fallback to the historical candidate digest.

The correction-design commit supersedes only the old digest-authority
binding. It is identified through Git history and must be bound by the
correction-aware execution-authority configuration.

The original approved Failure Memory design commit:

`b3cb816e2e727600f79f1947a77c73ce87d4a97c`

remains design ancestry and is not replaced as the original Failure Memory
design authority.

The final repository manifest must be created and frozen before task
execution.

The historical `/tmp` candidate artifact/producer was not uniquely
recovered and is not required to establish the finalized exact-contract
authority once the approved three-way reproduction evidence is bound.

### 21.8 Retrieval-gold annotation governance

Retrieval gold labels require:

`MEMORY_RETRIEVAL_GOLD_ANNOTATION_V1`

Initial applicability annotation uses a separate blind view:

`MEMORY_RETRIEVAL_GOLD_CANDIDATE_VIEW_V1`

This view is descriptive-only.

It may contain:

- an opaque annotation-candidate identity;
- the Policy-visible query state;
- factual or sequence evidence permitted for annotation;
- `activation_cues`;
- `failure_pattern`;
- `revalidate_on`;
- `release_cues`;
- `non_applicability_cues`;
- a frozen applicability, release, conflict and non-applicability
  rubric.

The initial applicability view must not contain:

- `recovery_procedure`;
- proposed exact recovery actions;
- recovery-effect evidence;
- effect status;
- effect scope;
- promotion or lifecycle status;
- Analyzer confidence;
- retriever similarity scores;
- candidate ranking;
- selected retriever identity;
- paired-effect outcomes;
- final system results.

The initial annotation question is limited to:

> Based on the current Policy-visible state and the descriptive failure
> boundary, is this Memory applicable, not applicable, conflicting or
> uncertain?

Applicability and recovery quality are separate judgments.

Only after the initial applicability label is independently recorded may
a separate recovery-quality review inspect permitted recovery content.

Recovery-quality review may affect:

- repair validity;
- prescriptive eligibility;
- harm or uncertainty disposition.

It may not retroactively redefine applicability gold merely because the
recovery appears useful.

The first and second applicability passes receive the same
descriptive-only candidate view and the same blind rubric.

A second independent pass evaluates every registered case.

Disagreement proceeds to registered adjudication.

Unresolved cases become:

```text
UNCERTAIN
→ abstention-compatible
```

They are not forced into a binary applicable/not-applicable label.

All initial labels, second-pass labels, disagreements, recovery-quality
labels and adjudications are preserved in an append-only annotation
ledger.

Analyzer/retriever agreement alone is not gold authority.

Neither `valid_seen` nor `valid_unseen` may contribute gold labels,
retriever selection or threshold tuning.

---

## 22. Memory-library snapshots

Formal execution reads:

`MEMORY_LIBRARY_SNAPSHOT_V1`

It does not read a mutable latest database.

A snapshot freezes:

- included Memory record versions;
- descriptive and prescriptive projection versions;
- retrieval-key hashes;
- embedding/index identity;
- retrieval configuration;
- thresholds;
- scoring and tie-break;
- access policy;
- projection schema;
- tokenizer identity;
- token ceilings;
- snapshot SHA-256.

During a formal execution:

```text
active snapshot = read only
```

New evidence may enter only a shadow event ledger.

It cannot affect a later task in the same formal execution.

Between rounds:

```text
shadow evidence
→ verification
→ promotion decision
→ next immutable snapshot
```

Rollback is a snapshot-pointer change.

An old snapshot is never edited or deleted to simulate rollback.

---

## 23. Lifecycle and ledgers

Memory lifecycle events are append-only.

Examples include:

```text
EPISODE_COMPLETED
SEQUENCE_EXPERIENCE_BUILT
SEMANTIC_ANNOTATION_CREATED
ENVIRONMENT_VERIFICATION_COMPLETED
MEMORY_EFFECT_OBSERVED
MEMORY_QUARANTINED
MEMORY_PROMOTED
MEMORY_SUPERSEDED
SNAPSHOT_CREATED
SNAPSHOT_ROLLED_BACK
```

The four core ledgers are:

### 23.1 Event ledger

`MEMORY_EVENT_LEDGER_V1`

Authority:

- lifecycle event history.

### 23.2 Record-effect ledger

`MEMORY_RECORD_EFFECT_LEDGER_V1`

Authority:

- paired effect and harm evidence.

### 23.3 Promotion ledger

`MEMORY_PROMOTION_LEDGER_V1`

Authority:

- governance decisions and their referenced evidence.

It does not create scientific evidence.

### 23.4 Exposure ledger

`MEMORY_EXPOSURE_LEDGER_V1`

Authority:

- what the Policy actually saw on each call.

The formal active-library authority is:

`MEMORY_LIBRARY_SNAPSHOT_V1`

Consistency rules require:

- promotion references source/effect evidence;
- snapshot membership references promotion;
- exposed Memory versions exist in the bound snapshot;
- harm evidence remains append-only;
- superseded versions remain preserved.

---

## 24. Role and authority separation

### 24.1 Task Policy

May read:

- current Policy-visible state;
- frozen Policy projections.

May write:

- normal trajectory evidence.

May not:

- modify Memory;
- validate its own Memory;
- filter the menu;
- see hidden state;
- select promotion.

### 24.2 Sequence Builder

May read:

- raw evidence.

May write:

- factual sequence records.

May not:

- assign causal mechanisms;
- invent recovery;
- promote Memory.

### 24.3 Analyzer

May read:

- raw evidence;
- sequence records;
- Memory records;
- allowed historical semantic analyses.

May write:

- semantic hypotheses;
- candidate applicability;
- candidate recovery;
- typed semantic links.

May not:

- declare its own hypothesis verified;
- overwrite raw facts;
- promote directly into active Memory;
- act as an online Policy controller.

### 24.4 Environment/Effect Verifier

May read:

- source replay state;
- proposed recovery;
- effect-test design.

May write:

- reconstruction evidence;
- executability evidence;
- paired effect/harm evidence.

May not:

- rewrite raw sequence;
- decide semantic mechanism truth;
- alter Policy-visible state.

### 24.5 Memory Governance

May read:

- registered evidence and gate states.

May write:

- promotion;
- quarantine;
- disable;
- supersede;
- snapshot decisions.

May not:

- alter historical evidence;
- hide negative observations;
- create effect evidence.

### 24.6 Research Planner

Research Planner is outside Failure Memory V1 implementation.

A future Planner may read round-level aggregates and propose a next
system modification.

It may not directly mutate a live Memory system.

---

## 25. Policy-exposure evidence

Every Policy call records:

- source decision fingerprint where applicable;
- base-prompt SHA-256;
- Memory interface version;
- Memory snapshot ID;
- retrieval mode;
- retrieved Memory IDs and versions;
- projection class;
- projection SHA-256;
- projection token count;
- projection record count;
- insertion anchor;
- final rendered-prompt SHA-256;
- branch role.

Retrieval mode is one of:

```text
EMPTY_SLOT
DIRECT_FROZEN_PROJECTION
LIVE_FROZEN_RETRIEVER
```

Record-level source-state effect tests forbid
`LIVE_FROZEN_RETRIEVER`.

The exposure ledger records what was shown.

It does not infer whether the Policy internally “used” it.

---

## 26. Experimental conditions

Formal condition names are:

### FM0 — No Persistent Memory

`FM0_NO_PERSISTENT_MEMORY`

Uses the common Memory-aware prompt with:

```text
RETRIEVED_FAILURE_EXPERIENCES_JSON=[]
```

`MEMORY_M0_V1` remains unchanged.

### FM1 — Matched Raw Episodic View

`FM1_MATCHED_RAW_EPISODIC_VIEW`

Uses the same retrieval identity as FM2/FM3 and exposes the deterministic
bounded raw/sequence view.

### FM2 — Structured Descriptive Memory

`FM2_STRUCTURED_DESCRIPTIVE_MEMORY`

Uses structured procedural fields with:

```text
recovery_procedure=[]
```

### FM3 — Gated Prescriptive Memory

`FM3_GATED_PRESCRIPTIVE_MEMORY`

Uses the same candidate universe and identical descriptive bytes as FM2.

Only prescriptively eligible records receive a nonempty
`recovery_procedure`.

FM3 does not delete an otherwise eligible descriptive record merely
because its recovery is not prescriptively eligible.

---

## 27. Experimental comparisons

The primary formal condition is:

`FM3_GATED_PRESCRIPTIVE_MEMORY`

The primary method-level comparison is:

```text
FM3 vs FM0
```

Secondary decomposition comparisons are:

```text
FM1 vs FM0
→ bounded historical episodic context value

FM2 vs FM1
→ structured representation value under matched retrieval

FM3 vs FM2
→ gated recovery value beyond descriptive Memory
```

No positive ordering is assumed.

Possible scientifically meaningful results include:

- FM1 approximately equals FM0;
- FM2 approximately equals FM1;
- FM3 is worse than FM2;
- Memory reduces repeated errors without improving task success;
- Memory helps ID but not OOD;
- Memory helps OOD but creates harmful retrieval cases.

---

## 28. Metrics and statistical authority

### 28.1 Primary endpoint

The library-level primary endpoint is:

`TASK_SUCCESS`

The primary statistical unit is:

`UNIQUE_TASK`

Episodes, seeds or Memory exposures are not treated as independent task
units.

### 28.2 Supporting mechanism metrics

Supporting metrics include:

- repeated-error recurrence;
- period-1 loop;
- period-2 loop;
- state revisit;
- inadmissible recurrence;
- failure-position shift;
- environment steps;
- policy attempts;
- release-cue behavioral compliance.

If task success is unchanged, improvement in these metrics supports only
a mechanism-level claim.

### 28.3 Memory-specific observable metrics

V1 reports:

- Memory exposure rate;
- nonempty projection rate;
- retrieval rate;
- abstention rate;
- correct-applicability rate;
- wrong-Memory exposure rate;
- harmful-Memory exposure rate;
- conflict rate;
- paired action-divergence rate;
- stale-Memory persistence;
- release-cue behavioral compliance;
- Memory tokens;
- total prompt tokens;
- latency.

“Memory utilization rate” is excluded because Policy output does not
provide an observable authority for internal utilization.

### 28.4 Seeds

The design distinguishes:

```text
policy_training_seed
continuation_seed
library_evaluation_seed
```

Record-level effect testing uses one source-bound frozen continuation
seed by default.

The library-evaluation schedule is separately preregistered.

All executed replications count.

Best-of-seed reporting is forbidden.

### 28.5 Statistical analysis contract

Formal analysis requires:

`FAILURE_MEMORY_STATISTICAL_ANALYSIS_V1`

The single primary method contrast is:

```text
FM3_GATED_PRESCRIPTIVE_MEMORY
vs
FM0_NO_PERSISTENT_MEMORY
```

The project-held-out primary confirmatory estimand is:

```text
PROJECT_HELD_OUT_ID_PRIMARY_ESTIMAND
=
valid_seen task-success difference:
FM3 - FM0
```

The standard OOD benchmark estimand is:

```text
STANDARD_HISTORICALLY_EXPOSED_OOD_ESTIMAND
=
valid_unseen task-success difference:
FM3 - FM0
```

The two splits are analyzed and reported separately.

They are never pooled into one task sample.

For each split, report:

- paired task-level FM0/FM3 outcomes;
- FM0 and FM3 success rates;
- paired success-rate difference;
- paired bootstrap 95% confidence interval;
- exact two-sided McNemar test;
- FM3 wins;
- FM3 losses;
- ties.

The bootstrap resample count, bootstrap RNG seed and interval
construction rule must be preregistered before execution.

If multiple `library_evaluation_seed` values are used, the formal
schedule must preregister a task-level aggregation rule before
execution.

Seed-level episodes must not be treated as independent task units.

The exact McNemar analysis operates on the preregistered task-level
binary outcomes.

Secondary decomposition contrasts are:

```text
FM1 vs FM0
FM2 vs FM1
FM3 vs FM2
```

They are labeled:

`SECONDARY_DECOMPOSITION`

If they are reported only through effect estimates and confidence
intervals, they remain secondary descriptive analyses.

If formal hypothesis tests are performed across these secondary
contrasts, the preregistered correction is:

`HOLM_MULTIPLICITY_CORRECTION`

The primary FM3-versus-FM0 contrast may not be replaced after observing
results.

`valid_unseen` remains an important standard OOD benchmark result, but
it is not relabeled as an independent fresh confirmatory estimand.

### 28.6 Library-evaluation task aggregation

Formal execution requires:

`LIBRARY_EVALUATION_TASK_AGGREGATION_V1`

The V1 primary formal analysis uses exactly one preregistered
`library_evaluation_seed` for each task and FM condition.

The same frozen seed is used across the paired FM conditions for the
same task and frozen policy realization.

Therefore the primary task-level outcome is directly binary:

```text
task success = 0 or 1
```

and can enter the exact McNemar analysis without post-hoc seed
aggregation.

The exact primary seed value, request identity and schedule order must
be frozen before execution and must not be chosen using Memory results.

Any additional `library_evaluation_seed` executions are:

`SECONDARY_STOCHASTIC_ROBUSTNESS`

They must:

- be preregistered;
- use the same frozen method;
- report every executed result;
- prohibit best-of-seed selection;
- remain separate from the primary task-level binary outcome;
- not change the primary McNemar table.

A future protocol using multiple seeds in the primary estimand would
require a separately approved, exact binary aggregation rule and tie
rule before execution.

Such a future rule may not be selected after results are observed.

---

## 29. Stage 0 acceptance

Stage 0 must audit:

### 29.1 Evidence quality

- source binding completeness;
- sequence fidelity;
- procedural completeness;
- fact/hypothesis separation;
- typed-relation validity.

### 29.2 Safety and contamination

- Policy visibility;
- future leakage;
- hidden-state leakage;
- access violation;
- fresh-evaluation contamination;
- prompt spoofing;
- action-oracle leakage.

### 29.3 Retrieval development

The development suite includes:

- hard positive cases;
- hard negative cases;
- release cases;
- non-applicability cases;
- conflict cases;
- abstention cases.

It measures:

- applicable candidate recall;
- wrong-Memory exposure;
- harmful eligibility;
- abstention correctness;
- conflict handling.

Threshold values are selected only under the frozen selection protocol.

### 29.4 Reproducibility

Repeated retrieval with identical inputs must reproduce exact outputs.

### 29.5 Interface perturbation

Historical prompt and common empty-slot prompt are compared on a frozen
train-development control set.

The result is reported separately from Memory-content effects.

### 29.6 Cost

Record:

- candidate count;
- retrieval latency;
- selected record count;
- Memory tokens;
- total prompt tokens;
- projection-generation cost at snapshot time.

---

## 30. Stage 1 acceptance

### 30.1 Record-level evidence

Single-record testing produces append-only local effect evidence.

A positive result is local and developmental.

### 30.2 Train-only system development

FM0–FM3 development uses train-only task and Memory sources according to
the access contract.

`valid_seen` and `valid_unseen` remain unavailable for method selection.

Stage 1 determines whether the complete external Memory system is ready
for controlled multi-round development.

---

## 31. Stage 2 controlled multi-round Memory loop

Policy weights remain frozen in every round.

The complete Stage 2 processing pipeline is also frozen across the
primary accumulation experiment.

Frozen components include:

- primary policy contract;
- sequence schema and Sequence Builder version;
- Analyzer provider/model identity;
- Analyzer prompt and output schema;
- Analyzer sampling, retry and failure policy;
- source-state reconstruction implementation;
- environment/effect Verifier;
- descriptive and prescriptive eligibility gates;
- promotion and quarantine policy;
- retriever algorithm;
- lexical configuration;
- dense encoder identity where applicable;
- lexical/dense fusion rule;
- similarity and ranking weights;
- thresholds and tie-breaks;
- projection builder and schema;
- token ceilings and packing rule;
- access policy;
- development evaluation panel;
- rollback rule.

The only systematic changes allowed across the primary Stage 2
snapshots are:

```text
Memory record population
Memory record versions
snapshot identity
derived retrieval-index content
```

Retrieval-index content may change only as a deterministic consequence
of the changed Memory population.

Its construction algorithm and configuration remain frozen.

Changing an Analyzer, retriever, threshold, projection schema,
promotion rule or other pipeline component creates a separate
experimental lineage.

It may not be counted as the same Memory-accumulation curve.

### 31.1 Stage 2 round schedule

Scientific execution requires:

`STAGE2_ROUND_SCHEDULE_V1`

The default V1 schedule class is:

`FIXED_ROUND_COUNT`

Before the first Stage 2 source task is executed, the schedule must
freeze:

- the exact number of primary accumulation rounds;
- the exact source-batch identity for every round;
- the number of canonical task/gamefile groups in every batch;
- the initial snapshot identity;
- the snapshot expected after every completed round;
- the read-only evaluation-panel identity;
- the per-round execution budget;
- the infrastructure and safety halt rules.

The exact round count is selected during implementation planning under a
registered resource audit.

It must be frozen before scientific execution and before any Stage 2
result is observed.

A separately approved alternative may use:

`FIXED_SOURCE_BUDGET_EXHAUSTION`

only when the complete source budget and deterministic round assignment
are frozen before execution.

Performance-dependent stopping is forbidden.

The experiment may not stop because:

- the current snapshot appears best;
- task success has increased;
- a preferred mechanism metric has improved;
- a later round might reduce a favorable result.

All scheduled snapshots must be reported:

```text
S0, S1, ..., SR
```

No intermediate snapshot may be selected as the sole reported endpoint.

An early halt is permitted only for a preregistered:

- critical safety failure;
- access or leakage violation;
- infrastructure failure;
- resource-hard-limit violation.

An early halt must preserve:

- all completed snapshots;
- the halt reason;
- remaining unexecuted rounds;
- the fact that the schedule was not completed.

Regression and NO-GO snapshots remain part of the result.

The schematic ellipsis in:

```text
ROUND_1_SOURCE_BATCH
ROUND_2_SOURCE_BATCH
ROUND_3_SOURCE_BATCH
...
```

does not grant an open-ended stopping decision.

Execution authority comes only from the frozen round-schedule
artifact.

A round uses:

```text
frozen policy
+
read-only snapshot Sr
+
preregistered train source batch
```

During the round:

- execution reads snapshot `Sr`;
- new evidence is written only to shadow ledgers;
- the active snapshot does not change;
- no later task in the same round sees same-round writes.

Between rounds:

```text
shadow evidence
→ sequence construction
→ semantic proposal
→ verification
→ eligibility gates
→ promotion/quarantine
→ snapshot Sr+1
```

The train source stream and development evaluation panel are frozen
before round execution.

Before the first primary accumulation round, deterministic source
batches are registered:

```text
ROUND_1_SOURCE_BATCH
ROUND_2_SOURCE_BATCH
ROUND_3_SOURCE_BATCH
...
```

The split unit is the canonical task/gamefile group.

No canonical task/gamefile group may occur in more than one primary
source round.

The primary accumulation experiment therefore emphasizes cross-task
experience accumulation.

Same-task recurrence remains a separately labeled mechanism experiment.

The Stage 2 read-only evaluation panel is:

`MULTIROUND_FROZEN_DEV_PANEL`

It must be disjoint from:

- Memory source batches;
- retriever calibration;
- retriever-selection validation.

The development evaluation panel must not write back into the active
Memory source bank.

Its shadow evidence may be preserved for audit, but it may not alter the
current or later primary snapshots.

Stage 2 evaluates:

- task success across snapshots;
- repeated-error recurrence;
- wrong-Memory and harmful-Memory exposure;
- abstention;
- snapshot size;
- token and latency cost;
- regression;
- rollback;
- old-error reduction;
- new-error capture.

Monotonic improvement is not assumed.

Regression and NO-GO snapshots remain preserved.

The required claim is system-level external-Memory improvement, not
policy-weight improvement.

---

## 32. Stage 3 formal evaluation

Formal execution begins only after:

- final schema freeze;
- final access manifest;
- final retriever selection;
- final threshold freeze;
- final projection freeze;
- final active snapshot;
- final FM0–FM3 definitions;
- final policy/runtime identity;
- final Stage 2 round-schedule identity;
- final library-evaluation seed and aggregation contract;
- final schedule approval.

Run:

```text
valid_seen 140
valid_unseen 134
```

under one frozen evaluation package.

The Train17 primary worker runs the complete FM0–FM3 decomposition.

After every method component and the final snapshot are frozen,
Train31 and Train47 each run the preregistered secondary:

```text
FM0
vs
FM3
```

policy-realization-robustness audit.

The secondary audits use the same final:

- Memory snapshot;
- retriever;
- thresholds;
- projections;
- runtime;
- budgets;
- evaluation code.

They provide no method-development feedback.

Their results are reported regardless of direction.

Formal execution forbids:

- active Memory writeback;
- shadow readback;
- retriever adaptation;
- projection rewriting;
- threshold changes;
- method changes;
- test-task Memory source;
- cross-split method adjustment.

`valid_seen` supports project-held-out ID confirmation.

Project-held-out means held out from this project's Memory development;
it does not claim pretraining-level non-exposure.

`valid_unseen` supports standard historically exposed OOD benchmark
comparison.

Neither supports a clean fresh OOD claim.

---

## 33. Failure Memory V1 acceptance

Failure Memory V1 scientific acceptance requires:

1. Memory quality, procedural-completeness and safety gates pass;
2. source-state reconstruction is fail-closed and reproducible;
3. record-level paired effects are measured without claim inflation;
4. retrieval applicability gold uses the descriptive-only blind
   candidate view and independent annotation process;
5. library-level FM0–FM3 evaluation is completed;
6. harmful and conflicting Memory is auditable and controlled;
7. controlled multi-round snapshot evolution is evaluated under one
   frozen processing pipeline and one preregistered round schedule;
8. project-held-out `valid_seen` and historically exposed standard-OOD
   `valid_unseen` results are produced under one frozen package;
9. the preregistered statistical-analysis and
   library-evaluation-aggregation contracts are executed;
10. Train31 and Train47 FM0-versus-FM3 policy-realization robustness
    audits are completed without method feedback;
11. all scheduled Stage 2 snapshots, negative results, disagreements
    and NO-GO results remain visible;
12. Policy weights remain frozen for the primary V1 claim.

A positive primary result may support:

> A frozen policy agent improved at the system level through persistent,
> provenance-grounded and gated procedural failure experience.

A positive Train17 result accompanied by aligned Train31/Train47
secondary results may additionally support:

> The observed Memory effect was robust across the preregistered
> Round-1 policy-training-seed realizations.

Disagreement across the three checkpoint realizations must be reported
as policy-instance sensitivity.

It may not support:

> The underlying policy weights self-improved.

---

## 34. Failure conditions

The design fails closed on:

- missing raw provenance;
- source-sequence mismatch;
- procedural completeness not established;
- a reusable Memory collapsed to an error-action/corrected-action pair;
- untyped semantic authority;
- source-state reconstruction mismatch;
- Policy-visible hidden information;
- future leakage;
- action-oracle projection;
- prompt-field spoofing;
- access-manifest violation;
- active-snapshot mutation during execution;
- evaluation-task writeback/readback;
- applicability gold exposed to recovery, effect, promotion or
  retriever-ranking information;
- unregistered retriever change;
- live projection rewriting;
- dropped harm evidence;
- best-of-seed selection;
- undefined or post-hoc task-level seed aggregation;
- performance-dependent Stage 2 stopping;
- selective omission of scheduled Stage 2 snapshots;
- method change between evaluation splits;
- promotion without referenced evidence.

---

## 35. Deferred modules

The following are explicitly deferred:

### 35.1 Parametric policy internalization

Preserved as an optional later extension.

Not required for V1 success.

### 35.2 Research Memory

A future cross-round research record may store:

- accepted and rejected hypotheses;
- experiment outcomes;
- resource cost;
- regressions;
- NO-GO decisions.

It is not part of Policy Memory V1.

### 35.3 Research Planner

A future Planner may propose one principal system change per round.

It may not mutate a live system without offline evaluation, governance
and a new snapshot.

### 35.4 Cloud-to-local Analyzer/Planner distillation

Deferred until Analyzer and Planner quality are separately validated.

### 35.5 World-model and environment-generation extensions

Env simulation, AgentWorld-style task generation and fresh OOD
generation require separate designs and freezes.

---

## 36. Implementation decomposition after approval

After final human design approval, implementation should be decomposed
into small independently closed modules:

1. task-access regeneration and primary-policy contract;
2. factual sequence schema and builder;
3. canonical Memory schema and authority types;
4. projection builder and Policy-view safety;
5. source-state replay and Memory execution identity;
6. event/effect/promotion/exposure ledgers;
7. immutable snapshot builder;
8. retrieval-DEV subpartition and blind gold-label tooling;
9. lexical/dense/hybrid retriever candidates;
10. threshold-selection harness;
11. common Memory-aware prompt interface;
12. Stage 0 quality/safety suite;
13. record-level paired-effect runner;
14. FM0–FM3 train-development runner;
15. controlled multi-round Memory loop;
16. statistical-analysis and reporting package;
17. formal ID/OOD evaluation package;
18. secondary policy-realization robustness audit;

Each implementation module requires:

- its own plan;
- tests;
- deterministic audit;
- single-purpose commit;
- push;
- remote equality;
- parent-ledger update.

---

## 37. Final design gate

Final design status:

`DESIGN_APPROVED_FAILURE_MEMORY_V1`

The approved design authority is the complete specification at the
final-hardened design basis:

`6b84488ca08f730f11427dcd0f1611ad6408ceb7`

The user granted explicit final approval on 2026-08-15.

Current authorization is:

```text
IMPLEMENTATION_PLAN = AUTHORIZED

MEMORY_BUILDER_IMPLEMENTATION = NOT_AUTHORIZED
MEMORY_RECORD_MATERIALIZATION = NOT_AUTHORIZED
MEMORY_ASSISTED_EXECUTION = NOT_AUTHORIZED
SCIENTIFIC_EXECUTION = NOT_AUTHORIZED
```

Implementation authorization requires:

1. a written implementation plan;
2. plan self-review;
3. human review and approval of that plan;
4. implementation-module-specific execution authorization.

Design approval does not waive any task-access, provenance, safety,
testing, audit, commit, push or remote-equality requirement.
