#!/bin/bash
#SBATCH -p gpu_a800
#SBATCH --nodes=1
#SBATCH --gpus=4
#SBATCH --time=03:30:00
#SBATCH --job-name=st4d_select_4gpu

set -euo pipefail

EXECUTION_ROOT="$1"
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
PY="/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python"

# Keep --export=NIL at submission and restore only deterministic runtime tools.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export VLLM_NO_USAGE_STATS=1
export DO_NOT_TRACK=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false

export STAGE4D_RUNTIME_CACHE_ROOT="/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/runtime_cache/stage4d_existing_select_live_execution_v1/${SLURM_JOB_ID}"
export VLLM_CACHE_ROOT="${STAGE4D_RUNTIME_CACHE_ROOT}/vllm"
export TORCHINDUCTOR_CACHE_DIR="${STAGE4D_RUNTIME_CACHE_ROOT}/torchinductor"
export TRITON_CACHE_DIR="${STAGE4D_RUNTIME_CACHE_ROOT}/triton"
export TMPDIR="/tmp/st4d-${SLURM_JOB_USER}-${SLURM_JOB_ID}"
mkdir -p "$VLLM_CACHE_ROOT" "$TORCHINDUCTOR_CACHE_DIR" "$TRITON_CACHE_DIR" "$TMPDIR"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY
export NO_PROXY="127.0.0.1,localhost"
export no_proxy="$NO_PROXY"
unset ROCR_VISIBLE_DEVICES HIP_VISIBLE_DEVICES

command -v ld >/dev/null
command -v gcc >/dev/null
ld --version | head -n 1
nvidia-smi --query-gpu=index,uuid,memory.total,memory.used,memory.free --format=csv,noheader

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PACKAGE_ROOT"

exec "$PY" -m stage4d_full.slurm_entry --execution-root "$EXECUTION_ROOT"
