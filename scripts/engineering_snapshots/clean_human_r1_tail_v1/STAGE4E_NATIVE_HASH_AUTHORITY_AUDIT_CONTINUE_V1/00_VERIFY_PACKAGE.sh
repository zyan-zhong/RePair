#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
PY="${STAGE4E_PYTHON:-/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python}"
sha256sum -c PACKAGE_FILES.sha256
"$PY" - <<'PY'
import ast
from pathlib import Path
root=Path.cwd()
for line in (root/'PACKAGE_FILES.sha256').read_text().splitlines():
    digest,name=line.split('  ',1)
    if name.endswith('.py'):
        ast.parse((root/name).read_text(),filename=name)
print('PACKAGE_PYTHON_AST_PASS')
PY
"$PY" -m unittest discover -s tests -v
for s in ./*.sh; do bash -n "$s"; done
printf '%s\n' 'STAGE4E_NATIVE_HASH_BRIDGE_PACKAGE_VERIFY_PASS' 'PACKAGE_VERIFICATION_SCIENTIFIC_CELL_COUNT=0' 'REMOTE_PUBLICATION_PERFORMED_BY_VERIFICATION=false'
