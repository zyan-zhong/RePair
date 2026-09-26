# The validation reported in the paper

This directory is a reading index for an **executed** experiment, not a new run
request. It reuses R5 rollout/Analyzer evidence and adds zero formal campaign
rounds. Follow [settings](../../docs/repair/EXPERIMENTS.md) and
[results](../../docs/repair/RESULTS.md) before interpreting outputs.

| Step | Program or record |
|---|---|
| Framework roles | `src/pchsi/analyzer/`, `research_intelligence/`, `memory/` |
| Current source review / PRE | `strategy_planner.py` in indexed strategy package |
| Bounded interventions | `guarded_strategy.py`, `cue_strategy.py` |
| F0/F1 worker | `strategy_worker.py`, `strategy_gpu.py`; registered native H44 core |
| Full validation sequence | `one_validation.py`, `entry_v208.py` |
| Training materialization | `strategy_hooks.py`; indexed `training_binding/` and registered trainer sources |
| Selection policy / seed amendment | Indexed selection and single-seed recovery packages |
| Progress display | Indexed `progress_window` package |
| Executed hyperparameters | [training_configuration.json](../../paper/evidence/training_configuration.json) |
| Native training coverage | [supervision_coverage.json](../../paper/evidence/supervision_coverage.json) |
| Numerical evidence and recount | [paper/](../../paper/README.md) |

Exact package paths are in [COMPONENT_INDEX.json](../../runtime/COMPONENT_INDEX.json),
so readers need not infer a current package from directory names. Default scripts
in historical candidate directories may deliberately refuse execution; they are
preserved for provenance and are not the executed validation entry.

The measured candidate is rejected by OFF/OFF TRAIN_SELECT. The final RePair
benchmark and matched action-only experiment are not present as completed results.
