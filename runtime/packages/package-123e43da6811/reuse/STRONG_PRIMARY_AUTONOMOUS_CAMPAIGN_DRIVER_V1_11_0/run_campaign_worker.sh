#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python "$ROOT/campaign_supervisor.py" run "$@"
