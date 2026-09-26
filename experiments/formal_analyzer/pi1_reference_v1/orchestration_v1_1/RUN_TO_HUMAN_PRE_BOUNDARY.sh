#!/usr/bin/env bash

PACKAGE_ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" &&
  pwd -P
)"

module purge
module load miniforge3

source \
  /data/apps/miniforge3/25.11.0-1/etc/profile.d/conda.sh

conda activate \
  /data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312

echo "========== PACKAGE VERIFY =========="

sha256sum -c \
  "$PACKAGE_ROOT/SHA256SUMS.txt"

VERIFY_RC="$?"

echo "PACKAGE_VERIFY_RC=$VERIFY_RC"

if test "$VERIFY_RC" -ne 0
then
  exit "$VERIFY_RC"
fi

python \
  "$PACKAGE_ROOT/tools/verify_package.py"

STATIC_RC="$?"

echo "PACKAGE_STATIC_VERIFY_RC=$STATIC_RC"

if test "$STATIC_RC" -ne 0
then
  exit "$STATIC_RC"
fi

python -m pytest -q \
  "$PACKAGE_ROOT/tests/test_master_helpers.py"

TEST_RC="$?"

echo "PACKAGE_HELPER_TEST_RC=$TEST_RC"

if test "$TEST_RC" -ne 0
then
  exit "$TEST_RC"
fi

if test -z "${OPENAI_API_KEY-}"
then
  SECRET_LOADER="/data/run01/scwb204/.pchsi_secrets/load_openai_key.sh"

  if test -f "$SECRET_LOADER"
  then
    . "$SECRET_LOADER"
  fi
fi

if test -z "${OPENAI_API_KEY-}"
then
  echo "STOP=OPENAI_API_KEY_NOT_LOADED"
  exit 71
fi

export PYTHONUNBUFFERED=1

LOG_ROOT="${FORMAL_ANALYZER_BOUNDARY_LOG_ROOT:-/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_analyzer_to_human_researcher_pre_boundary_v1_logs}"

mkdir -p "$LOG_ROOT"

LOG="$LOG_ROOT/RUN_TO_HUMAN_PRE_BOUNDARY.log"

echo "MASTER_LOG=$LOG"
echo "PCHSI_BATCH_POLL_SECONDS=${PCHSI_BATCH_POLL_SECONDS:-60}"
echo "PCHSI_AUTHORIZE_FORMAL_ANALYZER_LIVE=${PCHSI_AUTHORIZE_FORMAL_ANALYZER_LIVE:-NO}"

python \
  "$PACKAGE_ROOT/tools/master.py" \
  "$@" \
  2>&1 |
tee -a "$LOG"

MASTER_RC="${PIPESTATUS[0]}"

echo "FORMAL_ANALYZER_TO_HUMAN_PRE_BOUNDARY_RC=$MASTER_RC"

exit "$MASTER_RC"
