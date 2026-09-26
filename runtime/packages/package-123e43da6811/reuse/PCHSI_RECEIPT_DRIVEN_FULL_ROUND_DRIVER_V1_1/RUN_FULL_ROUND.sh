#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
exec "$PYTHON_BIN" "$SCRIPT_DIR/full_round_driver.py" "$@"
