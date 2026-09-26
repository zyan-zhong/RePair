#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE" || exit 65
sha256sum -c PACKAGE_FILES.sha256 || exit 66
PYTHONDONTWRITEBYTECODE=1 python - <<'PY' || exit 67
import ast
from pathlib import Path
root=Path('.')
for p in sorted(root.rglob('*.py')):
    if '__pycache__' in p.parts: continue
    ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
print('PACKAGE_AST_PASS')
PY
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests || exit 68
python - <<'PY' || exit 69
from pathlib import Path
root=Path('.')
for name in ('RUN_DETACHED.sh','run_campaign_worker.sh','STATUS.sh','campaign_supervisor.py'):
    text=(root/name).read_text(encoding='utf-8')
    if 'OPENAI_API_KEY' in text: raise SystemExit('LONG_LIVED_SECRET_BOUNDARY_VIOLATION:'+name)
    if 'set -euo pipefail' in text or 'set -e' in text: raise SystemExit('STRICT_SHELL_FORBIDDEN:'+name)
print('LONG_LIVED_SECRET_AND_SHELL_BOUNDARY_PASS')
PY
echo "STRONG_PRIMARY_AUTONOMOUS_CAMPAIGN_DRIVER_V1_11_0_PACKAGE_VERIFY_PASS"
echo "STRICT_SHELL_ERREXIT_NOUNSET_PIPEFAIL_ENABLED=false"
echo "V110_RUNTIME_INHERITANCE_FROM_PROC=true"
echo "V110_ACCEPTED_POST_ADOPTION_NO_RESEND=true"
echo "NO_TRAIN_FIXED_HEAD_SIGNATURE_RECOVERY=true"
echo "ACTION_ONLY_TRAINING_FALLBACK_ALLOWED=false"
echo "FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false"
