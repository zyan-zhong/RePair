#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"
python - <<'PY'
import ast, json
from pathlib import Path
for p in Path('.').rglob('*.py'):
    ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
for p in Path('plans').glob('*.json'):
    json.loads(p.read_text(encoding='utf-8'))
print('FULL_ROUND_PACKAGE_AST_JSON_PASS')
PY
bash -n RUN_FULL_ROUND.sh VERIFY_PACKAGE.sh
python -m pytest -q tests
python - <<'PY'
from pathlib import Path
s=Path('full_round_driver.py').read_text()
assert 'shell=False' in s
assert 'PARTIAL_UNSAFE_GATE' in s
assert 'REUSED_EXISTING_TERMINAL_RECEIPT' in s
assert 'PLAN_HAS_UNBOUND_GATES' in s
assert 'subprocess.run(' in s
assert 'shell=True' not in s
plan=Path('plans/CANONICAL_PI_K_TO_NEXT_ROUND_STANDARD_V1.json').read_text()
for x in ('POLICY_ROLLOUT_WITH_POLICY_MEMORY_VIEW','RESEARCH_PLANNER_PRE','SAME_STATE_F0_F1','INDEPENDENT_ENVIRONMENT_VERIFICATION','RESEARCH_PLANNER_POST','MEMORY_ROUND_MAINTENANCE','TRAIN_OR_NO_TRAIN_GATE','POLICY_UPDATE_IF_AUTHORIZED','MEMORY_OFF_HARNESS_OFF_ACCEPTANCE','PROMOTE_OR_ROLLBACK','OUTER_LOOP_STOP_GOVERNANCE','NEXT_ROUND_TRANSITION_IF_AUTHORIZED'):
    assert x in plan
print('FULL_ROUND_STATIC_ASSERTIONS_PASS')
PY
if [ -f PACKAGE_FILES.sha256 ]; then sha256sum -c PACKAGE_FILES.sha256; fi
echo PCHSI_RECEIPT_DRIVEN_FULL_ROUND_DRIVER_V1_1_VERIFY_PASS
