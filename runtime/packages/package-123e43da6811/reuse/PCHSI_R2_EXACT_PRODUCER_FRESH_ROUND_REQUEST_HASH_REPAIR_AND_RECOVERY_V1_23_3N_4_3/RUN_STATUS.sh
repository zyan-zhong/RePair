#!/usr/bin/env bash
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
RC=$?
if [ "$RC" -ne 0 ]; then exit "$RC"; fi
"${PCHSI_PYTHON:-python}" -B "$HERE/status.py" "$@"
RC=$?
exit "$RC"
