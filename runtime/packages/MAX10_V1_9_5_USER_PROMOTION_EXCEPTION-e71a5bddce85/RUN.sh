#!/usr/bin/env bash
set +euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python -B "$HERE/VERIFY.py" --server
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
python -B "$HERE/launch.py"
exit $?
