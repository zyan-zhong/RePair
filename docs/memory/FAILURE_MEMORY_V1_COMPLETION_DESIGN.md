# Failure Memory V1 Completion — Corrected Design

Canonical base: `da505ae55f326a44245c9703847d94edfdbcf775`.

## Scope

Failure Memory V1 owns:

- provenance-grounded procedural Failure Experience records;
- fact / hypothesis / recovery-proposal authority separation;
- retrieval keys, projections, token packing and immutable snapshots;
- Policy-safe direct exposure;
- bounded Analyzer candidate-support export;
- train-side Researcher evidence export;
- append-only within-round shadow maintenance;
- verifier-effect ingestion;
- promotion, quarantine, descriptive-only and staging dispositions;
- typed optional training-evidence export port;
- Stage 0 / 1A / 1B / 2 / 3 scientific program contracts;
- a truthful Q1–Q5 evidence matrix.

Failure Memory V1 does **not** implement:

- a Hierarchical Analyzer algorithm;
- a Training Researcher / Planner algorithm;
- policy training;
- OFF/OFF evaluation execution;
- the outer research loop.

Those components connect through frozen ports after their own design, implementation,
Code Approval and scientific execution gates.

## Three consumer views

`Policy exposure gate != Analyzer candidate access != Researcher evidence access`.

### Task Policy

At most one Policy-safe FM2/FM3 projection. It may abstain. It never receives rank,
score, record identity, raw provenance, source task/attempt/gamefile, effect/training
labels, formal gold, or held-out identity.

### Hierarchical Analyzer export

Bounded top-k governed candidates, without the final Policy exposure threshold. It
may receive rank/score, applicability/release/non-applicability, typed hypotheses,
recoveries, counterevidence, effect/harm status, evidence SHA and completeness. It
has no direct action or Benefit/Harm authority.

### Training Researcher export

Full governed records require explicit `TRAIN_MEMORY_SOURCE` authority binding.
Round evidence may include Analyzer and F0/F1 references, NO-GO/regression, costs,
historical research evidence and held-out aggregates. Per-task held-out trajectories,
actions, menus, answers and gamefile identities are forbidden.

## Round maintenance

The active snapshot is immutable within a round. New evidence is append-only shadow
evidence and cannot be read back during that round.

Between rounds:

- clean complete train-side Benefit → next-round promotion;
- Harm → quarantine;
- Neutral → descriptive-only;
- Uncertain → staging/unresolved;
- infrastructure incident → no scientific outcome;
- `TRAIN_RETRIEVAL_DEV` → shadow-only;
- `valid_seen`, `valid_unseen`, formal evaluation → no writeback.

## Scientific program

- Stage 0: quality, leakage, retrieval, applicability, access, abstention, tokens and
  cost diagnostics.
- Stage 1A: same-source-state Memory OFF versus one frozen projection.
- Stage 1B: frozen-policy FM0/FM1/FM2/FM3 task-success experiment.
- Stage 2: controlled multi-round external-Memory accumulation with fixed policy and
  method.
- Stage 3: fully frozen valid_seen / valid_unseen formal evaluation with no
  adaptation or writeback between splits.

## Current scientific truth

- Q1: OPEN. A0 is local Neutral-only evidence.
- Q2: PARTIAL local null. No general representation-superiority claim.
- Q3: MIXED. Policy-direct B is safe-by-abstention with zero coverage.
- Q4: OPEN. External Analyzer plus real same-state F0/F1 required.
- Q5: DEFERRED optional parametric internalization extension.

Engineering tests never upgrade these statuses.
