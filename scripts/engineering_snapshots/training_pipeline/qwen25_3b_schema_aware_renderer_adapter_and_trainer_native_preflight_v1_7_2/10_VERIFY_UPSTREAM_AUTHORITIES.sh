#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

echo "【阶段10】校验上游科研与序列化权威"
python "$PACKAGE_ROOT/tools/verify_upstream_authorities.py"
rc=$?
printf '10_VERIFY_UPSTREAM_AUTHORITIES.sh_RC=%s\n' "$rc"
exit "$rc"
