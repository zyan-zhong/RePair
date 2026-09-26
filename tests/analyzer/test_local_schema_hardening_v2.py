from __future__ import annotations

from pchsi.analyzer.schema_contract import load_schema


def _local_schema() -> dict[str, object]:
    return load_schema("ANALYZER_LOCAL_RESULT_V2")


def test_local_schema_condition_enum_is_a0_a1_only() -> None:
    schema = _local_schema()
    assert schema["properties"]["condition_id"]["enum"] == [
        "A0_ONE_SHOT_LOCAL",
        "A1_MULTI_HYPOTHESIS_LOCAL",
    ]


def test_local_schema_requires_privileged_post_episode_boundary() -> None:
    schema = _local_schema()
    props = schema["properties"]
    required = set(schema["required"])
    assert props["scientific_use"] == {
        "type": "string",
        "const": "PRIVILEGED_OFFLINE_ANALYSIS",
    }
    assert props["analysis_time_information_boundary"] == {
        "type": "string",
        "const": "POST_EPISODE_DEV_ONLY",
    }
    assert {"scientific_use", "analysis_time_information_boundary"} <= required


def test_local_schema_excludes_repair_kind_abstain() -> None:
    schema = _local_schema()
    repair_kinds = (
        schema["properties"]["local_repairs"]["items"]["properties"]
        ["repair_kind"]["enum"]
    )
    assert "ABSTAIN" not in repair_kinds
    assert repair_kinds == ["EXACT_ACTION", "SHORT_OPTION", "TRAINABLE_RULE"]


def test_success_optimization_candidates_require_environment_verification() -> None:
    schema = _local_schema()
    success = schema["properties"]["success_analysis"]["properties"]
    for category in ("redundancy_candidates", "efficiency_candidates"):
        contract = (
            success[category]["items"]["properties"]
            ["requires_environment_verification"]
        )
        assert contract == {"type": "boolean", "const": True}
