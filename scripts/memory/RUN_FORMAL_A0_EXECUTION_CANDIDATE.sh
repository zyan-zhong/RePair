#!/usr/bin/env bash
# Formal Package A execution candidate. It never submits itself to Slurm.
# No global strict-shell option mutation.

APPROVAL="PACKAGE_A0_LOCAL_MECHANISM_EXECUTION_APPROVED"

if [ "${PACKAGE_A0_SCIENTIFIC_EXECUTION_APPROVAL:-}" != "$APPROVAL" ]; then
    echo "STOP=PACKAGE_A0_SCIENTIFIC_EXECUTION_APPROVAL_MISSING" >&2
    exit 70
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [ ! -d "$REPO_ROOT/src/pchsi" ]; then
    echo "STOP=FORMAL_A0_REPO_SRC_LAYOUT_MISSING" >&2
    exit 71
fi

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_ROOT" || exit 71

for required in A0_MANIFEST A0_INPUT_BINDING A0_RUNTIME_BINDING A0_CELLS_ROOT
do
    eval "value=\${$required:-}"
    if [ -z "$value" ]; then
        echo "STOP=MISSING_$required" >&2
        exit 72
    fi
done

mkdir -p "$A0_CELLS_ROOT" || exit 73

index=0
while [ "$index" -lt 12 ]
do
    cell_dir="$A0_CELLS_ROOT/cell_$(printf '%02d' "$index")"
    mkdir -p "$cell_dir" || exit 73

    if [ -f "$cell_dir/cell_result.json" ] && [ -f "$cell_dir/resolved_attempt.json" ]; then
        echo "FORMAL_A0_RESUME_SKIP_RESOLVED_CELL=$index"
        index=$((index + 1))
        continue
    fi

    attempt=0
    resolved=false
    while [ "$attempt" -lt 3 ]
    do
        target="$cell_dir/attempt_$(printf '%03d' "$attempt")"
        if [ -e "$target" ]; then
            attempt=$((attempt + 1))
            continue
        fi

        python scripts/memory/run_formal_a0_cell_v1.py \
          --manifest "$A0_MANIFEST" \
          --input-binding "$A0_INPUT_BINDING" \
          --runtime-binding "$A0_RUNTIME_BINDING" \
          --cell-index "$index" \
          --attempt-index "$attempt" \
          --output-dir "$target"
        rc=$?

        if [ "$rc" -eq 0 ]; then
            cp "$target/cell_result.json" "$cell_dir/cell_result.json" || exit 74
            RESULT_SHA="$(
                sha256sum "$cell_dir/cell_result.json" |
                awk '{print $1}'
            )"
            python - "$cell_dir/resolved_attempt.json" "$index" "$attempt" "$RESULT_SHA" <<'PY'
import json
import os
import sys

path, cell_index, attempt_index, digest = sys.argv[1:]
payload = {
    "schema_id": "FORMAL_A0_RESOLVED_ATTEMPT_V1",
    "schema_version": 1,
    "cell_index": int(cell_index),
    "attempt_index": int(attempt_index),
    "attempt_relative_directory": "attempt_" + str(int(attempt_index)).zfill(3),
    "cell_result_file_sha256": digest,
}
data = (
    json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    + "\n"
).encode("utf-8")
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    os.write(fd, data)
    os.fsync(fd)
finally:
    os.close(fd)
PY
            receipt_rc=$?
            if [ "$receipt_rc" -ne 0 ]; then
                echo "STOP=FORMAL_A0_RESOLVED_ATTEMPT_RECEIPT_FAILED" >&2
                exit "$receipt_rc"
            fi
            resolved=true
            break
        fi

        if [ "$rc" -eq 75 ]; then
            echo "FORMAL_A0_EXACT_CELL_INFRA_RETRY=$index ATTEMPT=$attempt"
            attempt=$((attempt + 1))
            continue
        fi

        # 76 = post-execution ambiguity, 77 = no Policy exposure / pre-execution
        # identity failure. Neither is eligible for automatic scientific retry.
        echo "FORMAL_A0_EXECUTION_HARD_STOP_CELL=$index RC=$rc" >&2
        exit "$rc"
    done

    if [ "$resolved" != "true" ]; then
        echo "STOP=FORMAL_A0_PRE_RESULT_INFRA_RETRY_EXHAUSTED_CELL_$index" >&2
        exit 75
    fi

    index=$((index + 1))
done

echo "FORMAL_A0_ALL_12_CELLS_RESOLVED"
