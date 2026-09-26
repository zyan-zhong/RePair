# Failure Memory V1 — Post-hoc Trajectory Analysis Archive

This directory archives the post-hoc descriptive trajectory/process analysis
generated after the registered Failure Memory V1 scientific result seal.

Scientific status remains unchanged:

- Q1 = NOT_SUPPORTED
- Q2 = NOT_SUPPORTED
- Q3 = NOT_SUPPORTED
- Q4 = Analyzer + same-state verifier handoff
- Q5 = verified training + Memory-OFF/Harness-OFF handoff

The analysis is descriptive only. It did not call a model or environment and
did not write a scientific authority.

Primary files:

- `POSTHOC_TRAJECTORY_ANALYSIS_SUMMARY.md`
- `paired_process_summary.csv`
- `paired_task_family_summary.csv`
- `paired_process_deltas.csv`
- `cell_process_metrics.csv`
- `top_process_changes.csv`

The sealed run did not retain trustworthy step-level action traces for these
cells (`trace_linked_cell_count=0`), so `trace_pair_deltas.csv` is intentionally
empty and no loop/revisit/edit-distance claim is authorized.
