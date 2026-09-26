#!/usr/bin/env bash
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
RC=$?
if [ "$RC" -ne 0 ]; then exit "$RC"; fi
PY="${PCHSI_PYTHON:-python}"
"$PY" -B "$HERE/verify_package.py"
RC=$?
if [ "$RC" -ne 0 ]; then echo "N4_3_VERIFY_RC=$RC"; exit "$RC"; fi
"$PY" -u -B "$HERE/recover.py" "$@"
RC=$?
echo "V1233N4_COMMAND_RC=$RC"
echo "V1233N4_3_COMMAND_RC=$RC"
exit "$RC"
