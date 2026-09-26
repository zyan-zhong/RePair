#!/usr/bin/env bash

PACKAGE_ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" &&
  pwd -P
)"

sha256sum -c \
  "$PACKAGE_ROOT/SHA256SUMS.txt"

RC="$?"

echo "SHA256SUMS_RC=$RC"

if test "$RC" -ne 0
then
  exit "$RC"
fi

python \
  "$PACKAGE_ROOT/tools/verify_package.py"

RC="$?"

echo "STATIC_VERIFY_RC=$RC"

if test "$RC" -ne 0
then
  exit "$RC"
fi

python -m pytest -q \
  "$PACKAGE_ROOT/tests/test_master_helpers.py"

RC="$?"

echo "HELPER_TEST_RC=$RC"

exit "$RC"
