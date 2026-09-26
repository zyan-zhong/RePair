# Formal Memory Package B — Minimal Q3 Protocol V1

Protocol authority: `f7b2a114860154abf1722c739fd0c1955dd5210fb70b7510bef8bb6cdbb2d6fb`

Purpose:
validate only the minimum Memory function needed by the paper's Q3 evidence:
retrieve relevant historical Failure Experience and avoid exposing wrong or
non-applicable Memory.

Kept unchanged:
- Code-Approved Formal-B retriever;
- CASEFOLD_WORD_JACCARD_V1;
- threshold grid;
- applicability gate;
- corrected 90 exact policy-call query identities;
- frozen 10/10/10 task/gamefile-group pools;
- active 3-record Memory snapshot.

Simplification:
- no LLM/API annotator;
- no judge/adjudicator agent;
- no additional Memory intelligence;
- independent reference labels are mechanically derived from the already-registered
  applicability boundaries and mechanically bound factual sidecar;
- retriever observability is recorded only as a diagnostic limitation, not another
  prerequisite layer.

Hard pre-score gate:
every pool must contain at least one mechanically reference-positive row and at
least one reference-abstain row. Otherwise stop before scoring.

If the gate passes, this package completes:
Calibration -> Selection Validation -> Registered Safety Stress -> byte-identical
recompute -> result seal.

Formal B remains Q3 support only and is not causal Benefit/Harm authority.
