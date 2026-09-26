#!/usr/bin/env bash

PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PACKAGE_ROOT"

APPROVAL_EXPECTED='APPROVE_HUMAN_T2_FORMAL_TRAINING_V1'

if test "${HUMAN_T2_FORMAL_TRAINING_EXECUTION_APPROVAL-}" != "$APPROVAL_EXPECTED"
then
  echo "STOP=EXPLICIT_FORMAL_TRAINING_EXECUTION_APPROVAL_REQUIRED"
  echo "EXPECTED_APPROVAL_TOKEN=$APPROVAL_EXPECTED"
  exit 70
fi

bash ./00_VERIFY_PACKAGE.sh
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=PACKAGE_VERIFY_FAILED:$RC"
  exit "$RC"
fi

export PYTHONPATH="$PACKAGE_ROOT"

python ./10_PREPARE_FORMAL_AUTHORIZATION.py
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=FORMAL_AUTHORIZATION_PREPARATION_FAILED:$RC"
  exit "$RC"
fi

env \
  -u OUTPUT_ROOT \
  -u REPRO_ROOT \
  -u SOURCE_ADAPTER_ROOT \
  -u NATIVE_ROOT \
  -u MAINLINE_ROOT \
  -u PREFLIGHT_ROOT \
  -u REVIEW_ROOT \
  PYTHONPATH="$PACKAGE_ROOT" \
  python \
  ./20_OFFLINE_FORMAL_TRAINING_PREFLIGHT.py

RC=$?
if test "$RC" -ne 0
then
  echo "STOP=FORMAL_TRAINING_OFFLINE_PREFLIGHT_FAILED:$RC"
  exit "$RC"
fi

bash -n slurm/human_t2_formal_training.sbatch
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=SBATCH_SYNTAX_FAILED:$RC"
  exit "$RC"
fi

TRAIN_OUT='/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_v1/human-t2-train17-continuation-v1-a000'
STAGE_ATTEMPT='/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_stage_attempts_v1/human-t2-train17-continuation-v1-a000'
REVIEW_ZIP='/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/ROUND_HUMAN_T2_FORMAL_TRAINING_REVIEW_V1.zip'

if test -e "$TRAIN_OUT"
then
  echo "STOP=AUTHORIZED_TRAINING_OUTPUT_ALREADY_EXISTS:$TRAIN_OUT"
  exit 61
fi

if test -e "$STAGE_ATTEMPT"
then
  echo "STOP=TRAINING_STAGE_ATTEMPT_ROOT_ALREADY_EXISTS:$STAGE_ATTEMPT"
  exit 62
fi

if test -e "$REVIEW_ZIP"
then
  echo "STOP=TRAINING_REVIEW_ZIP_ALREADY_EXISTS:$REVIEW_ZIP"
  exit 63
fi

mkdir -p logs
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=LOG_DIRECTORY_CREATE_FAILED:$RC"
  exit "$RC"
fi

AUTH_ROOT="/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_authorization_v1/human-t2-train17-continuation-v1-a000"
SUBMISSION_GUARD="$AUTH_ROOT/submission_guard_v1"

if test -e "$SUBMISSION_GUARD"
then
  echo "STOP=FORMAL_TRAINING_ATTEMPT_ALREADY_SUBMITTED_OR_GUARDED:$SUBMISSION_GUARD"
  if test -f "$SUBMISSION_GUARD/JOB_ID.txt"
  then
    cat "$SUBMISSION_GUARD/JOB_ID.txt"
  fi
  exit 65
fi

mkdir "$SUBMISSION_GUARD"
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=SUBMISSION_GUARD_CREATE_FAILED:$RC"
  exit "$RC"
fi

SBATCH_OUTPUT="$(
  sbatch \
    --export=NIL \
    --chdir="$PACKAGE_ROOT" \
    --output="$PACKAGE_ROOT/logs/human_t2_formal_training_%j.out" \
    --error="$PACKAGE_ROOT/logs/human_t2_formal_training_%j.err" \
    "$PACKAGE_ROOT/slurm/human_t2_formal_training.sbatch"
)"
RC=$?

echo "$SBATCH_OUTPUT"
echo "SBATCH_RC=$RC"

if test "$RC" -ne 0
then
  rmdir "$SUBMISSION_GUARD" 2>/dev/null
  echo "STOP=HUMAN_T2_FORMAL_TRAINING_SUBMISSION_FAILED"
  exit "$RC"
fi

JOB_ID="$(
  printf '%s\n' "$SBATCH_OUTPUT" |
  awk '/Submitted batch job/{print $4}'
)"

if test -z "$JOB_ID"
then
  echo "STOP=FORMAL_TRAINING_JOB_ID_NOT_FOUND"
  exit 64
fi

printf '%s\n' "$JOB_ID" \
  > logs/LAST_HUMAN_T2_FORMAL_TRAINING_JOB_ID.txt

printf '%s\n' "$JOB_ID" \
  > "$SUBMISSION_GUARD/JOB_ID.txt"

echo "HUMAN_T2_FORMAL_TRAINING_SUBMITTED"
echo "JOB_ID=$JOB_ID"
echo "OPTIMIZER_STEPS=3"
echo "TARGET_LOSS_TOKENS=151"
echo "DIAGNOSTIC_ONLY=true"
echo "PROMOTION_ELIGIBLE=false"
