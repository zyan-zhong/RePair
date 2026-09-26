#!/usr/bin/env bash
P="$(cd "$(dirname "$0")" && pwd -P)";cd "$P";sha256sum -c PACKAGE_FILES.sha256||exit $?;export PYTHONDONTWRITEBYTECODE=1;C="$(mktemp -d)";export PYTHONPYCACHEPREFIX="$C";python -m pytest -q -p no:cacheprovider tests||{ R=$?;rm -rf "$C";exit $R;};python -m compileall -q round_training tests build_review.py||{ R=$?;rm -rf "$C";exit $R;};python - <<'PY2'
from pathlib import Path
import re
for r in [Path('round_training'),Path('build_review.py')]:
 for p in ([r] if r.is_file() else sorted(r.rglob('*.py'))):
  if re.search(r'[一-鿿]',p.read_text()):raise SystemExit('STOP=PRODUCTION_SOURCE_CONTAINS_CHINESE:'+str(p))
print('PRODUCTION_SOURCE_LANGUAGE_AUDIT_PASS')
PY2
R=$?;test $R -eq 0||{ rm -rf "$C";exit $R;};python build_review.py;R=$?;rm -rf "$C";exit $R
