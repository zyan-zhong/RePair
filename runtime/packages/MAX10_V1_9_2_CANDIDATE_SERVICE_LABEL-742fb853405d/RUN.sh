#!/usr/bin/env bash
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python -B "$SCRIPT_DIR/VERIFY.py" --server
verify_rc=$?
if [ "$verify_rc" -ne 0 ]; then exit "$verify_rc"; fi
python -B "$SCRIPT_DIR/launch.py"
launch_rc=$?
exit "$launch_rc"
