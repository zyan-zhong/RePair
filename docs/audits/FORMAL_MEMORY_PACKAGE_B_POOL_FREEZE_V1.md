# Formal Memory Package B — Outcome-Blind Pool Freeze V1

Code Approval parent:
`0da5e153d90552c4f9de4bac13d220ff9303f94c`

Pool freeze:
`55d16af9c5a73ea1620f054692efde41deedb711fd7ddd82c5018db85f97292d`

Query-candidate panel:
`c69b7bd69a45857e51796f22fddcf57d323c269a93bfffa27f98bb690f862b92`

Frozen before independent gold annotation and before any Formal-B retrieval score
or scientific outcome.

Design:
- exactly 30 distinct task/gamefile groups;
- exactly 10 groups each in Calibration DEV, Selection Validation, Safety Stress;
- one active-Memory source-provenance anchor group in each pool;
- the remaining 27 groups assigned by deterministic SHA-256 ordering and
  round-robin, with no gold or retrieval-score input;
- each source failure contributes only its final up to three policy-visible
  model-call states;
- candidate query IDs are validated against production FormalBQueryV1 identity;
- independent boundary authority artifacts are copied by verified SHA for later
  blinded gold annotation.

No gold label exists in this freeze.
No retrieval score was computed.
No scientific execution is authorized.
