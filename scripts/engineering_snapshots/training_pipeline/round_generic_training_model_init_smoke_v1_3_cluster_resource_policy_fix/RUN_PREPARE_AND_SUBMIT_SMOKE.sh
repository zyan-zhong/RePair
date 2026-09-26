#!/usr/bin/env bash

PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
EXPECTED_PACKAGE_ROOT_LOGICAL="/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/round_generic_training_model_init_smoke_v1_3_cluster_resource_policy_fix"

if test ! -d "$EXPECTED_PACKAGE_ROOT_LOGICAL"
then
  echo "STOP=EXPECTED_PACKAGE_ROOT_MISSING:$EXPECTED_PACKAGE_ROOT_LOGICAL"
  exit 49
fi

EXPECTED_PACKAGE_ROOT_PHYSICAL="$(
  realpath -e "$EXPECTED_PACKAGE_ROOT_LOGICAL"
)"
RC=$?

if test "$RC" -ne 0
then
  echo "STOP=EXPECTED_PACKAGE_ROOT_CANONICALIZATION_FAILED:$RC"
  exit "$RC"
fi

if test ! "$PACKAGE_ROOT" -ef "$EXPECTED_PACKAGE_ROOT_LOGICAL"
then
  echo "STOP=PACKAGE_ROOT_IDENTITY_MISMATCH:$PACKAGE_ROOT:$EXPECTED_PACKAGE_ROOT_LOGICAL"
  echo "EXPECTED_PACKAGE_ROOT_PHYSICAL=$EXPECTED_PACKAGE_ROOT_PHYSICAL"
  exit 50
fi

echo "PACKAGE_ROOT_IDENTITY_PASS"
echo "PACKAGE_ROOT_PHYSICAL=$PACKAGE_ROOT"
echo "PACKAGE_ROOT_LOGICAL=$EXPECTED_PACKAGE_ROOT_LOGICAL"
echo "EXPECTED_PACKAGE_ROOT_PHYSICAL=$EXPECTED_PACKAGE_ROOT_PHYSICAL"

cd "$PACKAGE_ROOT"

bash ./00_VERIFY_PACKAGE.sh
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=PACKAGE_VERIFY_FAILED:$RC"
  exit "$RC"
fi

export PYTHONPATH="$PACKAGE_ROOT"
python ./10_OFFLINE_PREFLIGHT.py
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=OFFLINE_PREFLIGHT_FAILED:$RC"
  exit "$RC"
fi

bash -n slurm/model_init_smoke.sbatch
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=SBATCH_SYNTAX_FAILED:$RC"
  exit "$RC"
fi

ATTEMPT_ROOT="/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/round_training_model_init_smoke_v1/attempts/human-t2-model-init-smoke-v1-a000"
REVIEW_BUNDLE="/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/ROUND_GENERIC_TRAINING_MODEL_INIT_SMOKE_REVIEW_V1.zip"

if test -e "$ATTEMPT_ROOT"
then
  echo "STOP=SMOKE_ATTEMPT_ROOT_ALREADY_EXISTS:$ATTEMPT_ROOT"
  exit 61
fi

if test -e "$REVIEW_BUNDLE"
then
  echo "STOP=SMOKE_REVIEW_BUNDLE_ALREADY_EXISTS:$REVIEW_BUNDLE"
  exit 62
fi

mkdir -p logs
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=LOG_DIRECTORY_CREATE_FAILED:$RC"
  exit "$RC"
fi

SBATCH_OUTPUT="$(
  sbatch     --export=NIL     --chdir="$PACKAGE_ROOT"     --output="$PACKAGE_ROOT/logs/model_init_smoke_%j.out"     --error="$PACKAGE_ROOT/logs/model_init_smoke_%j.err"     "$PACKAGE_ROOT/slurm/model_init_smoke.sbatch"
)"
RC=$?

echo "$SBATCH_OUTPUT"
echo "SBATCH_RC=$RC"

if test "$RC" -ne 0
then
  echo "STOP=MODEL_INIT_SMOKE_SUBMISSION_FAILED"
  exit "$RC"
fi

JOB_ID="$(
  printf '%s\n' "$SBATCH_OUTPUT"   | awk '/Submitted batch job/{print $4}'
)"

if test -z "$JOB_ID"
then
  echo "STOP=MODEL_INIT_SMOKE_JOB_ID_NOT_FOUND"
  exit 63
fi

printf '%s\n' "$JOB_ID"   > logs/LAST_MODEL_INIT_SMOKE_JOB_ID.txt

echo "MODEL_INIT_SMOKE_SUBMITTED"
echo "JOB_ID=$JOB_ID"
echo "FORMAL_TRAINING_AUTHORIZED=false"
echo "TRAINING_EXECUTION_COUNT=0"
