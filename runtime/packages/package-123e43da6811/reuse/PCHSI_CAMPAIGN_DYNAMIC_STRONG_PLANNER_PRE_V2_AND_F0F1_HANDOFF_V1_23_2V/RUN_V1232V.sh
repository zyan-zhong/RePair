#!/usr/bin/env bash

PCHSI_PYTHON="${PCHSI_PYTHON:-python}"
DRIVER="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/v1232v_driver.py"

if [ -z "${OPENAI_API_KEY:-}" ]; then
  SECRET_LOADER="${PCHSI_OPENAI_SECRET_LOADER:-${HOME}/.pchsi_secrets/load_openai_key.sh}"
  if [ ! -f "$SECRET_LOADER" ]; then
    echo "V1232V_SECRET_LOADER_MISSING=$SECRET_LOADER" >&2
    exit 41
  fi
  . "$SECRET_LOADER"
  LOADER_RC=$?
  if [ "$LOADER_RC" -ne 0 ]; then
    echo "V1232V_SECRET_LOADER_RC=$LOADER_RC" >&2
    exit "$LOADER_RC"
  fi
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "V1232V_OPENAI_API_KEY_NOT_AVAILABLE_AFTER_LOADER" >&2
  exit 42
fi

"$PCHSI_PYTHON" -B "$DRIVER" "$@"
RC=$?
echo "PCHSI_CAMPAIGN_DYNAMIC_STRONG_PLANNER_PRE_V2_AND_F0F1_HANDOFF_RC=$RC"
exit "$RC"
