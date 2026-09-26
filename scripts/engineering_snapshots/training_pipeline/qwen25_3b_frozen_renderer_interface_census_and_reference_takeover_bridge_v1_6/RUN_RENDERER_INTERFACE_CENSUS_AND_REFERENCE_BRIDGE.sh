#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PACKAGE_ROOT"

run_stage() {
  local script="$1"
  printf '\n========== %s ==========\n' "$script"
  bash "$PACKAGE_ROOT/$script"
  local rc=$?
  printf '%s_RC=%s\n' "$script" "$rc"
  if test "$rc" -ne 0
  then
    echo "STOP=QWEN_RENDERER_CENSUS_V1_6_STAGE_FAILED:$script"
    exit "$rc"
  fi
}

run_stage 00_VERIFY_PACKAGE.sh
run_stage 10_CENSUS_FROZEN_Q2_RENDERER_INTERFACE.sh
run_stage 20_FREEZE_REFERENCE_TAKEOVER_NORMATIVE_BRIDGE.sh
run_stage 30_BUILD_REVIEW.sh

source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

printf '\nQWEN25_3B_FROZEN_RENDERER_INTERFACE_CENSUS_AND_REFERENCE_TAKEOVER_BRIDGE_V1_6_COMPLETE\n'
printf 'MATERIALIZER_SOURCE_EXECUTED=false\n'
printf 'ADAPTER_IMPLEMENTATION_READY=false\n'
printf 'REFERENCE_NORM_CONTINUITY=true\n'
printf 'FRESH_ROUND_ANSWERS_RESET=true\n'
printf 'TRAINER_EXECUTION_AUTHORIZED=false\n'
printf 'TRAINING_EXECUTION_COUNT=0\n'
printf 'NEXT_GATE=BUILD_EXACT_SCHEMA_AWARE_RENDERER_ADAPTER_FROM_CENSUS\n'
printf 'OUTPUT_ROOT=%s\n' "$OUTPUT_ROOT"
printf 'REVIEW_ZIP=%s\n' "$OUTPUT_ROOT/review.zip"
