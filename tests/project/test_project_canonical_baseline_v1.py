from __future__ import annotations

import json
from pathlib import Path


def test_project_canonical_baseline_contains_nonnegotiable_route() -> None:
    value = json.loads(
        Path(
            "configs/project/project_canonical_baseline_and_route_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert value["scientific_mainline"] == (
        "RESEARCH_GUIDED_POLICY_SELF_IMPROVEMENT"
    )
    assert value["change_authority"] == (
        "EXPLICIT_PROJECT_OWNER_INSTRUCTION_ONLY"
    )
    assert value["final_routine_human_decisions"] == 0
    assert value["final_routine_strong_model_calls"] == 0
    assert value["final_role_modes"] == [
        "ROLE_POLICY",
        "ROLE_ANALYZER",
        "ROLE_RESEARCH_PLANNER",
    ]
    assert "STRONG_MODEL_REFERENCE" in value["benchmark_lineage"]
    assert value["server_scripts_root"] == (
        "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts"
    )
