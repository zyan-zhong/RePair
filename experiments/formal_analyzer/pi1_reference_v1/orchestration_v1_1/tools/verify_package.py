#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
master = root / "tools" / "master.py"
runner = root / "RUN_TO_HUMAN_PRE_BOUNDARY.sh"

ast.parse(master.read_text(encoding="utf-8"), filename=str(master))

text = master.read_text(encoding="utf-8")
shell = runner.read_text(encoding="utf-8")

for forbidden in (
    "env.step(",
    "alfworld",
    "client.responses.create(",
    "client.beta.responses.create(",
    "R-PRE-SHADOW",
    "R-POST-SHADOW",
):
    if forbidden in text:
        raise SystemExit(f"forbidden master surface: {forbidden}")

if "set -euo pipefail" in shell or "set -euo pipefail" in text:
    raise SystemExit("forbidden shell strict-mode marker present")

if "GROUP_MEMBER_CONFIRMATORY_NOT_PERMITTED" in text:
    raise SystemExit("stale confirmatory-as-live-gate marker present")
if 'source_conditioned_repairs' in text:
    raise SystemExit("stale group-result proposal field present")
if 'source_conditioned_proposals' not in text:
    raise SystemExit("current group-result proposal field missing")

required = (
    "FORMAL_ANALYZER_DAG_REGISTRY_V2",
    "crosscheck_projection_v2",
    "project_candidate",
    "freeze_round_evidence_package",
    "PCHSI_AUTHORIZE_FORMAL_ANALYZER_LIVE",
    "client.batches.create",
    "completion_window=\"24h\"",
    "METHOD_INVALID_K1_STATE_BUDGET_COLLISION",
    "HUMAN_RESEARCHER_PRE_CREATED=false",
)
for marker in required:
    if marker not in text:
        raise SystemExit(f"missing boundary semantic marker: {marker}")

print("PACKAGE_MASTER_AST_PASS")
print("PACKAGE_NO_ENVIRONMENT_OR_DIRECT_RESPONSES_CALL_PASS")
print("PACKAGE_NO_SET_EUO_PIPEFAIL_PASS")
print("PACKAGE_BOUNDARY_MARKERS_PASS")
