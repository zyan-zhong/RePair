# V1.23.2X — Dynamic Strong Planner PRE resume-stable Memory authority + autonomous infra recovery

This package is a narrow continuation of V1232V/V1232W. It does **not** rerun Analyzer, rebuild the Dynamic Planner pair universe, execute ALFWorld, or train a policy.

## Root cause fixed

`researcher_memory_candidates()` scans Researcher Memory views before the first V1232V output root exists. On resume, the already-materialized current-round `RESEARCHER_MEMORY_VIEW_V1.json` is visible to that scan. Its stable Memory payload is identical, but it is a **derived current-round view**, not a predecessor Memory authority. Counting it again changes `researcher_memory_candidate_view_count`, causing exact activation-artifact replay to fail even though all scientific inputs are unchanged.

V1232X builds the current-round evidence identity first, then semantically partitions matching Memory views:

- exact current-round-evidence-bound views -> derived/self outputs, excluded from predecessor authority discovery;
- all other current-snapshot round-planning views -> predecessor candidates;
- predecessor candidates must still collapse to exactly one stable Memory signature.

The fix is semantic and authority-driven: no path order, mtime, latest-file rule, manual selection, or current live cardinality is used.

## Recovery behavior

After exact V1232V activation identity is restored, V1232X continues the already-built V1232W historical infra classifier and bounded new-remediation-logical-call policy. Same-logical-call resend remains forbidden.

## Execution

```bash
PCHSI_PYTHON=/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python \
  bash ./RUN_V1232X.sh \
  --v1232u-output-root <V1232U_ROOT> \
  --authorize-bounded-infrastructure-recovery
```
