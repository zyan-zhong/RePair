# Round-1 Research Asset Consolidation V1

## 1. Status

Design status:

`DESIGN_FROZEN_IMPLEMENTATION_NOT_STARTED`

This design organizes the historical assets of the completed first
single-round policy-improvement validation.

It does not rerun an experiment, modify scientific evidence, reinterpret
a result, generate Failure Memory records or change any frozen SHA-256
identity.

## 2. Problem

The repository contains substantial code, manifests, experiment assets,
audits and Git history, but the current navigation layer does not expose
the full first-round scientific workflow.

In particular:

- the root README is behind the current research state;
- the experiment ledger is dominated by earlier Runtime Core and
  backend-probe engineering;
- the code map does not expose the active single-round research
  components;
- strong-proposer, Q2, training, Harness-OFF and post-hoc assets lack one
  canonical Round-1 entry point;
- hierarchical analysis Levels 1-6 do not have one repository-level
  component and asset map;
- builders, runners, analyzers, verifiers, trainers, evaluators and
  aggregators are not consistently distinguished.

## 3. Scientific scope

The consolidated round is:

`ROUND1_SINGLE_ROUND_POLICY_IMPROVEMENT_VALIDATION`

Its core path is:

```text
pi0 evidence
→ strong-model candidate generation
→ Q2 environment validation
→ training-data construction
→ pi1 training
→ Harness-OFF evaluation
→ NO-GO
→ mechanical and hierarchical post-hoc analysis
→ canonical provenance closure
→ Failure Memory handoff
```

The completed first-round result remains a `NO-GO` for policy
improvement.

The consolidation must not convert engineering completion or semantic
analysis completion into a stronger scientific claim.

## 4. Terminology namespaces

Three independent terminology namespaces are retained.

### 4.1 Research-system layers

These describe the overall research system:

1. same-state causal audit;
2. single-round policy internalization;
3. cross-round Research Planner.

### 4.2 Round-1 workflow stages

These describe the first single-round workflow:

1. governance and runtime foundation;
2. pi0 trajectory collection;
3. strong-model proposal;
4. Q2 environment validation;
5. training-data construction;
6. pi1 training;
7. Harness-OFF evaluation;
8. mechanical post-hoc analysis;
9. hierarchical semantic analysis;
10. canonical evidence and provenance closure;
11. Failure Memory handoff.

### 4.3 Hierarchical-analysis levels

These describe only the semantic post-hoc analysis:

- Level 1 — Matched-Group Analysis;
- Level 2 — Capability-Scoped Mechanism Discovery;
- Level 3 — Task-Family Projection;
- Level 4 — Cross-Capability Interaction / Coverage Synthesis;
- Level 5 — Global Mechanism Synthesis;
- Level 6 — Independent Challenge.

Canonical evidence and provenance closure is not called Level 0.

## 5. Target documentation structure

```text
docs/rounds/round1/
├── README.md
├── COMPONENT_REGISTRY.md
├── HIERARCHICAL_ANALYSIS.md
├── ASSET_REGISTRY.md
└── ASSET_CONSOLIDATION_LEDGER.md
```

Existing evidence remains at its current canonical location.

For example:

```text
docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md

docs/audits/evidence/
└── round1_canonical_gap/
    └── r132_primary117_identity_v1/
```

The new Round-1 documents link to existing evidence rather than moving
or copying it without a specific preservation reason.

## 6. Document responsibilities

### 6.1 Root README

The repository entry point.

It records only:

- project purpose;
- canonical protocol;
- current research state;
- most important current conclusion;
- links to the Round-1 overview, experiment ledger, current audit,
  protocol and code map.

### 6.2 Round-1 README

The canonical human-readable entry point for the first single-round
validation.

It records:

- research question;
- policy identities;
- workflow stages;
- major components;
- major results;
- NO-GO interpretation;
- hierarchical-analysis status;
- provenance-closure status;
- Failure Memory handoff state;
- links to authoritative sub-ledgers and assets.

### 6.3 Component Registry

The canonical registry of scientific and engineering components used in
Round 1.

Every component records:

- component name;
- internal or historical ID;
- component type;
- scientific role;
- inputs;
- outputs;
- authority boundary;
- code or script location;
- server evidence root;
- repository mirror or ledger;
- status;
- producer and consumer relationship;
- commit, package or SHA-256 identity where known.

### 6.4 Hierarchical Analysis Ledger

The canonical map of Levels 1-6.

Every level records:

- research question;
- population and denominator;
- evidence-pack builder;
- deterministic census builder;
- request builder;
- semantic analyzer;
- local shadow analyzer, if applicable;
- semantic validator;
- deterministic verifier;
- result aggregator;
- inputs and outputs;
- model-call count;
- result status;
- conclusion boundary;
- authoritative assets;
- downstream level.

### 6.5 Asset Registry

The canonical path and identity registry.

Every asset records:

- logical name;
- scientific role;
- server path;
- repository path, if mirrored;
- producer;
- downstream consumer;
- file count or population;
- SHA-256 or root seal;
- status;
- retention rule;
- whether the asset is authoritative, derived or navigational.

### 6.6 Experiment Ledger

The project-wide record of major scientific events.

It does not duplicate every low-level file.

### 6.7 Code Map

The active implementation and component map.

Historical implementation details remain, but the current active
research path must appear first.

## 7. Component types

The registry uses the following component types:

- `GOVERNANCE`
- `BUILDER`
- `RUNNER`
- `COLLECTOR`
- `PUBLISHER`
- `MECHANICAL_ANALYZER`
- `SEMANTIC_ANALYZER`
- `VERIFIER`
- `TRAINER`
- `EVALUATOR`
- `AGGREGATOR`
- `REGISTRY`

A component may have more than one type only when the roles cannot be
separated without falsifying the historical implementation.

## 8. Authority boundaries

The registry distinguishes:

- byte and identity authority;
- deterministic mechanical-fact authority;
- environment-execution validity authority;
- semantic-hypothesis generation;
- training-data transformation;
- model-training execution;
- evaluation aggregation;
- no scientific decision authority.

External or local semantic analyzers never become environment truth.

Builders, registries and trainers do not judge their own scientific
success.

## 9. Status vocabulary

The following statuses are used consistently:

- `COMPLETE`
- `COMPLETE_NO_GO`
- `IN_PROGRESS`
- `REJECTED`
- `INCOMPLETE`
- `HOLD`
- `HISTORICAL`
- `SUPERSEDED`
- `NOT_APPLICABLE`

`COMPLETE` means that the registered execution or audit finished. It
does not automatically mean the associated hypothesis was supported.

## 10. Source-of-truth hierarchy

When records disagree, use this order:

1. original server-side raw evidence;
2. original manifest, ledger and cryptographic seal;
3. deterministic audit output;
4. Round-1 Asset Registry;
5. component or hierarchical-analysis ledger;
6. project Experiment Ledger;
7. root README.

Higher-level summaries may not override lower-level evidence.

## 11. Preservation rules

The consolidation must not:

- rewrite historical commits;
- force-push;
- move raw server evidence;
- overwrite existing evidence files;
- regenerate historical strong-model outputs;
- rerun ALFWorld to repair historical evidence;
- change existing scientific hashes;
- relabel a rejected or incomplete analysis as complete;
- call provenance closure a hierarchical-analysis level;
- generate Failure Memory records.

Historical absolute server paths may be registered, but repository links
must use relative Markdown links where possible.

## 12. Small-module sequence

### Module 1 — Round-1 Navigation and Component Map

Creates:

- `docs/rounds/round1/README.md`
- `docs/rounds/round1/COMPONENT_REGISTRY.md`

It also adds only the minimum links needed to identify the Round-1
overview and component map.

### Module 2 — Hierarchical Analysis Asset Map

Creates:

- `docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`

It records Levels 1-6 and the builders, analyzers, verifiers, populations,
outputs and statuses within each level.

### Module 3 — Historical Asset Registry and Global Documentation Sync

Creates:

- `docs/rounds/round1/ASSET_REGISTRY.md`

Updates:

- `README.md`
- `docs/experiments/EXPERIMENT_LEDGER.md`
- `docs/code_map.md`
- `docs/protocol/MODULE_CLOSURE_POLICY.md`

It also checks all relative links and records the current active branch
and evidence-closure entry points.

## 13. Documentation Sync Check

Every later small-module closure checks:

1. parent major-module ledger;
2. Round-1 README;
3. Component Registry;
4. Asset Registry;
5. Hierarchical Analysis Ledger, when applicable;
6. Experiment Ledger, when scientific status changes;
7. Code Map, when active implementation changes;
8. root README, when top-level project status changes.

Each item is recorded as:

- `UPDATED`;
- `CHECKED_NO_CHANGE_REQUIRED`;
- `NOT_APPLICABLE`.

## 14. Acceptance criteria

The major module is complete only when:

- the root README reaches the correct Round-1 entry point;
- the Round-1 overview exposes the entire first-round workflow;
- every major component has a registered type, role, input, output,
  authority and status;
- Levels 1-6 are separately documented;
- the provenance audit remains separate from Levels 1-6;
- every major server asset has an identity and retention entry;
- relative links resolve;
- no historical scientific evidence changes;
- README, Experiment Ledger and Code Map reflect the same current state;
- every small module has its own commit, push and remote-equality proof.

## 15. Non-goals

This work does not:

- resume terminal provenance analysis;
- modify R132 scientific outputs;
- change the Round-1 NO-GO result;
- revise the hierarchical taxonomy;
- run a model or environment;
- train pi2;
- implement Failure Memory;
- decide the next scientific method.
