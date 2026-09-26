#!/bin/bash
#SBATCH -p gpu_a800
#SBATCH --gpus=1
#SBATCH --time=00:45:00
#SBATCH --job-name=human_pilot_stage0_offoff_v1

PACKAGE_ROOT="$(pwd -P)"

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

unset OUTPUT_ROOT
unset REPRO_ROOT
unset SOURCE_ADAPTER_ROOT
unset NATIVE_ROOT
unset MAINLINE_ROOT
unset PREFLIGHT_ROOT
unset REVIEW_ROOT

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PACKAGE_ROOT:/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-generic-select-policy-binding-human-offoff-v1/src"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export VLLM_NO_USAGE_STATS=1
export DO_NOT_TRACK=1

unset http_proxy
unset https_proxy
unset HTTP_PROXY
unset HTTPS_PROXY
unset all_proxy
unset ALL_PROXY
export NO_PROXY="127.0.0.1,localhost"
export no_proxy="127.0.0.1,localhost"

unset ROCR_VISIBLE_DEVICES
unset HIP_VISIBLE_DEVICES

python -m stage0.slurm_entry
RC=$?

echo "HUMAN_PILOT_STAGE0_SLURM_RC=$RC"
exit "$RC"
