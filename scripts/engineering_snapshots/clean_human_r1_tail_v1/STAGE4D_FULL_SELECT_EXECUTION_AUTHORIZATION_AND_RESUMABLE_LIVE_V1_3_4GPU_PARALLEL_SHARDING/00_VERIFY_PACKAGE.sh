#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$ROOT"
sha256sum -c PACKAGE_FILES.sha256
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT"
python -m unittest discover -s tests -v
python - <<'PY'
import ast
from pathlib import Path
for path in sorted(Path('.').rglob('*.py')):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
print('PACKAGE_PYTHON_AST_PASS')
PY
bash -n RUN_AUTHORIZE_AND_SUBMIT.sh
bash -n slurm_template.sh
if grep -nE -- '--cpus-per-task|--mem(=| )|--mem-per-cpu|--mem-per-gpu' RUN_AUTHORIZE_AND_SUBMIT.sh slurm_template.sh; then
  echo 'STOP=FORBIDDEN_CLUSTER_RESOURCE_REQUEST_FOUND'
  exit 91
fi
if grep -R -n 'run_single_episode(' stage4d_full; then
  echo 'STOP=SECOND_EPISODE_EVALUATOR_IMPLEMENTATION_DETECTED'
  exit 92
fi
grep -Fxq '#SBATCH --nodes=1' slurm_template.sh
grep -Fxq '#SBATCH --gpus=4' slurm_template.sh
grep -Fxq '#SBATCH --time=03:30:00' slurm_template.sh
grep -q '"srun"' stage4d_full/slurm_entry.py
grep -q '"--exclusive"' stage4d_full/slurm_entry.py
grep -q '"--gpus=1"' stage4d_full/slurm_entry.py
grep -q 'stage4d_full.shard_worker' stage4d_full/slurm_entry.py
grep -q 'consolidate_shards' stage4d_full/slurm_entry.py
grep -q 'parallel_v1' stage4d_full/live.py
echo 'STAGE4D_FULL_SELECT_PACKAGE_VERIFY_PASS'
echo 'PARALLEL_SHARD_COUNT=4'
echo 'AUTHORIZED_TOTAL_CONDITION_CELLS=3550'
echo 'RESULT_INTERPRETATION_AUTHORIZED=false'
echo 'PROMOTION_AUTHORIZED=false'
