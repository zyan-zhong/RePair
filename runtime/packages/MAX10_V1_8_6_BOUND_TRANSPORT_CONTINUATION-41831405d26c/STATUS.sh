#!/usr/bin/env bash
set +euo pipefail
PACKAGE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["registered_python"])' "$PACKAGE_DIR/AUTHORITY.json")"
"$PYTHON_BIN" -B "$PACKAGE_DIR/STATUS.py" "$@"
status_rc=$?
exit "$status_rc"
