# Clean Experiment Data Access Policy V1

All future adaptive scientific work is train-only.

ALFWorld `train` is partitioned before clean execution into three disjoint
governance pools:

- `TRAIN_UPDATE`: rollout collection, failure mining, Analyzer, Memory,
  Research Planner, same-state F0/F1, policy training, and localization
  supervision.
- `TRAIN_SELECT`: internal parent/candidate selection and promote/rollback only.
  It never enters policy training or adaptive diagnosis.
- `TRAIN_AUDIT`: role-takeover audit and calibration only. It never enters
  policy training.

`valid_seen` and `valid_unseen` are benchmark-only. They may be executed only by
the benchmark evaluator after the relevant comparison checkpoints and analysis
protocol are frozen. Detailed benchmark evidence cannot be released to Analyzer,
Memory, Research Planner, F0/F1, policy training, localization supervision, or
the internal promotion gate.

The Stage 0 pilot used historically exposed valid-unseen material and therefore
remains permanently segregated as engineering provenance.

A clean experiment may reuse Stage 0 generic engineering assets but may not
reuse Stage 0 task-specific semantic evidence.
