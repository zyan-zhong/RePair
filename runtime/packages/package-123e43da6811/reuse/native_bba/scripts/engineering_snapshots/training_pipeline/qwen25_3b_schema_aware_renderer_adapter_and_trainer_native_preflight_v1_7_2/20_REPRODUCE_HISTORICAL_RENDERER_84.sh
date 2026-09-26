#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

echo "【阶段20】历史Renderer 84/84精确回放"
python "$PACKAGE_ROOT/tools/reproduce_historical_renderer_84.py"
rc=$?
printf '20_REPRODUCE_HISTORICAL_RENDERER_84.sh_RC=%s\n' "$rc"
exit "$rc"
