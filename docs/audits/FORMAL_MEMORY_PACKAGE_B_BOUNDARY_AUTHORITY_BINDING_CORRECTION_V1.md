# Formal Memory Package B — Boundary Authority Binding Correction V1

Timing: before any independent-gold annotation, Formal-B retrieval score, selected
threshold, or scientific outcome.

The first blinded-packet builder stopped because it required each boundary
`registration_id` to appear literally in the referenced authority artifact bytes.

That requirement is not part of the frozen Memory boundary contract.

The actual frozen binding is:
- `boundary_authority = REGISTERED_BOUNDARY`;
- `origin_artifact_ref.source_kind = REGISTERED_BOUNDARY_ARTIFACT`;
- `origin_artifact_ref.source_id = registration_id`;
- `origin_artifact_ref.source_sha256` binds the authority artifact bytes.

V2 therefore verifies the structural source-id/registration-id equality and exact
artifact SHA, while retaining the stronger independent check that each
`condition_text` used by the annotator exists verbatim in the authority artifact.

No gold label or Formal-B result existed when this correction was made.
