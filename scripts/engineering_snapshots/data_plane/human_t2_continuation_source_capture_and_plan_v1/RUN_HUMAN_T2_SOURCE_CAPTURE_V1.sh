#!/usr/bin/env bash

PY="/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python"
SCRIPT_ROOT="$(cd "$(dirname "$0")" && pwd -P)"

export PYTHONDONTWRITEBYTECODE=1

"$PY" \
  "$SCRIPT_ROOT/collect_human_t2_sources_v1.py"

RC=$?

echo "HUMAN_T2_SOURCE_CAPTURE_RC=$RC"

exit "$RC"
