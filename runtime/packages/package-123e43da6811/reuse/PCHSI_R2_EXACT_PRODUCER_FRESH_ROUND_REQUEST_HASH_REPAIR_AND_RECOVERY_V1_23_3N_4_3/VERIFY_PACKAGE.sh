#!/usr/bin/env bash
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
RC=$?
if [ "$RC" -ne 0 ]; then exit "$RC"; fi
"${PCHSI_PYTHON:-python}" -B "$HERE/verify_package.py"
RC=$?
echo "V1233N4_VERIFY_RC=$RC"
exit "$RC"
