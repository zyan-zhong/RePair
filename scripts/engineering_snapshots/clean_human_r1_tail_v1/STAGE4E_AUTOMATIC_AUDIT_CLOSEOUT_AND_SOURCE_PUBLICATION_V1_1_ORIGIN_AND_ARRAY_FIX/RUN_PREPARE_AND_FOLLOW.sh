#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
PY="${STAGE4E_PYTHON:-/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python}"
JOB_ID="${1:-156834}"
case "$JOB_ID" in ''|*[!0-9]*) echo 'STOP=NUMERIC_JOB_ID_REQUIRED' >&2; exit 70;; esac
bash ./00_VERIFY_PACKAGE.sh
LOG_ROOT="/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/logs/stage4e_automatic_closeout_v1"
mkdir -p "$LOG_ROOT"
LOG="$LOG_ROOT/closeout_from_${JOB_ID}_$(date -u +%Y%m%dT%H%M%SZ)_$$.log"
echo "STAGE4E_DRIVER_LOG=$LOG"
"$PY" -u -m stage4e.driver prepare-follow-publish --job-id "$JOB_ID" 2>&1 | tee "$LOG"
