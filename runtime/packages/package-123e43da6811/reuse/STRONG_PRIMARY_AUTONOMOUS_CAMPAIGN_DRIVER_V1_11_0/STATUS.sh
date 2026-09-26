#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
STATE_ROOT=""
while [ "$#" -gt 0 ]; do
  case "$1" in --state-root) STATE_ROOT="$2";shift 2;;*) echo "STOP=UNKNOWN_OPTION:$1";exit 64;;esac
done
if [ -z "$STATE_ROOT" ]; then echo "STOP=STATE_ROOT_REQUIRED";exit 64;fi
exec python "$ROOT/campaign_supervisor.py" status --state-root "$STATE_ROOT"
