#!/bin/bash

PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PACKAGE_ROOT"

CONDA_SH="/data/apps/miniforge3/25.11.0-1/etc/profile.d/conda.sh"
CONDA_ENV="/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312"

if test ! -f "$CONDA_SH"
then
  echo "STOP=CONDA_SH_MISSING:$CONDA_SH"
  exit 51
fi

. "$CONDA_SH"
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=CONDA_INITIALIZATION_FAILED:$RC"
  exit "$RC"
fi

conda activate "$CONDA_ENV"
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=CONDA_ACTIVATION_FAILED:$RC"
  exit "$RC"
fi

EXPECTED_APPROVAL="APPROVE_STAGE1_GENERIC_ROUND_CONTROL_PLANE_V1"
if test "${STAGE1_CONTROL_PLANE_BUILD_APPROVAL-}" != "$EXPECTED_APPROVAL"
then
  echo "STOP=EXPLICIT_STAGE1_CONTROL_PLANE_APPROVAL_REQUIRED"
  echo "EXPECTED_APPROVAL_TOKEN=$EXPECTED_APPROVAL"
  exit 70
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PACKAGE_ROOT"

bash ./00_VERIFY_PACKAGE.sh
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=STAGE1_PACKAGE_VERIFY_FAILED:$RC"
  exit "$RC"
fi

python ./10_VERIFY_STAGE0_AND_WORKTREE.py
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=STAGE1_PRECONDITION_FAILED:$RC"
  exit "$RC"
fi

python ./20_APPLY_STAGE1_CONTROL_PLANE.py
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=STAGE1_CONTROL_PLANE_BUILD_FAILED:$RC"
  exit "$RC"
fi

python ./30_BUILD_STAGE1_REVIEW.py
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=STAGE1_REVIEW_BUILD_FAILED:$RC"
  exit "$RC"
fi

echo "STAGE1_GENERIC_ROUND_AUTOMATION_CONTROL_PLANE_PASS"
echo "MODEL_EXECUTION_COUNT=0"
echo "ENVIRONMENT_EXECUTION_COUNT=0"
echo "TRAINING_EXECUTION_COUNT=0"
echo "BENCHMARK_EXECUTION_COUNT=0"
echo "REPOSITORY_COMMIT_CREATED=false"
echo "REPOSITORY_PUSH_EXECUTED=false"
echo "NEXT_GATE=STAGE1_CONCRETE_COMPONENT_RUNNER_BINDING_AND_HUMAN_STRONG_LOCAL_DRY_RUN"
