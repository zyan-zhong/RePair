#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
PY="${STAGE4E_PYTHON:-/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python}"
bash ./00_VERIFY_PACKAGE.sh
LOG_ROOT="/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/logs/stage4e_automatic_closeout_v1"
mkdir -p "$LOG_ROOT"
LOG="$LOG_ROOT/single_owner_consolidation_156934_$(date -u +%Y%m%dT%H%M%SZ)_$$.log"
echo "STAGE4E_CONTINUATION_LOG=$LOG"
"$PY" -u ./continue_closeout.py "$@" 2>&1 | tee "$LOG"
