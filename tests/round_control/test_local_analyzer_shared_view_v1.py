from __future__ import annotations

from pchsi.round_control.local_analyzer_shared_view import (
    LOCAL_ANALYZER_COMPACT_STAGES_V1,
    build_local_analyzer_shared_user_projection_v1,
)


def _catalog(pack_sha: str):
    return {
        "schema_id": "ANALYZER_EVIDENCE_REFERENCE_CATALOG_V1",
        "evidence_pack_sha256": pack_sha,
        "copy_policy": "COPY",
        "mechanical_selector_policy": "LOCAL_SELECTOR",
        "trajectory_calls": [
            {
                "artifact_sha256": pack_sha,
                "evidence_kind": "TRAJECTORY_CALL",
                "local_selector": "$/trajectory/0",
                "authority": "DETERMINISTIC_FACT",
            }
        ],
        "mechanical_facts": [
            {
                "artifact_sha256": pack_sha,
                "evidence_kind": "MECHANICAL_FACT",
                "local_selector": "$/mechanical/0",
                "authority": "DETERMINISTIC_FACT",
            }
        ],
        "counterexamples": [],
    }


def _projection():
    pack_sha = "a" * 64
    return {
        "evidence_pack_sha256": pack_sha,
        "evidence_pack": {
            "schema_id": "ANALYZER_EVIDENCE_PACK_V1",
            "trajectory": [
                {
                    "public_task_goal": "goal",
                    "executed_history": ["look"],
                    "policy_prompt_text": "large duplicate prompt",
                    "observation_before": "room",
                    "admissible_commands": ["look", "go north"],
                    "raw_model_response": '{"action":"look"}',
                    "final_executed_action": "look",
                    "resulting_observation": "room",
                    "resulting_admissible_commands": [
                        "look",
                        "go north",
                    ],
                    "budget_before": {"steps": 30},
                    "budget_after": {"steps": 29},
                },
                {
                    "public_task_goal": "goal",
                    "executed_history": ["look", "go north"],
                    "policy_prompt_text": "large duplicate prompt 2",
                    "observation_before": "room",
                    "admissible_commands": ["look", "go north"],
                    "raw_model_response": '{"action":"go north"}',
                    "final_executed_action": "go north",
                    "resulting_observation": "hall",
                    "resulting_admissible_commands": ["look"],
                    "budget_before": {"steps": 29},
                    "budget_after": {"steps": 28},
                },
            ],
            "mechanical_evidence": {"facts": []},
        },
        "evidence_reference_catalog": _catalog(pack_sha),
        "local_repair_contract": {"effect_authority": False},
        "memory_pack_sha256": None,
    }


def test_only_l_a0_l_a1_use_compact_route():
    assert LOCAL_ANALYZER_COMPACT_STAGES_V1 == {
        "L-A0",
        "L-A1",
    }
    source = _projection()
    unchanged = build_local_analyzer_shared_user_projection_v1(
        original_user_projection=source,
        stage_id="G-A2",
    )
    assert unchanged == source
    assert unchanged is not source


def test_compact_route_removes_only_stage6o_duplicate_fields_and_factors_values():
    out = build_local_analyzer_shared_user_projection_v1(
        original_user_projection=_projection(),
        stage_id="L-A0",
    )
    assert out["schema_id"] == "LOCAL_RI_ANALYZER_COMPACT_VIEW_V2"
    pack = out["evidence_pack_view"]
    assert len(pack["trajectory"]) == 2
    assert "trajectory_value_tables_v2" in pack
    for row in pack["trajectory"]:
        assert "public_task_goal" not in row
        assert "executed_history" not in row
        assert "policy_prompt_text" not in row
        assert "observation_before_ref" in row
        assert "admissible_commands_ref" in row
    contract = out["projection_contract"]
    assert contract["automatic_truncation_used"] is False
    assert contract["automatic_chunking_used"] is False
    assert contract["example_drop_used"] is False
    assert contract["source_field_omission_authorized"] is False


def test_compact_view_keeps_evidence_and_repair_authority():
    source = _projection()
    out = build_local_analyzer_shared_user_projection_v1(
        original_user_projection=source,
        stage_id="L-A1",
    )
    assert out["source_evidence_pack_sha256"] == "a" * 64
    assert out["local_repair_contract"] == source[
        "local_repair_contract"
    ]
    assert (
        out["evidence_reference_catalog"]["evidence_pack_sha256"]
        == "a" * 64
    )
