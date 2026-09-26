#!/usr/bin/env bash
PCHSI_PYTHON_VALUE="${PCHSI_PYTHON:-python}"
V1230_ROOT=""
LINEAGE_ROOT=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --v1230-output-root) V1230_ROOT="$2"; shift 2;;
    --lineage-root) LINEAGE_ROOT="$2"; shift 2;;
    *) echo "STOP=UNKNOWN_ARGUMENT:$1"; exit 64;;
  esac
done

if [ -z "$V1230_ROOT" ] || [ -z "$LINEAGE_ROOT" ]; then
  echo "STOP=V1232_REQUIRED_ARGUMENT_MISSING"
  exit 64
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"

PYTHONDONTWRITEBYTECODE=1 \
"$PCHSI_PYTHON_VALUE" -B "$ROOT/submit_v1232.py" \
  --v1230-output-root "$V1230_ROOT" \
  --lineage-root "$LINEAGE_ROOT"

RC=$?
echo "PCHSI_CAMPAIGN_AUTHORITY_DRIVEN_FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_RC=$RC"
exit "$RC"
