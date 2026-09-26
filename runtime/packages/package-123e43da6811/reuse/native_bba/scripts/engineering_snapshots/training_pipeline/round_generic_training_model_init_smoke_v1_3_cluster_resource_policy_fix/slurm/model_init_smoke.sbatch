#!/bin/bash
#SBATCH -p gpu_a800
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus=1
#SBATCH --time=00:10:00
#SBATCH --job-name=human_t2_model_init_smoke_v1

PACKAGE_ROOT="$(pwd -P)"
EXPECTED_PACKAGE_BASENAME="round_generic_training_model_init_smoke_v1_3_cluster_resource_policy_fix"

if test "$(basename "$PACKAGE_ROOT")" != "$EXPECTED_PACKAGE_BASENAME"
then
  echo "STOP=SBATCH_PACKAGE_BASENAME_MISMATCH:$PACKAGE_ROOT:$EXPECTED_PACKAGE_BASENAME"
  exit 50
fi

echo "SBATCH_PACKAGE_ROOT_PHYSICAL=$PACKAGE_ROOT"

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

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PACKAGE_ROOT"

python -m smoke.smoke_runner
SMOKE_RC=$?

echo "MODEL_INIT_SMOKE_RUNTIME_RC=$SMOKE_RC"

if test "$SMOKE_RC" -ne 0
then
  exit "$SMOKE_RC"
fi

python ./20_BUILD_SMOKE_REVIEW.py
REVIEW_RC=$?

echo "MODEL_INIT_SMOKE_REVIEW_BUILD_RC=$REVIEW_RC"

exit "$REVIEW_RC"
