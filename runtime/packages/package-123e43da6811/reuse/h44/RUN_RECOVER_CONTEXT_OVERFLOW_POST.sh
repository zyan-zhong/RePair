#!/usr/bin/env bash
# Explicit-RC runner: no set -e/-u/pipefail by project rule.
PY="${PCHSI_PYTHON:-python}"
"$PY" -B ./verify_package.py
VRC=$?
if [ "$VRC" -ne 0 ]; then
  echo "H4_4_PACKAGE_VERIFICATION_RC=$VRC"
  exit "$VRC"
fi
"$PY" -B ./post_context_recovery.py "$@"
RC=$?
echo "H4_4_CONTEXT_RECOVERY_RC=$RC"
exit "$RC"
