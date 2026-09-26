# Stage4D Full SELECT V1.3 — 4×A800 Parallel Sharding

## Purpose

This package is an execution-only acceleration of the already authorized Stage4D full SELECT universe.
It does **not** change the scientific protocol, binding, candidate, tasks, seeds, interface profile, Memory/Harness state, evaluator, or result authority.

Frozen scientific universe:

- binding SHA-256: `4ab7942b2c66238cb3833bdb04eb7f7ca23b52d10c388575aaf1bd272dfc100d`
- execution authorization SHA-256: `978ab39389d447b74b1a1acf653619ff437c0d341c9fe76b72236dd8f5fd865b`
- tasks: 355
- seeds: 17, 31, 47, 73, 101
- paired task-seed cells: 1775
- conditions: T0 then T2 within every pair
- total condition cells: 3550
- I1 + RAW
- Memory OFF
- Harness OFF
- result interpretation: not authorized
- promotion: not authorized

The existing canonical execution root is reused. The program discovers the already completed canonical paired prefix from the existing T0/T2 receipt ledgers; it does not hard-code the observed 102-pair prefix from job 156730.

## Parallel execution design

The Slurm allocation requests one node with 4 A800 GPUs. The parent coordinator starts four concurrent `srun --exclusive --gpus=1` job steps. Slurm therefore assigns exactly one GPU to each worker step and sets that step's `CUDA_VISIBLE_DEVICES`; the package does not guess or remap physical GPU indices itself.

Remaining schedule ordinals are assigned deterministically by:

`shard_id = absolute_schedule_ordinal % 4`

Each worker preserves the existing pair-local order:

`T0 -> T2`

Workers never append to the canonical `execution/t0/cell_receipts.jsonl` or `execution/t2/cell_receipts.jsonl`. Each worker writes an independent append-only hash chain under:

`parallel_v1/shard_<id>/execution/{t0,t2}`

After all four shards are complete, the coordinator:

1. validates every shard receipt against the exact frozen schedule;
2. audits every referenced published attempt bundle with the existing attempt auditor;
3. copies attempt directories into the existing canonical evaluator roots with no-clobber exact-tree verification;
4. rebuilds the canonical receipt hash chains in frozen schedule order;
5. emits the same `STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1.json` expected by Stage4E.

Thus Stage4E does not need a parallel-specific result format.

## Resources

The generated job uses only:

```bash
#SBATCH -p gpu_a800
#SBATCH --nodes=1
#SBATCH --gpus=4
#SBATCH --time=03:30:00
```

No CPU or memory request is present.

Runtime caches and TMPDIR are isolated per shard. The submission still uses `--export=NIL` and relies on Slurm-provided job variables plus explicit runtime environment restoration.

## Server procedure

Upload the ZIP into:

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts`

Verify the ZIP SHA shown in the accompanying response, unzip it, enter the package directory, then run:

```bash
bash ./00_VERIFY_PACKAGE.sh
```

Submit with the already frozen approval token:

```bash
export STAGE4D_FULL_SELECT_EXECUTION_APPROVAL=APPROVE_STAGE4D_FULL_SELECT_EXECUTION_V1
bash ./RUN_AUTHORIZE_AND_SUBMIT.sh 2>&1 | tee stage4d_full_select_submit_v1_3.log
```

The package reuses the existing authorization root and refuses to submit while a previous Stage4D full SELECT job is active.

## Expected completion

Successful one-job completion ends with:

```text
STAGE4D_FULL_SELECT_EXECUTION_COMPLETE
T0_CELL_COUNT=1775
T2_CELL_COUNT=1775
TOTAL_CONDITION_CELL_COUNT=3550
PARALLEL_SHARD_COUNT=4
RESULT_INTERPRETATION_AUTHORIZED=false
PROMOTION_AUTHORIZED=false
NEXT_GATE=STAGE4E_EXISTING_SELECT_RESULT_AUDIT
```

If the 3h15 worker budget is insufficient for a long-tail shard, the job exits cleanly at pair boundaries with `STAGE4D_FULL_SELECT_EXECUTION_GRACEFUL_PARTIAL`; rerunning the same package resumes shard-local receipts without rerunning completed cells.
