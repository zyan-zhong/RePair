#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

python "$PACKAGE_ROOT/tools/census_frozen_q2_renderer_interface.py"
rc=$?
echo "CENSUS_FROZEN_Q2_RENDERER_INTERFACE_RC=$rc"
exit "$rc"
