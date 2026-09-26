#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
PID=""
STATE_ROOT=""
LOG_DIR="/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts"
POLL="10"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --v110-pid) PID="$2"; shift 2;;
    --state-root) STATE_ROOT="$2"; shift 2;;
    --log-dir) LOG_DIR="$2"; shift 2;;
    --poll-seconds) POLL="$2"; shift 2;;
    *) echo "STOP=UNKNOWN_OPTION:$1"; exit 64;;
  esac
done
if [ -z "$PID" ]; then echo "STOP=V110_PID_REQUIRED"; exit 64; fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [ -z "$STATE_ROOT" ]; then
  STATE_ROOT="/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/strong_primary_autonomous_campaign_driver_v1_11_0/${STAMP}"
fi
mkdir -p "$STATE_ROOT" "$LOG_DIR" || exit 65
LOG="$LOG_DIR/strong_primary_autonomous_campaign_v1_11_0_${STAMP}.log"
nohup "$ROOT/run_campaign_worker.sh" --state-root "$STATE_ROOT" --v110-pid "$PID" --poll-seconds "$POLL" >"$LOG" 2>&1 </dev/null &
SUP_PID=$!
sleep 1
if kill -0 "$SUP_PID" 2>/dev/null; then
  echo "STATUS=AUTONOMOUS_CAMPAIGN_SUPERVISOR_CONFIRMED"
  echo "PID=$SUP_PID"
  echo "INHERITED_V110_PID=$PID"
  echo "STATE_ROOT=$STATE_ROOT"
  echo "LOG_PATH=$LOG"
  echo "NEXT=SUPERVISOR_WAITS_FOR_V110_RELEASE_THEN_RECOVERS_CURRENT_ROUND_WITHOUT_BLIND_RESEND"
  exit 0
fi
echo "STATUS=AUTONOMOUS_CAMPAIGN_SUPERVISOR_LAUNCH_FAILED"
echo "STATE_ROOT=$STATE_ROOT"
echo "LOG_PATH=$LOG"
exit 1
