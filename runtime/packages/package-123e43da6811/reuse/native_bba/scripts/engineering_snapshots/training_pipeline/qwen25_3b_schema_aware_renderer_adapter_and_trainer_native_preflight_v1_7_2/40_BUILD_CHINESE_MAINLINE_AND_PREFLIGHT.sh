#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

echo "【阶段40】构建中文科研主线与Trainer预检"
python "$PACKAGE_ROOT/tools/build_chinese_mainline_and_preflight.py"
rc=$?
printf '40_BUILD_CHINESE_MAINLINE_AND_PREFLIGHT.sh_RC=%s\n' "$rc"
exit "$rc"
