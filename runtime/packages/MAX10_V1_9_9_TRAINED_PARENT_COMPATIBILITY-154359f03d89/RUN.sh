#!/usr/bin/env bash
set +euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python "$ROOT/VERIFY.py" --server
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
python "$ROOT/launch.py"
exit $?
