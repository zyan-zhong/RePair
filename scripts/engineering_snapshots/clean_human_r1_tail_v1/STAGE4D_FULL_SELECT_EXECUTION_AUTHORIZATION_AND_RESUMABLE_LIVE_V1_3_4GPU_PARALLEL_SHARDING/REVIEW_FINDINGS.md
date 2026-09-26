# Review Findings — Stage4D V1.3 4-GPU Parallel Sharding

## Scientific invariants retained

- fixed head unchanged: `ede426ffb069bd887bd3caf847add8193c801d60`
- Stage4C protocol SHA unchanged
- Stage4D binding SHA unchanged
- readiness receipt SHA unchanged
- execution authorization payload/hash unchanged
- 355 tasks / 5 seeds / 1775 pairs / 3550 condition cells unchanged
- T0 then T2 order retained within each pair
- I1 + RAW unchanged
- Memory OFF / Harness OFF unchanged
- existing historical cell execution spine reused by exact source SHA
- no second episode evaluator implemented
- result interpretation and promotion remain unauthorized

## Parallelization boundary

Parallelism is only across independent absolute schedule ordinals. A task-seed pair is never split across workers. The parent allocation is one node / four GPUs; four concurrent `srun --exclusive --gpus=1` steps provide scheduler-owned single-GPU isolation for the four workers.

Canonical receipt ledgers remain single-writer. Four workers write separate hash chains under shard-local roots. Canonical receipt chains are materialized only by the parent coordinator after all shard attempts pass identity and attempt-bundle audits.

## Existing evidence reuse

The canonical prefix is discovered from the existing T0 and T2 receipt ledgers and validated against the frozen schedule. The 102 pairs produced by Slurm job 156730 are therefore reused without being re-executed, while the code remains valid if the canonical prefix changes before submission.

## Runtime hardening retained

- `--export=NIL`
- explicit system PATH for gcc/ld
- vLLM usage stats disabled
- offline HF/Transformers mode
- run-partition vLLM / TorchInductor / Triton caches
- per-shard cache roots and TMPDIR
- no explicit CPU or memory request

## Failure boundaries

- a worker failure is infrastructure/execution failure; canonical scientific ledgers are not partially merged while workers are running;
- shard-local attempts and receipts remain available for exact resume;
- consolidation validates attempt bundles before copying them into the canonical tree;
- canonical append remains frozen-schedule ordered;
- a crash between T0 and T2 canonical append is recognized as a recoverable one-receipt consolidation state, not silently treated as a complete pair.
