# N.4.1 live failure and bounded recovery scope

Observed N.4 live terminal:

- package verification: 63 passed;
- exact registered capsule-missing root confirmed;
- exact original missing path was the current-round `V1232H_REPAIRED_ROLLOUT_SOURCE_CAPSULE.zip`;
- native CPU preflight started;
- registered historical execution worktree Git status check returned the package timeout sentinel `124 / TIMEOUT`;
- no native preflight PASS was published;
- no new Slurm array was submitted by N.4;
- no R2 environment rollout, Provider call, Analyzer entry, policy training, Memory update, or scientific attempt was consumed by that N.4 invocation.

Historical precedent: Canonical V181 / `STRONG_PRIMARY_R1_REPO_PREFLIGHT_TIMEOUT_RESILIENCE_V1_31_0` classified the same operational family as slow-filesystem Git preflight timeout and froze a narrow recovery pattern: retry identical Git argv exactly once only on TimeoutExpired, with the acceptance criterion unchanged; ordinary Git failures remain terminal. N.4.1 applies this only to the N.4 native worktree `git status --porcelain=v1 --untracked-files=all` check.

This package does not claim the registered worktree is clean until the server command completes and returns empty output. It does not claim R2 rollout success until the live producer publishes the existing scientific handoff contract.
