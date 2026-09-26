#!/usr/bin/env bash
RUN_ROOT="$1"
if test -z "$RUN_ROOT"; then
  printf 'usage: %s <current-round-run-root>\n' "$0" >&2
  exit 2
fi
if test -f "$RUN_ROOT/ROUND_EXECUTION_TERMINAL.json"; then
  cat "$RUN_ROOT/ROUND_EXECUTION_TERMINAL.json"
  exit 0
fi
printf 'STATUS=CURRENT_CAUSAL_ROUND_IN_PROGRESS_OR_NOT_STARTED\n'
if test -f "$RUN_ROOT/controller.log"; then
  tail -n 80 "$RUN_ROOT/controller.log"
fi
exit 0
