#!/bin/bash
set -e

PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${STAGE4D_PYTHON:-/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python}"
LOG_ROOT="${STAGE4D_LOG_ROOT:-/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/logs/stage4d_existing_select_live_binding_v1}"
mkdir -p "$LOG_ROOT"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PREPARE_LOG="$LOG_ROOT/prepare_${STAMP}.log"

cd "$PACKAGE_ROOT"
"$PY" -m stage4d_pkg.prepare 2>&1 | tee "$PREPARE_LOG"
PREPARE_RC="${PIPESTATUS[0]}"
if test "$PREPARE_RC" -ne 0; then
  echo "STOP=STAGE4D_PREPARE_FAILED"
  exit "$PREPARE_RC"
fi

BINDING_ROOT="$(grep '^STAGE4D_BINDING_ROOT=' "$PREPARE_LOG" | tail -n 1 | cut -d= -f2-)"
if test -z "$BINDING_ROOT" || test ! -d "$BINDING_ROOT"; then
  echo "STOP=STAGE4D_BINDING_ROOT_NOT_RESOLVED"
  exit 20
fi

BINDING_SHA="$(grep '^STAGE4D_BINDING_SHA256=' "$PREPARE_LOG" | tail -n 1 | cut -d= -f2-)"
if test -z "$BINDING_SHA"; then
  echo "STOP=STAGE4D_BINDING_SHA_NOT_RESOLVED"
  exit 21
fi

JOB_SCRIPT="$PACKAGE_ROOT/generated_readiness_${BINDING_SHA:0:12}.sbatch"
if test -e "$JOB_SCRIPT"; then
  echo "STOP=READINESS_JOB_SCRIPT_ALREADY_EXISTS:$JOB_SCRIPT"
  exit 22
fi

cat > "$JOB_SCRIPT" <<EOF
#!/bin/bash
#SBATCH -J st4d_select_ready
#SBATCH -p gpu_a800
#SBATCH --gpus=1
#SBATCH --time=00:10:00
#SBATCH --export=NIL
#SBATCH --output=$LOG_ROOT/readiness_%j.out
#SBATCH --error=$LOG_ROOT/readiness_%j.err

cd "$PACKAGE_ROOT"
exec "$PY" -m stage4d_pkg.readiness --binding-root "$BINDING_ROOT"
EOF
chmod 700 "$JOB_SCRIPT"

SUBMIT_OUTPUT="$(sbatch "$JOB_SCRIPT")"
printf '%s\n' "$SUBMIT_OUTPUT"
JOB_ID="$(printf '%s\n' "$SUBMIT_OUTPUT" | awk '{print $NF}')"

if ! printf '%s' "$JOB_ID" | grep -Eq '^[0-9]+$'; then
  echo "STOP=SLURM_JOB_ID_NOT_PARSED"
  exit 23
fi

echo "STAGE4D_READINESS_SUBMITTED"
echo "STAGE4D_BINDING_ROOT=$BINDING_ROOT"
echo "STAGE4D_BINDING_SHA256=$BINDING_SHA"
echo "READINESS_JOB_ID=$JOB_ID"
echo "READINESS_STDOUT=$LOG_ROOT/readiness_${JOB_ID}.out"
echo "READINESS_STDERR=$LOG_ROOT/readiness_${JOB_ID}.err"
echo "EVALUATION_EXECUTION_AUTHORIZED=false"
echo "SCIENTIFIC_SELECT_CELL_EXECUTION_COUNT=0"
echo "NEXT_GATE=WAIT_FOR_NONSCIENTIFIC_READINESS_RECEIPT"
