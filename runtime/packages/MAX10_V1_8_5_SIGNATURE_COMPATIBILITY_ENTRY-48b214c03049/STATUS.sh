#!/usr/bin/env bash
package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
base="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_source_root"])' "$package_dir/AUTHORITY.json")"
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
bash "$base/STATUS.sh" "$@"
exit $?
