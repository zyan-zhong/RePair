#!/usr/bin/env bash
# Operator-facing shell intentionally preserves explicit return-code handling.
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
PCHSI_PYTHON="${PCHSI_PYTHON:-python}"
if [ -z "${OPENAI_API_KEY:-}" ]; then
  LOADER="${PCHSI_OPENAI_SECRET_LOADER:-${HOME}/.pchsi_secrets/load_openai_key.sh}"
  if [ ! -f "$LOADER" ]; then
    echo "V1232U_SECRET_LOADER_MISSING=$LOADER" >&2
    exit 31
  fi
  . "$LOADER"
  LOAD_RC=$?
  if [ "$LOAD_RC" -ne 0 ]; then
    echo "V1232U_SECRET_LOADER_RC=$LOAD_RC" >&2
    exit "$LOAD_RC"
  fi
fi
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "V1232U_OPENAI_API_KEY_MISSING" >&2
  exit 31
fi
"$PCHSI_PYTHON" "$PKG_DIR/v1232u_driver.py" "$@"
RC=$?
echo "PCHSI_CAMPAIGN_STRONG_ANALYZER_G_TERMINAL_ADOPTION_CPX_DYNAMIC_PAIR_UNIVERSE_RC=$RC"
exit "$RC"
