#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

python "$PACKAGE_ROOT/tools/build_review.py"
rc=$?
echo "BUILD_REVIEW_RC=$rc"
exit "$rc"
