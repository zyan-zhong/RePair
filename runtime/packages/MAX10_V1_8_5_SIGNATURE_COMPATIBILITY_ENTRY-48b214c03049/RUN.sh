#!/usr/bin/env bash
package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$package_dir" || exit 1
python="$(python3 -c 'import json; print(json.load(open("AUTHORITY.json"))["registered_python"])')"
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
log="$(mktemp "$package_dir/launch.XXXXXX.log")" || exit 1
"$python" -B launch.py 2>&1 | tee "$log"
rc=${PIPESTATUS[0]}
printf 'REGISTERED_CONTINUATION_RC=%s\nLOG=%s\n' "$rc" "$log"
exit "$rc"
