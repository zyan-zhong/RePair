#!/usr/bin/env bash
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RC=$?
if test "$RC" -ne 0; then exit "$RC"; fi
PY="${PCHSI_PYTHON:-python}"
export PYTHONDONTWRITEBYTECODE=1
"$PY" -B "$HERE/verify_package.py"
RC=$?
if test "$RC" -ne 0; then
  printf 'H4_PACKAGE_VERIFICATION_RC=%s\n' "$RC"
  exit "$RC"
fi
"$PY" -B "$HERE/recovery.py" "$@"
RC=$?
printf 'H4_RECOVERY_RC=%s\n' "$RC"
exit "$RC"
