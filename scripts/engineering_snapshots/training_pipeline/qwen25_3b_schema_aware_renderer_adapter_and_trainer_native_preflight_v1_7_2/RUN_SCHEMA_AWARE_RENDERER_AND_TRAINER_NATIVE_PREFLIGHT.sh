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
    echo "STOP=QWEN_RENDERER_V1_7_STAGE_FAILED:$script"
    exit "$rc"
  fi
}

run_stage 00_VERIFY_PACKAGE.sh
run_stage 10_VERIFY_UPSTREAM_AUTHORITIES.sh
run_stage 20_REPRODUCE_HISTORICAL_RENDERER_84.sh
run_stage 30_MATERIALIZE_CURRENT_T2_TRAINER_NATIVE.sh
run_stage 40_BUILD_CHINESE_MAINLINE_AND_PREFLIGHT.sh
run_stage 50_BUILD_REVIEW.sh

source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

printf '\n================ 中文科研主线状态 ================\n'
printf '当前轮次=人工参考轮\n'
printf '当前阶段=12条T2已转Trainer原生数据，等待Train17_LoRA继续训练Runner审核\n'
printf '人工轮作用=建立分析规范_训练规范_TeacherTraces_供Strong与Local后续继承\n'
printf 'Strong接管原则=继承规范与TeacherTraces_重置FreshRound答案\n'
printf 'Trainer执行授权=false\n'
printf '训练执行次数=0\n'
printf 'Strong接管执行就绪=false\n'
printf 'Local自主执行就绪=false\n'
printf '下一关=审核并构建Train17_LoRA继续训练Runner\n'
printf 'OUTPUT_ROOT=%s\n' "$OUTPUT_ROOT"
printf 'REVIEW_ZIP=%s\n' "$OUTPUT_ROOT/review.zip"
