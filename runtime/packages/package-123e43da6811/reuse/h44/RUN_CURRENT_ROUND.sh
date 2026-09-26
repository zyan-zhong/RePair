#!/usr/bin/env bash
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RC=$?
if test "$RC" -ne 0; then exit "$RC"; fi
PY="${PCHSI_PYTHON:-python}"
export PYTHONDONTWRITEBYTECODE=1
"$PY" -B "$HERE/verify_package.py"
RC=$?
if test "$RC" -ne 0; then
  printf 'CURRENT_ROUND_PACKAGE_VERIFICATION_RC=%s\n' "$RC"
  exit "$RC"
fi
"$PY" -B "$HERE/controller.py" "$@"
RC=$?
printf 'CURRENT_ROUND_LAUNCH_RC=%s\n' "$RC"
exit "$RC"
