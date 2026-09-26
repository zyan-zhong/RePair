#!/usr/bin/env bash
PCHSI_ENTRY_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PCHSI_ENTRY_PYTHON=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["registered_python"])' "$PCHSI_ENTRY_DIR/AUTHORITY.json")
PCHSI_ENTRY_RC=$?
if [ "$PCHSI_ENTRY_RC" -ne 0 ]; then exit "$PCHSI_ENTRY_RC"; fi
"$PCHSI_ENTRY_PYTHON" -B "$PCHSI_ENTRY_DIR/VERIFY.py" --server
PCHSI_ENTRY_RC=$?
if [ "$PCHSI_ENTRY_RC" -ne 0 ]; then exit "$PCHSI_ENTRY_RC"; fi
"$PCHSI_ENTRY_PYTHON" -B "$PCHSI_ENTRY_DIR/launch.py"
exit $?
