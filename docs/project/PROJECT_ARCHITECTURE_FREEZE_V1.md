# Project Architecture Freeze V1

```text
STATUS = CANONICAL_PROJECT_BACKGROUND
CHANGE_POLICY = EXPLICIT_USER_DIRECTIVE_REQUIRED
```

Date frozen: 2026-08-19

This document defines the canonical role decomposition for the
Phase-Critical Harness-Guided Self-Improvement project.

Absent an explicit user/researcher directive, implementation plans, experiments,
paper diagrams and system descriptions must preserve this decomposition.

## 1. Task Policy

The Task Policy `πk` executes environment actions.

Its role is:

```text
task goal + current observation + allowed policy context
→ action
```

It is not the Analyzer and it is not the Training Researcher.

The decisive policy-improvement authority is independent evaluation with:

```text
Memory OFF
Harness OFF
```

A new policy version is not accepted merely because an external scaffold makes
the combined system stronger.

## 2. Hierarchical Analyzer — trajectory intelligence

The Hierarchical Analyzer owns reasoning over trajectories and failure evidence.

Its responsibilities include:

- trajectory segmentation;
- relevant-window localization;
- failure-onset localization;
- recovery-window detection;
- trajectory fusion;
- cross-trajectory comparison;
- grouped-trajectory analysis;
- multi-level temporal analysis;
- multi-dimensional attribution;
- mechanism hypotheses;
- counterevidence and contradiction analysis;
- applicability hypotheses;
- candidate repair proposals;
- abstention when evidence is insufficient.

The Analyzer should eventually replace routine manual trajectory cutting.
Human segmentation is a bootstrap/calibration activity, not the intended
steady-state pipeline.

Analyzer outputs do not become factual or causal truth merely because the
Analyzer produced them.

## 3. Persistent Failure Experience Library / Procedural Memory

Memory is **not a reasoning model**.

It is a governed evidence and reusable-experience substrate.

It stores and indexes:

- provenance-grounded factual experience;
- typed procedural records;
- source bindings;
- Analyzer hypotheses with explicit authority type;
- applicability/revalidation/release boundaries;
- recovery proposals;
- effect status;
- exposure status;
- retrieval keys;
- immutable snapshots;
- lineage/version history;
- harm/quarantine/governance state.

A deterministic Memory Compiler / Experience Builder converts approved evidence
and typed Analyzer output into canonical records.

Memory must not independently:

- infer scientific truth;
- declare Benefit/Harm;
- promote its own recovery proposal;
- alter Task Policy actions outside a frozen Policy-view interface.

## 4. Training Researcher — system-level research and training intelligence

The Training Researcher operates one level above trajectory diagnosis.

It reads:

- Analyzer findings;
- persistent Failure Experience;
- environment/causal verification evidence;
- training logs;
- policy evaluation;
- regression and NO-GO evidence;
- resource/cost evidence;
- historical research evidence.

It decides or proposes:

- which weakness is most important next;
- which candidate repair deserves testing;
- which data should be collected;
- which causal experiment should be run;
- which training signal should be constructed;
- which training method or objective should be tested;
- whether Analyzer/retrieval/verification/training design should change;
- whether a candidate policy deserves formal evaluation;
- whether to promote or roll back after independent evaluation.

The Training Researcher is not an ALFWorld action planner.

## 5. Training Harness — execution arm of the Training Researcher

The Harness is part of the Training Researcher system.

It is **not** a separate reasoning agent.

It executes controlled research/training operations such as:

- source-state reconstruction;
- controlled interventions;
- same-state F0/F1 execution;
- candidate repair experiments;
- environment verification;
- training-signal construction;
- training/evaluation machinery;
- evidence collection needed by the Training Researcher.

The Researcher chooses what to investigate.
The Harness performs the controlled experiment.

## 6. Environment / Verifier — causal authority

Environment evidence is independent authority.

For same-state intervention experiments, the frozen environment/verifier
determines:

```text
Benefit
Harm
Neutral
Uncertain
```

The Analyzer, Training Researcher and Memory Library may propose explanations,
but none may override environment evidence or self-certify a repair as useful.

## 7. Canonical self-improvement chain

The project-level scientific chain is:

```text
real failure evidence
→ Hierarchical Analyzer
→ historical Failure Experience retrieval/support
→ candidate diagnosis and repair
→ Training Researcher selects controlled experiment
→ Training Harness performs same-state intervention
→ Environment / Verifier produces causal evidence
→ verified training evidence
→ train candidate πk+1
→ Memory OFF + Harness OFF independent evaluation
→ promote / rollback
```

Failure Memory is an intermediate researcher-support mechanism, not the terminal
scientific claim.

## 8. Automatic trajectory processing target

The current manually registered Failure Memory examples are bootstrap gold
labels.

The target steady-state path is:

```text
raw trajectory
→ mechanical evidence assembler
→ Hierarchical Analyzer
   - segment
   - localize
   - compare
   - fuse
   - diagnose
   - propose
→ deterministic typed compiler
→ governed Failure Experience
→ environment verification where causal authority is required
```

Human review remains for:

- calibration;
- blind audits;
- disagreement adjudication;
- protocol changes;
- high-risk exceptions.

It should not remain routine per-failure labor.

## 9. Researcher and Analyzer remain separate

```text
Analyzer:
What happened across these trajectories?
Where did failure develop?
What mechanisms and candidate repairs are supported?

Training Researcher:
Given Analyzer + verifier + training/evaluation evidence,
what should the overall self-improvement system investigate or train next?
```

These roles must not be silently merged.

## 10. Change control

Any future proposal that changes these role boundaries must explicitly state:

```text
PROJECT_ARCHITECTURE_FREEZE_V1_CHANGE_REQUEST
```

and receive explicit researcher/user approval before implementation.
