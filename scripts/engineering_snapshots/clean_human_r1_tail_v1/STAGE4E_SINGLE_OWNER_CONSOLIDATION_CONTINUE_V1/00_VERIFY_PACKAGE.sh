#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
PY="${STAGE4E_PYTHON:-/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python}"
sha256sum -c PACKAGE_FILES.sha256
"$PY" -m unittest discover -s tests -v
"$PY" - <<'PY'
import ast
from pathlib import Path
for p in Path('.').rglob('*.py'):
    ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
print('PACKAGE_PYTHON_AST_PASS')
PY
bash -n RUN_CONTINUE.sh
bash -n 00_VERIFY_PACKAGE.sh
printf '%s\n' 'STAGE4E_SINGLE_OWNER_CONTINUATION_PACKAGE_PASS' 'VERIFICATION_SUBMITS_JOBS=false' 'VERIFICATION_EXECUTES_SCIENTIFIC_CELLS=false' 'VERIFICATION_PUBLISHES_REMOTE=false'
