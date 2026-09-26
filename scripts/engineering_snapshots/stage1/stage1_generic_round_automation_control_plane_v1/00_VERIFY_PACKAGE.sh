#!/bin/bash

PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PACKAGE_ROOT"

CACHE_ARTIFACTS="$(
  find . \
    \( -type d -name '__pycache__' -o -type f -name '*.pyc' \) \
    -print
)"

if test -n "$CACHE_ARTIFACTS"
then
  echo "STOP=PACKAGE_CONTAINS_TRANSIENT_PYTHON_CACHE"
  printf '%s\n' "$CACHE_ARTIFACTS"
  exit 45
fi

sha256sum -c PACKAGE_FILES.sha256
RC=$?
echo "PACKAGE_SHA256_VERIFY_RC=$RC"
if test "$RC" -ne 0
then
  exit "$RC"
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPYCACHEPREFIX="$(mktemp -d)"
export PYTHONPATH="$PACKAGE_ROOT/test_support:$PACKAGE_ROOT/payload/src:$PACKAGE_ROOT"

python -m pytest \
  -q \
  -p no:cacheprovider \
  tests \
  payload/tests/round_control
RC=$?
echo "PACKAGE_PYTEST_RC=$RC"
if test "$RC" -ne 0
then
  rm -rf "$PYTHONPYCACHEPREFIX"
  exit "$RC"
fi

python - <<'PY'
from pathlib import Path
import re

paths = (
    list(Path("stage1_pkg").rglob("*.py"))
    + list(Path("payload/src/pchsi/round_control").rglob("*.py"))
    + [
        Path("10_VERIFY_STAGE0_AND_WORKTREE.py"),
        Path("20_APPLY_STAGE1_CONTROL_PLANE.py"),
        Path("30_BUILD_STAGE1_REVIEW.py"),
    ]
)

for path in paths:
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    if re.search(r"[\u4e00-\u9fff]", source):
        raise SystemExit(
            "STOP=PRODUCTION_SOURCE_CONTAINS_CHINESE:"
            + str(path)
        )

print("PACKAGE_PYTHON_SOURCE_COMPILE_PASS")
print("PRODUCTION_SOURCE_LANGUAGE_AUDIT_PASS")
PY
RC=$?

rm -rf "$PYTHONPYCACHEPREFIX"

if test "$RC" -ne 0
then
  exit "$RC"
fi

bash -n RUN_STAGE1_CONTROL_PLANE_BUILD.sh
RC=$?
if test "$RC" -ne 0
then
  echo "STOP=PACKAGE_BASH_SYNTAX_FAILED"
  exit "$RC"
fi

CACHE_AFTER="$(
  find . \
    \( -type d -name '__pycache__' -o -type f -name '*.pyc' \) \
    -print
)"
if test -n "$CACHE_AFTER"
then
  echo "STOP=PACKAGE_GENERATED_TRANSIENT_PYTHON_CACHE"
  printf '%s\n' "$CACHE_AFTER"
  exit 46
fi

echo "STAGE1_GENERIC_ROUND_CONTROL_PLANE_PACKAGE_VERIFY_PASS"
echo "MODEL_EXECUTION_AUTHORIZED=false"
echo "ENVIRONMENT_EXECUTION_AUTHORIZED=false"
echo "TRAINING_EXECUTION_AUTHORIZED=false"
echo "BENCHMARK_EXECUTION_AUTHORIZED=false"
echo "REPOSITORY_COMMIT_AUTHORIZED=false"
echo "REPOSITORY_PUSH_AUTHORIZED=false"
