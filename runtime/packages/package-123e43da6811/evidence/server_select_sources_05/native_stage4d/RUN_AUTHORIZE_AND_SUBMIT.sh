#!/usr/bin/env bash
set -euo pipefail
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PACKAGE_ROOT"
PY="/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python"
APPROVAL="${STAGE4D_FULL_SELECT_EXECUTION_APPROVAL-}"
EXPECTED="APPROVE_STAGE4D_FULL_SELECT_EXECUTION_V1"
if test "$APPROVAL" != "$EXPECTED"; then
  echo "STOP=EXPLICIT_STAGE4D_FULL_SELECT_EXECUTION_APPROVAL_REQUIRED"
  echo "EXPECTED_APPROVAL_TOKEN=$EXPECTED"
  exit 70
fi
bash ./00_VERIFY_PACKAGE.sh
AUTH_OUT="$($PY -m stage4d_full.authorize --approval "$APPROVAL")"
printf '%s\n' "$AUTH_OUT"
EXECUTION_ROOT="$(printf '%s\n' "$AUTH_OUT" | awk -F= '/^STAGE4D_EXECUTION_ROOT=/{print $2}')"
if test -z "$EXECUTION_ROOT"; then
  echo "STOP=STAGE4D_EXECUTION_ROOT_NOT_FOUND"
  exit 71
fi
if test -f "$EXECUTION_ROOT/STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1.json"; then
  echo "STOP=STAGE4D_FULL_SELECT_ALREADY_COMPLETE"
  exit 72
fi
mkdir -p "/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/logs/stage4d_existing_select_live_execution_v1"
LAST="$EXECUTION_ROOT/LAST_JOB_ID.txt"
if test -f "$LAST"; then
  PREV="$(tr -d '[:space:]' < "$LAST")"
  STATE="$(squeue -h -j "$PREV" -o '%T' 2>/dev/null | head -n 1 || true)"
  if test -n "$STATE"; then
    echo "STOP=PREVIOUS_STAGE4D_FULL_SELECT_JOB_ACTIVE"
    echo "PREVIOUS_JOB_ID=$PREV"
    echo "PREVIOUS_JOB_STATE=$STATE"
    exit 73
  fi
fi
LOG_ROOT="/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/logs/stage4d_existing_select_live_execution_v1"
SBATCH_OUT="$(sbatch --export=NIL --chdir="$PACKAGE_ROOT" --output="$LOG_ROOT/full_select_%j.out" --error="$LOG_ROOT/full_select_%j.err" "$PACKAGE_ROOT/slurm_template.sh" "$EXECUTION_ROOT")"
printf '%s\n' "$SBATCH_OUT"
JOB_ID="$(printf '%s\n' "$SBATCH_OUT" | awk '/Submitted batch job/{print $4}')"
if test -z "$JOB_ID"; then
  echo "STOP=STAGE4D_FULL_SELECT_JOB_ID_NOT_FOUND"
  exit 74
fi
printf '%s\n' "$JOB_ID" > "$LAST"
echo "STAGE4D_FULL_SELECT_SUBMITTED"
echo "JOB_ID=$JOB_ID"
echo "STAGE4D_EXECUTION_ROOT=$EXECUTION_ROOT"
echo "AUTHORIZED_TOTAL_CONDITION_CELLS=3550"
echo "RESULT_INTERPRETATION_AUTHORIZED=false"
echo "PROMOTION_AUTHORIZED=false"
