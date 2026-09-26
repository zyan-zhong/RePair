# Formal Memory Package B — Gold Authority Correction V1

Correction authority:
`cf2c56f8f41b4babf15e0d78b2d2bfc24d03b6073327cfffdb5df80947d6b610`

Timing:
before any Formal-B retrieval score, threshold selection, Calibration outcome,
Validation outcome, or Safety Stress outcome.

## Preserved

- retriever implementation: unchanged;
- retriever scoring interface: unchanged;
- frozen 10/10/10 task/gamefile-group pool membership: unchanged;
- Round1 annotation preserved as VALID_DIAGNOSTIC / NOT_FINAL_GOLD.

## Newly audited query timing

The original candidate builder reconstructed interface feedback from the same
ActionTrace's post-generation `feedback_code`. Repository execution semantics use
`PolicyCallEvidenceV1.interface_feedback_before` as the exact policy-call input.

Timing mismatches found: `20`.

The corrected candidate population is rebuilt only from exact
`PolicyCallEvidenceV1` pre-generation inputs, while preserving the already-frozen
group pools. Corrected query count: `90`.

## V2 gold authority

Independent reference annotators receive:
- exact public task goal;
- exact immediately preceding rejected nonexecuted action when current feedback
  proves such a preceding failure exists;
- mechanically bound evidence hashes;
- the frozen policy-visible observation/history/menu/feedback.

The frozen retriever still receives only its original scoring visibility:
observation + executed history + interface feedback.

Every Memory/query therefore receives two separate annotations:
- REFERENCE_APPLICABILITY;
- RETRIEVER_OBSERVABILITY.

Two independent full-population passes are mandatory:
- Pass A: `346dd8d1dcd23a401ead6f88b0bf47199f0a2aa6f8004f6174d067efaf029e3f`;
- Pass B: `d2d6481b8a8772f79798fafc49fb4623353bd6ec14ecc1146a02897cb2eac473`.

Passes use independent query ordering and Memory aliases. They must not see each
other's annotations. A registered adjudication pass is mandatory before final gold.

Only after final gold freeze may the pool map be revealed to an independent
prerequisite auditor.

Post-gold prerequisites:
- every pool: >=1 reference-positive and >=1 reference-abstain row;
- Calibration and Validation: >=1 positive whose REFERENCE_APPLICABILITY is
  APPLICABLE and RETRIEVER_OBSERVABILITY is OBSERVABLE.

If any prerequisite fails: HARD STOP and open a versioned query/pool amendment
before any retrieval scoring.

Calibration is currently FORBIDDEN.
