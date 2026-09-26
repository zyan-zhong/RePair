#!/usr/bin/env bash
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
source "$PACKAGE_ROOT/PACKAGE_ENV.sh"

echo "【阶段30】当前12条T2转Trainer原生数据"
python "$PACKAGE_ROOT/tools/materialize_current_t2_trainer_native.py"
rc=$?
printf '30_MATERIALIZE_CURRENT_T2_TRAINER_NATIVE.sh_RC=%s\n' "$rc"
exit "$rc"
