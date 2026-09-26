#!/usr/bin/env bash
package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$package_dir" || exit 1
python="$(python3 entry/bootstrap.py)"
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
"$python" -B entry/progress.py "$@"
rc=$?
exit "$rc"
