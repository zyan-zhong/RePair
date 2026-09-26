from __future__ import annotations

from pathlib import Path

from pchsi.round_control.clean_role_actor_binding import human_primary_strong_shadow_bindings


ANALYZER_STAGES = ("L-A0", "L-A1", "G-A2", "G-A3", "C", "X")


def test_human_primary_strong_shadow_reuses_existing_actor_entrypoints() -> None:
    repo = Path(__file__).resolve().parents[2]
    bindings = human_primary_strong_shadow_bindings(repo)
    keyed = {(row.logical_role, row.actor, row.stage_id): row for row in bindings}

    for stage_id in ANALYZER_STAGES:
        human = keyed[("ANALYZER", "HUMAN", stage_id)]
        strong = keyed[("ANALYZER", "STRONG", stage_id)]
        assert human.entrypoint_relative_path == "scripts/analyzer/freeze_human_analyzer_primary_v1.py"
        assert human.transport_kind == "HUMAN_FREEZE"
        assert human.blind_input_required is True
        assert human.human_content_visibility_allowed is True
        assert strong.entrypoint_relative_path == "src/pchsi/cognitive_runtime/orchestrator.py"
        assert strong.transport_kind == "EXISTING_COGNITIVE_RUNTIME_P2"
        assert strong.blind_input_required is True
        assert strong.human_content_visibility_allowed is False

    pre_human = keyed[("RESEARCH_PLANNER_PRE", "HUMAN", None)]
    pre_strong = keyed[("RESEARCH_PLANNER_PRE", "STRONG", "R-PRE-SHADOW-HYDRATED-V2")]
    post_strong = keyed[("RESEARCH_PLANNER_POST", "STRONG", "R-POST-SHADOW")]
    assert pre_human.entrypoint_relative_path.endswith("freeze_human_researcher_pre_v2.py")
    assert pre_strong.human_content_visibility_allowed is False
    assert post_strong.blind_input_required is True
