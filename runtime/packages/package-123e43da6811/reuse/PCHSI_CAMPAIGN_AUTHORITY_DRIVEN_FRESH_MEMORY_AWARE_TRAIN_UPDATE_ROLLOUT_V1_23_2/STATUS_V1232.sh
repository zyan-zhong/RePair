#!/usr/bin/env bash
STATE_ROOT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --state-root) STATE_ROOT="$2"; shift 2;;
    *) echo "STOP=UNKNOWN_ARGUMENT:$1"; exit 64;;
  esac
done
if [ -z "$STATE_ROOT" ]; then
  echo "STOP=STATE_ROOT_REQUIRED"
  exit 64
fi

TERMINAL="$STATE_ROOT/PCHSI_V1232_JOB_TERMINAL_V1.json"
SUBMISSION="$STATE_ROOT/PCHSI_V1232_SLURM_SUBMISSION_RECEIPT_V1.json"

if [ -f "$TERMINAL" ]; then
  cat "$TERMINAL"
  exit 0
fi

if [ ! -f "$SUBMISSION" ]; then
  echo "STATUS=V1232_NO_SUBMISSION_RECEIPT"
  exit 2
fi

JOB_ID="$(
  python - "$SUBMISSION" <<'PY'
import json,sys
obj=json.load(open(sys.argv[1]))
print(obj["job_id"])
PY
)"
echo "STATUS=V1232_JOB_NOT_TERMINAL"
echo "V1232_SLURM_JOB_ID=$JOB_ID"
squeue -j "$JOB_ID" -o "%.18i %.12P %.28j %.10T %.10M %.6D %R" 2>/dev/null
SQUEUE_RC=$?
if [ "$SQUEUE_RC" -ne 0 ]; then
  echo "V1232_SQUEUE_RC=$SQUEUE_RC"
fi
exit 0
