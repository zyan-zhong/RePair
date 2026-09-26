#!/usr/bin/env bash
package_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python_bin=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["registered_python"])' "$package_dir/AUTHORITY.json")
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
if [ "$#" -eq 0 ]; then set -- --preflight-and-run; fi
log_path=$(mktemp "$package_dir/RUN.XXXXXXXX.log")
"$python_bin" -B "$package_dir/entry_v208.py" "${@}" 2>&1 | tee "$log_path"
run_rc=${PIPESTATUS[0]}
printf 'VALIDATION_RC=%s\nLOG_PATH=%s\n' "$run_rc" "$log_path"
exit "$run_rc"
