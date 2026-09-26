# Failure Memory V1 Live Closure Design V2

Status: `DESIGN_APPROVED_FAILURE_MEMORY_SCIENTIFIC_AUTHORITY_HARDENING_V1`

## Scope

This package completes only Memory-owned work:

- frozen-policy FM0/FM1/FM2/FM3 evaluation;
- controlled multi-round immutable-snapshot evaluation;
- one frozen valid_seen/valid_unseen formal package;
- per-cell Policy, Analyzer and Training Researcher Memory packs;
- no same-round Memory readback and no evaluation writeback;
- independently recomputed Q1--Q3 authorities;
- paper tables and bounded narrative artifacts;
- strict Q4 and Q5 handoffs.

It does not implement the Hierarchical Analyzer or Training Researcher, does not
train a policy, and cannot close Q4 or Q5.

## Execution boundary

The package supplies the Code-Approved live-stage orchestrator.  The server must
bind a separately reviewed cell executor to the frozen executor contract.  The
cell executor reports only mechanical outcomes; it cannot report scientific
question dispositions.  Stage-level decisions are recomputed from the complete
registered cell census.

## Role separation

- Task Policy receives only Policy-safe projections.
- Hierarchical Analyzer receives bounded historical candidate evidence.
- Training Researcher receives governed train-side and round evidence.
- Environment/same-state verifier remains Benefit/Harm authority.

## Round governance

Each round uses exactly one immutable active snapshot.  New evidence is not
readable during the same round.  Evaluation cells may not write back into active
Memory.  Harm is quarantined; formal evaluation has no Memory writeback.
