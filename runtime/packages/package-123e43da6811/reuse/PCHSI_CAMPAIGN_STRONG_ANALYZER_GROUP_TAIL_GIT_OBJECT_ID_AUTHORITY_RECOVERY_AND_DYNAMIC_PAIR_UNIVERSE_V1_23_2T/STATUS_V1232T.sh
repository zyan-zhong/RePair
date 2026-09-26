#!/usr/bin/env bash
# Read-only status helper. No scheduler/provider/environment/training action.
ROOT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-root) ROOT="$2"; shift 2 ;;
    *) echo "UNKNOWN_ARG=$1" >&2; exit 2 ;;
  esac
done
if [ -z "$ROOT" ]; then echo "--output-root required" >&2; exit 2; fi
PY="${PCHSI_PYTHON:-python}"
"$PY" - "$ROOT" <<'PY_V1232T_STATUS_INNER'
from pathlib import Path
import json,sys
root=Path(sys.argv[1])
term=root/'PCHSI_V1232T_TERMINAL_V1.json'
tail=root/'V1232T_STRONG_ANALYZER_TAIL_TERMINAL_V1.json'
fail=root/'V1232T_ANALYZER_TAIL_HARD_STOP_V1.json'
for p in (term,tail,fail):
    if p.is_file(): print(json.dumps(json.loads(p.read_text()),sort_keys=True))
runtime=root/'strong_group_runtime'
if runtime.is_dir():
    calls=[x for x in runtime.iterdir() if x.is_dir() and not x.is_symlink()]
    terminal=sum((x/'logical_call.json').is_file() for x in calls)
    accepted=sum((x/'validated_artifact.json').is_file() for x in calls)
    print('V1232T_CALL_DIR_COUNT='+str(len(calls)))
    print('V1232T_TERMINAL_CALL_COUNT='+str(terminal))
    print('V1232T_ACCEPTED_ARTIFACT_COUNT='+str(accepted))
PY_V1232T_STATUS_INNER
