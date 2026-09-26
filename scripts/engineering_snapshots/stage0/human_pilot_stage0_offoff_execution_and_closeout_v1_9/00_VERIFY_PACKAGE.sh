#!/usr/bin/env bash

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
PYTHONPYCACHEPREFIX="$(mktemp -d)"
export PYTHONPYCACHEPREFIX
export PYTHONPATH="$PACKAGE_ROOT"

python -m pytest -q -p no:cacheprovider tests
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

paths = list(Path("stage0").rglob("*.py")) + [
    Path("05_APPLY_GENERIC_SELECT_ARTIFACT_PATCH.py"),
    Path("10_OFFLINE_PREFLIGHT.py"),
    Path("20_PREPARE_EXECUTION_AUTHORIZATION.py"),
]
for path in paths:
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    if re.search(r"[\u4e00-\u9fff]", source):
        raise SystemExit(
            "STOP=PRODUCTION_SOURCE_CONTAINS_CHINESE:" + str(path)
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

CACHE_ARTIFACTS_AFTER="$(
  find . \
    \( -type d -name '__pycache__' -o -type f -name '*.pyc' \) \
    -print
)"
if test -n "$CACHE_ARTIFACTS_AFTER"
then
  echo "STOP=PACKAGE_GENERATED_TRANSIENT_PYTHON_CACHE"
  printf '%s\n' "$CACHE_ARTIFACTS_AFTER"
  exit 46
fi

echo "HUMAN_PILOT_STAGE0_V1_9_PACKAGE_VERIFY_PASS"
echo "MODEL_EXECUTION_AUTHORIZED_BY_PACKAGE=false"
echo "ENVIRONMENT_EXECUTION_AUTHORIZED_BY_PACKAGE=false"
echo "PAPER_EFFICACY_EVIDENCE=false"
