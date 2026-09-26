#!/usr/bin/env bash
ROOT="${1:-}"
if [ -z "$ROOT" ]; then echo "usage: $0 <v1232t-output-root>" >&2; exit 2; fi
if [ ! -d "$ROOT/strong_group_runtime" ]; then echo "V1232U_STATUS_RUNTIME_ROOT_MISSING=$ROOT/strong_group_runtime"; exit 1; fi
CALLS=$(find "$ROOT/strong_group_runtime" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
LOGICAL=$(find "$ROOT/strong_group_runtime" -mindepth 2 -maxdepth 2 -type f -name logical_call.json | wc -l | tr -d ' ')
ACCEPTED=$(grep -rl '"terminal_method_status":"ACCEPTED"' "$ROOT/strong_group_runtime"/*/logical_call.json 2>/dev/null | wc -l | tr -d ' ')
echo "V1232U_STATUS_CALL_DIR_COUNT=$CALLS"
echo "V1232U_STATUS_LOGICAL_TERMINAL_COUNT=$LOGICAL"
echo "V1232U_STATUS_ACCEPTED_TERMINAL_COUNT=$ACCEPTED"
for f in "$ROOT"/V1232U_T_G_TERMINAL_ADOPTION_V1.json "$ROOT"/V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1.json "$ROOT"/PCHSI_V1232U_TERMINAL_V1.json; do
  if [ -f "$f" ]; then echo "V1232U_STATUS_ARTIFACT=$f"; fi
done
