#!/usr/bin/env bash
set +euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["registered_python"])' "$HERE/AUTHORITY.json")"
"$PYTHON" -B "$HERE/launch.py" 2>&1 | tee "$HERE/LAUNCH_OPERATOR.log"
RC=${PIPESTATUS[0]}
printf 'CLOSED_HISTORY_LAUNCH_RC=%s\n' "$RC"
exit "$RC"
