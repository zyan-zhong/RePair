#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

python "$PACKAGE_ROOT/tools/freeze_reference_takeover_normative_bridge.py"
rc=$?
echo "FREEZE_REFERENCE_TAKEOVER_NORMATIVE_BRIDGE_RC=$rc"
exit "$rc"
