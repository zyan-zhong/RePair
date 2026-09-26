# Paper-critical causal round execution V1.23.3H2

## Released scope

This package is released for the **current accepted PRE causal round only**:

`exact replay -> governed per-step Memory -> typed short-option F0/F1 -> independent verifier -> one Strong Planner POST -> typed TRAIN/NO_TRAIN terminal`.

It does **not** execute optimizer steps, OFF/OFF evaluation, next-round launch, or max-10.  A POST `TRAIN` result emits `CURRENT_VERIFIED_TRAINING_HANDOFF_V1.json` for the already-existing strategy-bearing training pipeline; it does not invent a training recipe.

## Reused authorities

The input is the immutable E actor/runtime recovery archive.  Current state counts, branch counts, seeds, candidate identities, task/gamefile identities, policy identity, Memory snapshot and runtime are read from that archive and its accepted PRE handoff.  They are not production constants.

The native execution reuses the exact actor policy request/response path, source-state replay, ALFWorld adapter, frozen Memory `prepare/process`, paired-effect classifier, five-repeat aggregation, cognitive runtime, P2 transport and Strong POST finalizer already captured in the evidence archive/package.

## Scientific boundaries

- F0 is parent-policy continuation with no candidate intervention.
- F1 is the selected repair followed by the same parent policy.
- The current experiment therefore does not establish A3-vs-A2 superiority; the scope notice is carried into POST.
- Both branches use the same frozen Memory mechanism but query their own branch state.
- Unsupported selected option semantics remain protocol missingness.  No top-up, candidate replacement or first-action fallback is permitted.
- Infrastructure/protocol invalidity never becomes scientific `NO_TRAIN`.
- A zero-Benefit scientifically valid round may produce the existing `NO_TRAINING_UPDATE_V1`.
- A `TRAIN` POST produces a typed pending training handoff only. Optimizer execution is outside this release.

## Runtime behavior

`RUN_CURRENT_ROUND.sh --execute-current-round` validates the package, materializes the receipt-derived plan, and detaches one resident controller.  The controller submits one Slurm allocation, launches the frozen policy service in that same allocation, executes the current branch universe, independently re-verifies persisted branch receipts, tears down the service, then issues at most one Strong POST logical call.

Same logical calls/branches are never blindly resent.  An existing terminal is adopted.  A partial submission/execution intent is fail-closed.

## Not released

- task-policy training / optimizer execution;
- OFF/OFF candidate evaluation or promotion;
- next-round launch;
- max-10 campaign.

These remain false until separate live evidence exists.


## H2 mechanical recovery boundary

H2 fixes only the engine-profile receipt/cluster-policy import seam exposed before Slurm submission.
It reuses the durable engine-profile receipt directly (no rediscovery), derives GPU count from tensor parallel size,
uses `inference_partition_default` from the frozen site policy, and creates a deterministic operational recovery
root only when the predecessor diagnostic proves zero scheduler/model/environment/training side effects.
A predecessor with `SBATCH_SUBMISSION_INTENT.json` or `GPU_JOB_TERMINAL.json` is never automatically retried.
