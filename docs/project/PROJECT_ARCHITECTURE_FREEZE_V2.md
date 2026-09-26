# PROJECT_ARCHITECTURE_FREEZE_V2

## Canonical project question

Can a research-guided self-improvement system use a local policy's real
failures, structured cross-trajectory analysis and historical failure
experience to discover promising repairs; reject ineffective or harmful
repairs through same-state environment experiments; and internalize only
verified evidence so that the next policy is stronger with Memory OFF and
Harness OFF?

## Canonical chain

```text
π1 rollout
→ immutable full-trajectory evidence
→ deterministic mechanical evidence
→ Hierarchical Analyzer
→ historical Failure Experience support
→ Human Training Researcher prioritization
→ registered candidate repair
→ same-state F0/F1
→ Benefit / Harm / Neutral / Uncertain
→ verified training evidence
→ π2-human
→ Memory OFF + Harness OFF evaluation
→ promote / rollback
```

## Roles and authorities

### Task Policy

Produces environment actions. It cannot read Analyzer reasoning, F0/F1
outcomes, future state, training labels, or sealed detailed evidence.

### Evidence layer

Stores exact policy calls, ActionTrace, public transitions, episode artifacts,
checksums and immutable sidecar bindings. It contains facts, not explanations.

### Mechanical Evidence Extractor

Computes deterministic facts only. It cannot infer a failure mechanism,
criticality, repair utility, Benefit or Harm.

### Hierarchical Analyzer

Proposes failure windows, hypotheses, counterevidence and candidate repairs. Its
outputs remain proposals. It has no environment-action authority and no causal
outcome authority.

### Persistent Failure Experience Library

Provides governed historical evidence and applicability/counterexample context.
It is not a reasoning agent and does not decide promotion.

### Human Training Researcher

Before the first π1→π2 reference round is automated, a human follows a frozen
template to prioritize one principal bottleneck and a bounded experiment
portfolio. The Researcher cannot act as its own verifier or promotion gate.

### Training Harness

Executes registered experiments, state reconstruction, F0/F1 branches,
training-data construction, training and evaluation. It is the Researcher's
execution arm, not a separate scientific judge.

### Environment Verifier

The only source of Benefit/Harm/Neutral/Uncertain outcome authority, subject to
the frozen policy-conditioned paired protocol.

### Independent Promotion Gate

Reads frozen evaluation artifacts and deterministic rules only. It does not
read the Researcher's preference prose as evidence that π2 is better.

## Current scientific status

```text
π0→π1 = NO-GO for long-horizon competence
Failure Memory direct-to-policy Q1 = NOT_SUPPORTED
Failure Memory representation Q2 = NOT_SUPPORTED
Failure Memory retrieval/utility Q3 = NOT_SUPPORTED
Q4 = HANDOFF_TO_ANALYZER_VERIFIER_STAGE
Q5 = HANDOFF_TO_VERIFIED_TRAINING_OFF_OFF_STAGE
```

These dispositions are immutable historical inputs to the next round.

## Explicitly deferred

```text
autonomous Research Planner control of a real round
π2→π3 autonomous loop
routine local Analyzer as primary
unified Policy/Analyzer/Researcher checkpoint
audited RL
```

They may be shadow experiments only until π1→π2 obtains an independently
audited GO.
