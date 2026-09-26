#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PACKAGE_ROOT"

sha256sum -c PACKAGE_FILES.sha256
rc=$?
printf 'PACKAGE_SHA256_VERIFY_RC=%s\n' "$rc"
if test "$rc" -ne 0
then
  echo "STOP=PACKAGE_SHA256_VERIFY_FAILED"
  exit "$rc"
fi
echo "PACKAGE_SHA256_VERIFY_PASS"

PYTHONPYCACHEPREFIX="$(mktemp -d)"
export PYTHONPYCACHEPREFIX
export PYTHONDONTWRITEBYTECODE=1

python -m pytest -q -p no:cacheprovider "$PACKAGE_ROOT/tests"
rc=$?
printf 'PACKAGE_PYTEST_RC=%s\n' "$rc"
if test "$rc" -ne 0
then
  rm -rf "$PYTHONPYCACHEPREFIX"
  exit "$rc"
fi
echo "PACKAGE_TESTS_PASS"

for script in "$PACKAGE_ROOT"/*.sh
do
  bash -n "$script"
  rc=$?
  if test "$rc" -ne 0
  then
    rm -rf "$PYTHONPYCACHEPREFIX"
    exit "$rc"
  fi
done
echo "PACKAGE_BASH_SYNTAX_PASS"

python -m compileall -q "$PACKAGE_ROOT/tools" "$PACKAGE_ROOT/tests"
rc=$?
if test "$rc" -ne 0
then
  rm -rf "$PYTHONPYCACHEPREFIX"
  exit "$rc"
fi
echo "PACKAGE_PYTHON_COMPILE_PASS"

rm -rf "$PYTHONPYCACHEPREFIX"

echo "QWEN25_3B_SCHEMA_AWARE_RENDERER_ADAPTER_V1_7_2_PACKAGE_PASS"
echo "主线展示语言=中文"
echo "TRAINER_EXECUTION_AUTHORIZED=false"
echo "TRAINING_EXECUTION_COUNT=0"
