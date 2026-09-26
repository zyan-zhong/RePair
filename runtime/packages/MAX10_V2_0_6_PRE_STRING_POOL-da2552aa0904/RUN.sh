#!/usr/bin/env bash
set +e
set +u
set +o pipefail
PACKAGE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REGISTERED_PYTHON="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["registered_python"])' "$PACKAGE_DIR/AUTHORITY.json")"
if [ -z "$REGISTERED_PYTHON" ]; then exit 2; fi
"$REGISTERED_PYTHON" -B "$PACKAGE_DIR/VERIFY.py" --server 2>&1 | tee "$PACKAGE_DIR/RUN_VERIFY.log"
VERIFY_RC=${PIPESTATUS[0]}
if [ "$VERIFY_RC" -ne 0 ]; then exit "$VERIFY_RC"; fi
"$REGISTERED_PYTHON" -B "$PACKAGE_DIR/launch.py" 2>&1 | tee "$PACKAGE_DIR/RUN_LAUNCH.log"
LAUNCH_RC=${PIPESTATUS[0]}
exit "$LAUNCH_RC"
