# N4.2 live failure and recovery scope

Observed server N4.1 terminal:

- package verification: 66 passed
- exact original missing capsule path: confirmed
- native CPU preflight entered
- whole-worktree `git status --porcelain=v1 --untracked-files=all` timed out on both attempts
- no fresh R2 Slurm array was submitted by N4.1
- no R2 TRAIN_UPDATE rollout/evidence/Analyzer/training was produced

Canonical historical correction:

V181 / V1.31 did not freeze a whole-worktree `git status` scan. It froze an exact untracked-runtime-surface query:

`git ls-files --others --exclude-standard -- <runtime surfaces>`

with an identical-argv retry only after TimeoutExpired and a 180-second retry timeout. N4/N4.1 therefore drifted from the historical acceptance surface by broadening the filesystem scan.

N4.2 restores bounded runtime-surface checks. The same active validator is used by native CPU preflight, shard worker, the legacy formal producer entrypoint, Analyzer API preflight, and the post-rollout Analyzer revalidation. Scientific request, parent policy, Memory, schedule, capsule, and resource authorities are unchanged.

This package does not claim server live recovery until the server run produces a valid R2 rollout handoff.
