#!/usr/bin/env bash

PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PACKAGE_ROOT"

CONDA_SH="/data/apps/miniforge3/25.11.0-1/etc/profile.d/conda.sh"
CONDA_ENV="/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312"

if test ! -f "$CONDA_SH"
then
  echo "STOP=CONDA_SH_MISSING:$CONDA_SH"
  exit 71
fi

. "$CONDA_SH"
conda activate "$CONDA_ENV"
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=CONDA_ACTIVATION_FAILED:$RC"
  exit "$RC"
fi

EXPECTED_APPROVAL="APPROVE_HUMAN_PILOT_STAGE0_OFFOFF_V1"
if test "${HUMAN_PILOT_STAGE0_EXECUTION_APPROVAL-}" != "$EXPECTED_APPROVAL"
then
  echo "STOP=EXPLICIT_HUMAN_PILOT_STAGE0_EXECUTION_APPROVAL_REQUIRED"
  echo "EXPECTED_APPROVAL_TOKEN=$EXPECTED_APPROVAL"
  exit 70
fi

bash ./00_VERIFY_PACKAGE.sh
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=PACKAGE_VERIFY_FAILED:$RC"
  exit "$RC"
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PACKAGE_ROOT"

for name in \
  OUTPUT_ROOT \
  REPRO_ROOT \
  SOURCE_ADAPTER_ROOT \
  NATIVE_ROOT \
  MAINLINE_ROOT \
  PREFLIGHT_ROOT \
  REVIEW_ROOT
do
  unset "$name"
done

python ./05_APPLY_GENERIC_SELECT_ARTIFACT_PATCH.py
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=GENERIC_SELECT_ARTIFACT_PATCH_FAILED:$RC"
  exit "$RC"
fi

python ./10_OFFLINE_PREFLIGHT.py
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=STAGE0_OFFLINE_PREFLIGHT_FAILED:$RC"
  exit "$RC"
fi

python ./20_PREPARE_EXECUTION_AUTHORIZATION.py
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=STAGE0_AUTHORIZATION_PREPARATION_FAILED:$RC"
  exit "$RC"
fi

FINAL_REVIEW="/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/HUMAN_PILOT_STAGE0_OFFOFF_CLOSEOUT_REVIEW_V1.zip"
if test -e "$FINAL_REVIEW"
then
  echo "STOP=STAGE0_FINAL_REVIEW_ALREADY_EXISTS:$FINAL_REVIEW"
  exit 61
fi

mkdir -p logs

LAST_JOB_FILE="logs/LAST_STAGE0_JOB_ID.txt"
if test -f "$LAST_JOB_FILE"
then
  PREVIOUS_JOB_ID="$(
    tr -d '[:space:]' < "$LAST_JOB_FILE"
  )"
  if test -n "$PREVIOUS_JOB_ID"
  then
    PREVIOUS_JOB_STATE="$(
      squeue         -h         -j "$PREVIOUS_JOB_ID"         -o '%T'         2>/dev/null |
      head -n 1
    )"
    if test -n "$PREVIOUS_JOB_STATE"
    then
      echo "STOP=STAGE0_PREVIOUS_JOB_STILL_ACTIVE"
      echo "PREVIOUS_JOB_ID=$PREVIOUS_JOB_ID"
      echo "PREVIOUS_JOB_STATE=$PREVIOUS_JOB_STATE"
      exit 63
    fi
  fi
fi

SBATCH_OUTPUT="$(
  sbatch \
    --export=NIL \
    --chdir="$PACKAGE_ROOT" \
    --output="$PACKAGE_ROOT/logs/human_pilot_stage0_%j.out" \
    --error="$PACKAGE_ROOT/logs/human_pilot_stage0_%j.err" \
    "$PACKAGE_ROOT/slurm/human_pilot_stage0_offoff.sbatch"
)"
RC=$?

echo "$SBATCH_OUTPUT"
echo "SBATCH_RC=$RC"
if test "$RC" -ne 0
then
  echo "STOP=STAGE0_SBATCH_FAILED"
  exit "$RC"
fi

JOB_ID="$(
  printf '%s\n' "$SBATCH_OUTPUT" |
  awk '/Submitted batch job/{print $4}'
)"
if test -z "$JOB_ID"
then
  echo "STOP=STAGE0_JOB_ID_NOT_FOUND"
  exit 62
fi
printf '%s\n' "$JOB_ID" > logs/LAST_STAGE0_JOB_ID.txt

echo "HUMAN_PILOT_STAGE0_SUBMITTED"
echo "JOB_ID=$JOB_ID"
echo "PARENT_CELL_COUNT=85"
echo "CANDIDATE_CELL_COUNT=85"
echo "TOTAL_CONDITION_CELL_COUNT=170"
echo "PAPER_EFFICACY_EVIDENCE=false"
echo "PROMOTION_ELIGIBLE=false"
