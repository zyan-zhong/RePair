#!/usr/bin/env bash
#SBATCH -p gpu_a800
#SBATCH --gpus=1
#SBATCH --time=00:10:00
#SBATCH --job-name=human_t2_formal_train_v1

PACKAGE_ROOT="$(pwd -P)"
CONDA_SH="/data/apps/miniforge3/25.11.0-1/etc/profile.d/conda.sh"
CONDA_ENV="/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312"
V21_ROOT='/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/round_generic_training_stage_v2_1_hardening_build'
AUTH_FILE='/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_authorization_v1/human-t2-train17-continuation-v1-a000/ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1.json'
STAGE_BINDING="$V21_ROOT/profiles/human_reference_t2/ROUND_TRAINING_STAGE_BINDING_V1.json"

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

unset OUTPUT_ROOT
unset REPRO_ROOT
unset SOURCE_ADAPTER_ROOT
unset NATIVE_ROOT
unset MAINLINE_ROOT
unset PREFLIGHT_ROOT
unset REVIEW_ROOT

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PACKAGE_ROOT:$V21_ROOT"
export ROUND_TRAINING_RUNNER_FREEZE_ROOT_SHA256="c6918c25da0cba986ef80f05f4c144011835bca5592e4c81cc6a58cb198dd37e"


python -m round_training.stage_runner \
  --stage-binding "$STAGE_BINDING" \
  --authorization "$AUTH_FILE"
TRAIN_RC=$?

echo "HUMAN_T2_FORMAL_TRAINING_RC=$TRAIN_RC"

if test "$TRAIN_RC" -ne 0
then
  exit "$TRAIN_RC"
fi

python "$PACKAGE_ROOT/30_BUILD_FORMAL_TRAINING_REVIEW.py"
REVIEW_RC=$?

echo "HUMAN_T2_FORMAL_TRAINING_REVIEW_BUILD_RC=$REVIEW_RC"

exit "$REVIEW_RC"
