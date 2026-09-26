# Runtime + Researcher Activation V3 Implementation Plan

Base: `e64bc5efdcfd436bab807cd8519a3ffb7dd38746`. Reuse P2 transport and all deterministic Analyzer/Memory
assets. No second HTTP client.

## Task 1 — Freeze V3 identities, schemas, prompts and stage budgets
RED: missing stage rows, prompt/schema hash mismatch, A2/A3 reuse/memory violation.
GREEN: closed manifests and exact hashes.

## Task 2 — Bind existing P2 runtime assets
RED: missing/unhashed adapter/execute assets; direct-SDK fallback.
GREEN: locate, hash and report existing P2 adapter; fail closed on unknown interface.

## Task 3 — Implement scientific-unit and logical-call/attempt identities
RED: episode-only identity, retry counted as new scientific call, ambiguous resend.
GREEN: one logical outcome with explicit attempts and transmission state.

## Task 4 — Implement strict request rendering
RED: secret in request, mutable prompt/schema, tools, previous_response_id,
truncation or silent fallback.
GREEN: canonical request body and content-addressed projection.

## Task 5 — Implement no-clobber raw provenance recorder
RED: overwrite, missing request/response/usage/cost/latency/refusal.
GREEN: immutable call bundle and receipts.

## Task 6 — Implement task-access and Memory exposure gates
RED: teacher_call_permitted=false, A0/A1/A2 Memory, mismatched A1 bytes.
GREEN: exact access/SHA binding and A3-only higher-level Memory.

## Task 7 — Implement Analyzer stage orchestration
L/G/C/P/X, existing validators, no effect/training/promotion authority.

## Task 8 — Implement Human/API/Local Researcher data chain
Human PRE/POST no-clobber; API shadows cannot see corresponding Human record;
field adjudication; round-level split identity.

## Task 9 — ACT0 offline dry run
Render every stage; verify hashes, no secret, no network, no-clobber and invalid
fixtures. This is included in default RUN_ALL.

## Task 10 — ACT1 one-call DEV smoke
Explicit live authorization; source existing secret loader; P2 adapter only;
validate provider/model/fields/request ID/usage/raw evidence. No environment.

## Task 11 — ACT2 A0/A1 local pilot
4–8 DEV trajectories; same common evidence; frozen budgets; record invalid and
abstain outcomes; no claim.

## Task 12 — ACT3 A2/A3 + Memory + X pilot
A1 local bytes reused; A2 no Memory; A3 exact inputs + frozen Memory; independent
request-level X; no F0/F1.

## Task 13 — Runtime fixed-head review
Focused tests during development; one final native build + one full repository
regression. Export review bundle.

## Task 14 — Formal A0–A3 execution
Separate exact authorization after review. Common U_reg, K=1/ABSTAIN, full cost
ledger, no environment execution.

## Task 15 — Freeze ROUND_EVIDENCE_PACKAGE_V1
Bind formal outputs and metrics; prove future outcomes/current Human PRE/sealed
TEST details absent. Stop before Human Researcher PRE/F0F1.

## Test-time optimization
- Exact base head replaces repeated full baseline regressions.
- Baseline runs only `tests/analyzer` + `tests/cognitive_runtime`.
- Each task runs focused tests and compileall on changed modules.
- Native build and full repository pytest run once at final implementation seal.
- ACT stages run focused validators only; no repeated full suite.
- Resume by commit subject and clean-worktree identity.
- No new pytest-xdist dependency; correctness is not traded for speed.

## Formal DAG gate
A dedicated `FORMAL_ANALYZER_DAG_REGISTRY_V1` must prove complete `U_reg × {A0,A1,A2,A3}`, common evidence, byte-identical A1 reuse, and A3-only Memory before formal calls.
