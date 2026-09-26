#!/usr/bin/env bash
ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON=/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python
"$PYTHON" -B "$ROOT/VERIFY.py" --hash-only
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
exec "$PYTHON" -B "$ROOT/WATCH.py" "$@"
