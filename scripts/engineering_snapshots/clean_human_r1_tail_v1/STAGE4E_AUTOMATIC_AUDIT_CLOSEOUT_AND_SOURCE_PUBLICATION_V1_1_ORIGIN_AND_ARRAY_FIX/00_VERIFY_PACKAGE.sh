#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
PY="${STAGE4E_PYTHON:-/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python}"
test -x "$PY"
sha256sum -c PACKAGE_FILES.sha256
"$PY" -m unittest discover -s tests -v
"$PY" - <<'PY'
import ast
from pathlib import Path
for p in Path('.').rglob('*.py'):
    ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
print('PACKAGE_PYTHON_AST_PASS')
PY
bash -n ./RUN_PREPARE_AND_FOLLOW.sh
bash -n ./RUN_MIGRATE_SINGLE_GPU_ARRAY_AND_FOLLOW.sh
bash -n ./array_shard.sh
printf '%s\n' 'STAGE4E_PACKAGE_VERIFY_PASS' 'SCIENTIFIC_EXECUTION_PERFORMED_BY_VERIFICATION=false' 'REMOTE_PUBLICATION_VERIFIED=false'
