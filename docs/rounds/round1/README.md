# Round 1 — Single-Round Policy Improvement Validation

## Status at a Glance

| Item | Current status |
|---|---|
| Round identity | `ROUND1_SINGLE_ROUND_POLICY_IMPROVEMENT_VALIDATION` |
| Round execution | `COMPLETE` |
| Policy-improvement result | `COMPLETE_NO_GO` |
| Hierarchical analysis | `LEVELS_1_TO_4_COMPLETE` |
| Level 5 global synthesis | `LEVEL_5_REJECTED` |
| Level 6 independent challenge | `LEVEL_6_INCOMPLETE` |
| Canonical evidence and provenance closure | `IN_PROGRESS` |
| Failure Memory | `HOLD` |

The first pi0-to-pi1 training round was executed.

The final Harness-OFF evaluation did not establish successful policy
improvement. Round 1 therefore ended in a `NO-GO`.

The round produced substantial diagnostic evidence, but diagnostic
completion must not be confused with successful policy improvement.

## Research Question

Round 1 asks:

> Can failure-directed, externally proposed and environment-validated
> training data transform the initial task policy into a policy that
> performs better when evaluated without the external assistance used
> to construct the training signal?

The decisive scientific endpoint is the task policy under Harness-OFF
evaluation.

External analysis quality, training completion, interface compliance
and evidence-package completion are supporting measurements rather than
substitutes for that endpoint.

## Round Identity and Policy Boundary

### pi0 task policy

pi0 is the pre-training task policy used to generate the initial
development evidence.

Its role is:

```text
goal
+ current observation
+ recent executed history
+ admissible-action menu
→ task action
```

### pi1 task policy

pi1 is the policy produced by the first training round.

Its scientific value must be judged through independent Harness-OFF
evaluation rather than by training loss or teacher agreement.

### External strong proposer / analyzer

The external strong model is an offline semantic component.

Its role is to propose diagnoses, critical regions or correction
candidates from authorized development evidence.

It is not environment truth.

```text
semantic analyzer output
≠
environment truth
```

### Environment / Q2 verifier

The environment-validation path determines whether a proposed action or
state-bound correction is actually valid under the registered
environment evidence.

This is distinct from semantic plausibility.

### Harness-OFF evaluator

The evaluator measures task-policy behavior without treating external
teacher or analyzer output as an online decision authority.

This is the primary policy-improvement acceptance boundary.

### Future local analyzer

A future local analyzer may learn to perform trajectory diagnosis and
cross-trajectory synthesis.

It is not yet an approved or validated Round-1 component.

### Future Research Planner

A future Research Planner operates at the cross-round research level:

```text
round evidence
→ next research / training proposal
```

It is not an ALFWorld task-action policy and did not participate in
Round-1 task execution.

### Internalization boundary

```text
Harness-assisted or Memory-assisted behavior
≠
policy internalization
```

Policy internalization requires improvement that remains when the
external assistance being studied is disabled.

## End-to-End Workflow

```text
governance and runtime foundation
→ pi0 development trajectories
→ strong-model candidate proposals
→ Q2 environment validation
→ training-data construction
→ pi1 training
→ Harness-OFF evaluation
→ NO-GO
→ mechanical analysis
→ hierarchical semantic analysis
→ canonical provenance closure
→ Failure Memory handoff
```

This workflow contains different authority types.

Builders construct artifacts.

Mechanical analyzers derive deterministic facts.

Semantic analyzers propose interpretations.

Environment validators establish execution validity.

Trainers update model parameters.

Evaluators aggregate policy performance.

No single component automatically inherits the authority of another.

## Workflow Stage Status

| Stage | Status | Round-1 role |
|---|---|---|
| Governance and runtime foundation | `COMPLETE` | Freeze execution, access, evidence and runtime boundaries |
| pi0 trajectory collection | `COMPLETE` | Produce development policy evidence |
| Strong-model proposal | `COMPLETE` | Generate offline semantic correction candidates |
| Q2 environment validation | `COMPLETE` | Bind and validate candidate corrections against environment evidence |
| Training-data construction | `COMPLETE` | Materialize accepted training examples |
| pi1 training | `COMPLETE` | Produce first-round trained policy candidate |
| Harness-OFF evaluation | `COMPLETE_NO_GO` | Test whether policy improvement survived removal of external assistance |
| Mechanical post-hoc analysis | `COMPLETE` | Derive deterministic failure and trajectory facts |
| Hierarchical semantic analysis Levels 1-4 | `COMPLETE` | Build progressively broader diagnostic hypotheses |
| Global mechanism synthesis, Level 5 | `REJECTED` | Attempted synthesis did not pass the formal evidence-closure boundary |
| Independent challenge, Level 6 | `INCOMPLETE` | No final completed Round-1 challenge result is registered |
| Canonical evidence and provenance closure | `IN_PROGRESS` | Close remaining byte, semantic and provenance gaps |
| Failure Memory | `HOLD` | No formal Memory generation or Memory experiment is authorized yet |

## Main Result and Interpretation

Round 1 completed the full pi0-to-pi1 training and Harness-OFF
evaluation path, but the policy-improvement endpoint was not achieved.

The appropriate scientific disposition is therefore:

```text
ROUND1_POLICY_IMPROVEMENT = NO-GO
```

The round did show that some interface and protocol behavior could be
transferred into the trained policy.

That observation is useful diagnostically, but it must not be presented
as successful long-horizon task competence.

The core unresolved issue is therefore not whether the training
pipeline ran, but why the transferred supervision failed to produce the
required independent task-level improvement.

## Mechanical and Hierarchical Post-hoc Analysis

After the Round-1 NO-GO, two distinct analysis families were used.

### Mechanical post-hoc analysis

Mechanical analysis derives facts that can be computed without semantic
LLM judgment, including examples such as:

- termination structure;
- action repetition;
- state revisit;
- loop structure;
- environment depth;
- task/checkpoint comparison;
- other deterministic trajectory signatures.

These outputs have deterministic mechanical-fact authority only.

### Hierarchical semantic analysis

The semantic post-hoc hierarchy is:

```text
Level 1 — Matched-Group Analysis
        ↓
Level 2 — Capability-Scoped Mechanism Discovery
        ↓
Level 3 — Task-Family Projection
        ↓
Level 4 — Cross-Capability Interaction / Coverage Synthesis
        ↓
Level 5 — Global Mechanism Synthesis
        ↓
Level 6 — Independent Challenge
```

Current disposition:

```text
Levels 1-4 = COMPLETE
Level 5    = REJECTED
Level 6    = INCOMPLETE
```

Completion of a semantic analysis level means that its registered
analysis procedure completed under its evidence contract.

It does not make its hypotheses causal environment truth.

The detailed Level 1-6 component, population, request, audit and
asset map is maintained in the
[Hierarchical Analysis Ledger](./HIERARCHICAL_ANALYSIS.md).

## Canonical Evidence and Provenance Closure

Canonical evidence/provenance closure is a sibling workstream to the
hierarchical semantic analysis. It is not Level 0 and does not renumber
Levels 1-6.

The current navigation entry is:

[Round-1 Canonical Gap Audit](../../audits/ROUND1_CANONICAL_GAP_AUDIT.md)

The later raw-bundle provenance validator now reports:

```text
bundle_count                = 340
verified_bundle_count       = 340
rejected_bundle_count       = 0
provenance_validated        = true
semantic_identity_validated = true
```

That result closes the registered raw-bundle byte/semantic-identity
layer used for the future Memory handoff.

It does not rewrite the earlier historical canonical-artifact contract
audit. That historical audit remains preserved with:

```text
canonical_contract_complete = false
```

Its six non-unique discovery slots were subsequently resolved by human
review for the current Asset Registry without rewriting the original
audit.

Accordingly the project-level canonical evidence/provenance workstream
remains `IN_PROGRESS` rather than being promoted to a stronger final
closure claim.

## Failure Memory Handoff

Failure Memory has not yet been formally generated or evaluated.

Current state:

```text
FAILURE_MEMORY = HOLD
```

The 340 verified raw bundles, executed-history semantics audit,
source-file inventory and sequence-truth audit are evidence-preparation
inputs for the next design review.

They are not an already materialized Memory library.

The sequence-truth audit supports complete timeline call ranges across
the registered matched packs, while sparse detailed anchors are not
accepted as complete-sequence authority.

Therefore the next research-facing action is human review of the
Failure Memory representation and retrieval/injection design.

No Memory builder, Memory record materialization or Memory-assisted
experiment is authorized before that design is explicitly reviewed and
approved.

## Component Map

The major scientific and engineering components used during Round 1 are
registered in:

[Round-1 Component Registry](./COMPONENT_REGISTRY.md)

The registry separates:

- builders;
- runners;
- collectors;
- publishers;
- mechanical analyzers;
- semantic analyzers;
- verifiers;
- trainers;
- evaluators;
- aggregators;
- governance and registry components.

It also records the authority boundary of each component.

## Documentation Map

### Round-level records

- [Component Registry](./COMPONENT_REGISTRY.md)
- [Asset Registry](./ASSET_REGISTRY.md)
- [Hierarchical Analysis Ledger](./HIERARCHICAL_ANALYSIS.md)
- [Asset Consolidation Ledger](./ASSET_CONSOLIDATION_LEDGER.md)

### Current evidence closure

- [Round-1 Canonical Gap Audit](../../audits/ROUND1_CANONICAL_GAP_AUDIT.md)

### Project-level records

- [Experiment Ledger](../../experiments/EXPERIMENT_LEDGER.md)
- [Code Map](../../code_map.md)
- [Module Closure Policy](../../protocol/MODULE_CLOSURE_POLICY.md)

### Frozen consolidation design

- [Round-1 Research Asset Consolidation V1](../../superpowers/specs/2026-08-13-round1-research-asset-consolidation-v1-design.md)

The root README, Experiment Ledger, Code Map and closure policy are
synchronized by the final historical research-asset consolidation.

## Claim Boundary

Round 1 supports the following high-level statements:

- the first pi0-to-pi1 experimental training round was executed;
- the registered Harness-OFF evaluation produced a NO-GO for policy
  improvement;
- post-hoc mechanical failure analysis was completed;
- hierarchical semantic analysis was completed through Level 4;
- the attempted Level-5 global synthesis was formally rejected;
- final Level-6 completion is not registered;
- historical evidence/provenance closure remains in progress.

Round 1 does not currently support the following stronger claims:

- successful autonomous policy self-improvement;
- causal truth for hierarchical semantic mechanisms;
- successful Failure Memory;
- successful local Analyzer;
- successful Research Planner;
- successful pi2;
- policy improvement established only from Harness-ON or Memory-ON
  behavior.

## Current Next Step

Historical Round-1 research-asset consolidation is finishing in the
current closure commit.

The remaining project boundary is:

```text
Canonical evidence/provenance closure = IN_PROGRESS
Failure Memory                        = HOLD
```

The next research-facing gate is human review of the Failure Memory
design and its sequence-memory schema.

No Memory builder, Memory materialization or Memory-assisted scientific
experiment is authorized before that design is explicitly approved.
