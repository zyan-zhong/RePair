# Exact producer fresh-round scope repair

Goal: extend the reviewed V1232K worker/finalizer at the fresh-round request boundary, not build another rollout evaluator.

1. Preserve all supplied evidence. Verify export hashes and reviewed producer file hashes.
2. Reproduce on the original code: ordinal zero rejected; finalizer uses old capsule round ID; missing capsule on the generated runner. Read the actual shard fatal receipt before authorizing server recovery.
3. Add one shared request/schedule binder used by both original worker and finalizer. Keep the original capsule immutable; scope it by an independently validated current request; do not rename or rewrite prior results.
4. Native CPU preflight: exact worktree HEAD and source hashes, request/runtime/memory/train/profile consistency, native task-file validation and deterministic schedule, capsule safety, original failure/no-work proof, one-submission journal.
5. A separate infra output root retains the same scientific request. Reuse original array argv builder, gate, evaluator, runtime, finalizer and V1232Q. No old readiness, terminals or attempt directories are read as inputs.
6. At-most-one new submission, independent detached monitoring, durable fatal handling, bounded timeouts, at-most-one existing Analyzer reentry. No retry after an ambiguous send or second gate failure. Full autonomous campaign remains unreleased.
7. Tests run in isolated temporary roots with synthetic resource/task fixtures and original source code. They are not scientific evidence. Publish exact diff and append-only ledger/cache records.

Current critical scope correction: V1232Q stops after local-wave/group-prep (and returns 20 on censorship). It does not autonomously drive the entire G/C/P/X/PRE/POST/train loop. Never label its success a max-10 release.
