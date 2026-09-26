#!/bin/bash
set -e
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${STAGE4D_PYTHON:-python}"
cd "$PACKAGE_ROOT"
sha256sum -c PACKAGE_FILES.sha256
"$PY" -m compileall -q stage4d_pkg tests
"$PY" -m unittest discover -s tests -v
bash -n RUN_PREPARE_AND_SUBMIT_READINESS.sh
if grep -REn -- '--cpus-per-task|--mem(=| )|--mem-per-cpu|--mem-per-gpu' RUN_PREPARE_AND_SUBMIT_READINESS.sh; then
  echo "STOP=FORBIDDEN_SLURM_RESOURCE_REQUEST"
  exit 1
fi
echo "STAGE4D_PACKAGE_VERIFY_PASS"
echo "SCIENTIFIC_SELECT_CELL_EXECUTION_COUNT=0"
echo "EVALUATION_EXECUTION_AUTHORIZED=false"
