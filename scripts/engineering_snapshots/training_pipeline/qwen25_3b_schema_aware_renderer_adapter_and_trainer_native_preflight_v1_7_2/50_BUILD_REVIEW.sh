#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

echo "【阶段50】构建Review包"
python "$PACKAGE_ROOT/tools/build_review.py"
rc=$?
printf '50_BUILD_REVIEW.sh_RC=%s\n' "$rc"
exit "$rc"
