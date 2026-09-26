#!/usr/bin/env bash
set +euo pipefail
package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python -B "$package_dir/VERIFY.py" --server 2>&1 | tee "$package_dir/operator_verify.log"
verify_rc=${PIPESTATUS[0]}
if [ "$verify_rc" -ne 0 ]; then exit "$verify_rc"; fi
python -B "$package_dir/safe_handoff.py" 2>&1 | tee "$package_dir/operator_handoff.log"
run_rc=${PIPESTATUS[0]}
exit "$run_rc"
