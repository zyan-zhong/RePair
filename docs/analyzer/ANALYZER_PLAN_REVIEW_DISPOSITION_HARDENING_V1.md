# ANALYZER_PLAN_REVIEW_DISPOSITION_HARDENING_V1

## Status

```text
EXTERNAL_REVIEW_DISPOSITION = TECHNICALLY_EVALUATED
MAJOR_REDIRECTION = NO
TARGETED_HARDENING = REQUIRED
PLAN_APPROVAL_AFTER_THIS_HARDENING = ELIGIBLE_FOR_HUMAN_APPROVAL
```

This document records which review recommendations are adopted, narrowed, or
rejected after checking them against the frozen project architecture and the
actual 16-Task plan. It is normative where earlier wording conflicts.

## 1. Adopted blockers

### H1 — Scientific outcome availability gate

A terminal Boolean is not enough to classify a policy episode. Routing first
produces one of:

```text
SCIENTIFIC_OUTCOME_AVAILABLE
INFRASTRUCTURE_UNAVAILABLE
PROTOCOL_INVALID
EVIDENCE_INCOMPLETE
```

Only `SCIENTIFIC_OUTCOME_AVAILABLE` may enter `SUCCESS` or `FAILURE` semantic
lanes. The other routes remain in the census and missingness ledger but never
become policy failures.

Every Analyzer artifact additionally binds:

```text
scientific_use = PRIVILEGED_OFFLINE_ANALYSIS
analysis_time_information_boundary = POST_EPISODE_DEV_ONLY
```

These fields do not permit privileged outcome information to enter the online
Task Policy.

### H3 — Multi-error, error-instance grouping

Local failure analysis already supports multiple `error_instances[]`. Grouping
therefore operates on `ErrorInstanceMembershipV1`, not one episode-level onset.
One episode may contribute several error instances and may participate in
several groups. Each error instance has exactly one primary mechanical group
membership; optional matched/cross-outcome views are immutable sidecars.

Primary grouping keys remain mechanical and preregistered:

```text
task family
error-instance mechanical signature
progress/precondition signature
lifecycle/resolution signature
terminal-footprint class
```

Model-generated mechanism prose is not a primary grouping key. Statistical
inference remains clustered by task/gamefile; multiple memberships cannot
inflate the independent sample size.

### H4 — Explicit C/P semantic producer

Component attribution is an explicit C-stage semantic artifact,
`ANALYZER_COMPONENT_ATTRIBUTION_V1`, containing evidence references,
principal/secondary assignments, uncertainty, and raw/validated response
hashes. Deterministic profile code only aggregates validated assignments and
zero-claim denominators; it never infers components from prose.

### H6 — One metric source of truth

`ANALYZER_METRIC_TARGETED_HARDENING_V2` and the updated registry are normative.
Older HES/ECB headline wording is replaced by separately reported failure and
protected-cohort Harm, ProposalCoverage, VBP, formal verifier environment steps
per repaired unique unit, and EVRY@B. D2 uses `shortest tested sufficient
prefix` unless every shorter prefix is definitively non-Benefit. The trace is
named `RepairEffectDecompositionTraceV1`, not a mediator trace.

### H7 — Runtime activation is a separate approval gate

Tasks 1–16 implement and close deterministic scientific infrastructure. Their
completion status is:

```text
ANALYZER_DETERMINISTIC_SCIENTIFIC_INFRASTRUCTURE_CODE_APPROVED
```

It is not `COMPLETE_ANALYZER_EXECUTED`. Strong-model execution requires the
separate `ANALYZER_V2_STRONG_MODEL_RUNTIME_ACTIVATION_V1` handoff and explicit
approval. Existing P2 provider/provenance/retry/no-clobber assets are reused.

## 2. Partially adopted recommendations

### H2 — Keep the failure-majority scheduler, narrow its authority

The previously human-approved 85/15, 70/30, and 55/45 regimes are retained for
large-scale offline API sampling. They are reclassified as:

```text
MECHANICAL_OUTCOME_ANALYSIS_SAMPLING_SCHEDULER_V1
NOT_AN_ANALYZER_SEMANTIC_METHOD_COMPONENT
NOT_USED_TO_DEFINE_U_REG
NOT_USED_TO_SELECT_THE_RESEARCHER_BOTTLENECK
NOT_A_PAPER_METHOD_CLAIM
```

Formal A0–A3 still use the same failure-only `U_reg`. The success cohort remains
separate. The scheduler controls cost and coverage only; the Training
Researcher decides the research priority after receiving Analyzer and verifier
evidence. Deleting the scheduler would discard an already approved and useful
failure-priority resource rule; allowing it to choose the research question
would violate role boundaries.

### H5 — Fix the source-conditioned gap without an unequal extra model call

The review correctly identifies that a deterministic projector cannot turn an
abstract group template into an exact action. The primary experiment does not
add an extra source-conditioned strong-model pass only to A2/A3, because that
would confound hierarchy with additional computation.

Instead, the registered G-stage output may contain
`source_conditioned_repairs[]`, each bound to one member source state, its exact
visible menu, evidence references, and K=1/ABSTAIN contract. C/P/X may rank,
downgrade, or reject these bytes but cannot invent or rewrite executable bytes.
The deterministic projector validates identities, menu membership, budget,
option length, termination, and X disposition. An abstract template without a
source-conditioned executable proposal projects to ABSTAIN.

A future equalized generative extension may compare additional proposal calls,
but it is not part of the primary A0–A3 estimand.

## 3. Clarifications, not redesign blockers

- Task 12 already has a multi-error gold concept; implementation templates and
  tests are hardened to include lifecycle/resolution, terminal footprint,
  alternatives, `MULTI_CAUSAL`, `INDETERMINATE`, and
  `INSUFFICIENT_EVIDENCE`.
- Task 10 may materialize Researcher supervision only from actual frozen
  Human/API Researcher pre/post records governed by
  `HUMAN_TRAINING_RESEARCHER_TEMPLATE_V1`; Analyzer artifacts cannot fabricate
  Researcher targets.
- Task 13 remains implemented as reusable infrastructure but live execution is
  `SECONDARY_NON_BLOCKING`.
- Task 14 remains implemented as reusable infrastructure but live D0–D4
  execution is `POST_BENEFIT_SECONDARY` and cannot block the first A0–A3 run.

## 4. Preserved strengths

The following are unchanged: common `U_reg`; K=1 or ABSTAIN; A1 local output is
reused byte-for-byte by A2/A3; the local pass is Memory-blind; A3 adds only a
frozen higher-level Memory packet; X is immutable; rejected/invalid/Harm/
Neutral/Uncertain outcomes remain visible; environment verification is the
only Benefit/Harm authority; task/gamefile is the statistical unit; final paper
authority remains π2 versus π1 with Memory OFF and Harness OFF.
