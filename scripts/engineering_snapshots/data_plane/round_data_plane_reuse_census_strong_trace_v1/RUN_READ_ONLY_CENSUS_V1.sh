#!/usr/bin/env bash

PY="/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python"
SCRIPT_ROOT="$(cd "$(dirname "$0")" && pwd -P)"

export PYTHONDONTWRITEBYTECODE=1

"$PY" \
  "$SCRIPT_ROOT/run_read_only_census_v1.py"

RC=$?

echo "ROUND_DATA_PLANE_READ_ONLY_CENSUS_RC=$RC"

exit "$RC"
