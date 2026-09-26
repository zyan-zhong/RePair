#!/bin/bash
#SBATCH -p gpu_a800
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus=1
#SBATCH --array=0-3%4
#SBATCH --time=03:30:00
#SBATCH --job-name=st4d_select_shard

set -euo pipefail
PACKAGE_ROOT="$1"
EXECUTION_ROOT="$2"
PLAN_SHA="$3"
PY="/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export STAGE4D_RUNTIME_CACHE_ROOT="/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/runtime_cache/stage4d_existing_select_live_execution_v1/${SLURM_JOB_ID}/shard_${SLURM_ARRAY_TASK_ID}"
export VLLM_CACHE_ROOT="$STAGE4D_RUNTIME_CACHE_ROOT/vllm"
export TORCHINDUCTOR_CACHE_DIR="$STAGE4D_RUNTIME_CACHE_ROOT/torchinductor"
export TRITON_CACHE_DIR="$STAGE4D_RUNTIME_CACHE_ROOT/triton"
export TMPDIR="/tmp/st4d-${SLURM_JOB_USER}-${SLURM_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
mkdir -p "$VLLM_CACHE_ROOT" "$TORCHINDUCTOR_CACHE_DIR" "$TRITON_CACHE_DIR" "$TMPDIR"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY
unset ROCR_VISIBLE_DEVICES HIP_VISIBLE_DEVICES
export NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost"
command -v ld
command -v gcc
ld --version
printf 'STAGE4D_ARRAY_NODE=%s JOB=%s ARRAY=%s SHARD=%s CUDA_VISIBLE_DEVICES=%s\n' \
  "$(hostname)" "$SLURM_JOB_ID" "$SLURM_ARRAY_JOB_ID" "$SLURM_ARRAY_TASK_ID" "${CUDA_VISIBLE_DEVICES-}"
nvidia-smi --query-gpu=index,uuid,name,memory.total,memory.used,memory.free --format=csv,noheader
export PYTHONPATH="$PACKAGE_ROOT"
cd "$PACKAGE_ROOT"
exec "$PY" -u -m stage4e.array_driver worker --execution-root "$EXECUTION_ROOT" --plan-sha "$PLAN_SHA"
