from __future__ import annotations

from copy import deepcopy

import pytest

from pchsi.round_control.clean_analyzer_input_materialization import (
    build_actor_input_binding,
    build_local_u_reg_manifest,
    build_round_analyzer_resource_budget,
    select_failure_only_u_reg,
    validate_round_analyzer_resource_budget,
)


def _stage_rows() -> list[dict[str, object]]:
    return [
        {
            "stage_id": "L-A0",
            "condition_id": "A0",
            "role": "ANALYZER",
            "scientific_unit_type": "EPISODE",
            "memory_exposure": False,
            "logical_call_budget_per_unit": 1,
        },
        {
            "stage_id": "L-A1",
            "condition_id": "A1",
            "role": "ANALYZER",
            "scientific_unit_type": "EPISODE",
            "memory_exposure": False,
            "logical_call_budget_per_unit": 1,
        },
    ]


def _row(index: int, family: str) -> dict[str, object]:
    token = f"{index:064x}"
    return {
        "classification": "TASK_FAILURE",
        "source_campaign_sha256": "a" * 64,
        "policy_interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "scientific_cell_id": f"cell-{index:03d}",
        "execution_attempt_id": f"attempt-{index:03d}",
        "task_id": f"task-{index:03d}",
        "task_type": family,
        "attempt_bundle_sha256": token,
        "episode_semantic_sha256": f"{index + 1000:064x}",
        "attempt_bundle_relpath": f"attempts/{index:03d}",
    }


def test_budget_derives_state_count_from_logical_call_cap() -> None:
    budget = build_round_analyzer_resource_budget(
        round_id="round-1",
        policy_version="pi0",
        producer_role="REFERENCE_EXPERIMENT_CONTRACT",
        source_authority_sha256="b" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=22,
    )
    validate_round_analyzer_resource_budget(budget)
    assert budget["per_source_state_logical_calls"] == 2
    assert budget["maximum_source_state_count"] == 11
    assert budget["manual_source_state_count_input_allowed"] is False
    assert budget["failure_success_ratio_input_allowed"] is False
    assert budget["analyzer_self_budgeting_allowed"] is False
    assert budget["analyzer_self_denominator_selection_allowed"] is False
    assert budget["selection_is_deterministic_after_budget_freeze"] is True


def test_budget_is_not_tied_to_one_reference_round_size() -> None:
    first = build_round_analyzer_resource_budget(
        round_id="r1",
        policy_version="p1",
        producer_role="HUMAN_RESEARCH_PLANNER",
        source_authority_sha256="c" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=12,
    )
    second = build_round_analyzer_resource_budget(
        round_id="r2",
        policy_version="p2",
        producer_role="LOCAL_RESEARCH_PLANNER",
        source_authority_sha256="d" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=38,
    )
    assert first["maximum_source_state_count"] == 6
    assert second["maximum_source_state_count"] == 19


def test_failure_only_selection_is_deterministic_and_family_covering() -> None:
    budget = build_round_analyzer_resource_budget(
        round_id="round-1",
        policy_version="pi0",
        producer_role="STRONG_RESEARCH_PLANNER",
        source_authority_sha256="e" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=12,
    )
    rows = [
        _row(0, "family-a"),
        _row(1, "family-a"),
        _row(2, "family-a"),
        _row(3, "family-b"),
        _row(4, "family-b"),
        _row(5, "family-c"),
        _row(6, "family-c"),
    ]
    first = select_failure_only_u_reg(
        failure_rows=rows,
        resource_budget=budget,
        source_campaign_sha256="a" * 64,
    )
    second = select_failure_only_u_reg(
        failure_rows=reversed(rows),
        resource_budget=budget,
        source_campaign_sha256="a" * 64,
    )
    assert first == second
    assert len(first) == 6
    assert {row["task_type"] for row in first[:3]} == {
        "family-a",
        "family-b",
        "family-c",
    }
    assert [row["selection_rank"] for row in first] == list(range(6))


def test_success_or_cross_campaign_rows_are_rejected() -> None:
    budget = build_round_analyzer_resource_budget(
        round_id="round-1",
        policy_version="pi0",
        producer_role="REFERENCE_EXPERIMENT_CONTRACT",
        source_authority_sha256="f" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=2,
    )
    success = _row(0, "family-a")
    success["classification"] = "SUCCESS"
    with pytest.raises(ValueError, match="failure-only"):
        select_failure_only_u_reg(
            failure_rows=[success],
            resource_budget=budget,
            source_campaign_sha256="a" * 64,
        )

    other = _row(1, "family-a")
    other["source_campaign_sha256"] = "9" * 64
    with pytest.raises(ValueError, match="source campaign"):
        select_failure_only_u_reg(
            failure_rows=[other],
            resource_budget=budget,
            source_campaign_sha256="a" * 64,
        )


def test_budget_hash_tampering_fails_closed() -> None:
    budget = build_round_analyzer_resource_budget(
        round_id="round-1",
        policy_version="pi0",
        producer_role="REFERENCE_EXPERIMENT_CONTRACT",
        source_authority_sha256="1" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=10,
    )
    tampered = deepcopy(budget)
    tampered["local_logical_call_cap"] = 12
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_round_analyzer_resource_budget(tampered)


def test_u_reg_and_actor_binding_preserve_scientific_boundaries() -> None:
    budget = build_round_analyzer_resource_budget(
        round_id="round-1",
        policy_version="pi0",
        producer_role="REFERENCE_EXPERIMENT_CONTRACT",
        source_authority_sha256="2" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=4,
    )
    selected = select_failure_only_u_reg(
        failure_rows=[_row(0, "family-a"), _row(1, "family-b")],
        resource_budget=budget,
        source_campaign_sha256="a" * 64,
    )
    enriched = []
    for index, row in enumerate(selected):
        item = dict(row)
        item["gamefile_sha256"] = f"{index + 2000:064x}"
        item["source_unit_id"] = f"source-{index}"
        enriched.append(item)
    u_reg = build_local_u_reg_manifest(
        round_id="round-1",
        policy_version="pi0",
        evidence_cutoff_sha256="3" * 64,
        failure_universe_file_sha256="4" * 64,
        source_campaign_sha256="a" * 64,
        resource_budget=budget,
        selected_units=enriched,
    )
    assert u_reg["selected_failure_count"] == 2
    assert u_reg["selected_success_count"] == 0
    assert u_reg["human_selected_state_count"] == 0
    assert u_reg["mechanical_outcome_sampling_scheduler_used"] is False

    binding = build_actor_input_binding(
        round_id="round-1",
        runtime_registry_sha256="5" * 64,
        local_u_reg_sha256=u_reg["u_reg_sha256"],
        human_primary_authorized=True,
        strong_shadow_authorized=True,
    )
    assert binding["shared_input_registry_for_human_and_strong"] is True
    assert binding["strong_shadow_human_content_visible"] is False
    assert binding["local_shadow_future_compatible"] is True
    assert binding["benefit_harm_authority"] is False


def test_budget_requires_complete_a0_a1_stage_contract() -> None:
    missing_a1 = _stage_rows()[:1]
    with pytest.raises(ValueError, match="exactly L-A0/A0 and L-A1/A1"):
        build_round_analyzer_resource_budget(
            round_id="round-1",
            policy_version="pi0",
            producer_role="REFERENCE_EXPERIMENT_CONTRACT",
            source_authority_sha256="6" * 64,
            local_stage_rows=missing_a1,
            local_logical_call_cap=10,
        )

    wrong_condition = _stage_rows()
    wrong_condition[1]["condition_id"] = "A0"
    with pytest.raises(ValueError, match="exactly L-A0/A0 and L-A1/A1"):
        build_round_analyzer_resource_budget(
            round_id="round-1",
            policy_version="pi0",
            producer_role="REFERENCE_EXPERIMENT_CONTRACT",
            source_authority_sha256="7" * 64,
            local_stage_rows=wrong_condition,
            local_logical_call_cap=10,
        )


def test_budget_records_unallocated_logical_calls_without_manual_state_count() -> None:
    budget = build_round_analyzer_resource_budget(
        round_id="round-1",
        policy_version="pi0",
        producer_role="LOCAL_RESEARCH_PLANNER",
        source_authority_sha256="8" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=11,
    )
    assert budget["maximum_source_state_count"] == 5
    assert budget["unallocated_local_logical_call_count"] == 1
    validate_round_analyzer_resource_budget(budget)


def test_selected_row_preserves_frozen_source_evidence_identity() -> None:
    budget = build_round_analyzer_resource_budget(
        round_id="round-1",
        policy_version="pi0",
        producer_role="STRONG_RESEARCH_PLANNER",
        source_authority_sha256="9" * 64,
        local_stage_rows=_stage_rows(),
        local_logical_call_cap=2,
    )
    source = _row(9, "family-a")
    selected = select_failure_only_u_reg(
        failure_rows=[source],
        resource_budget=budget,
        source_campaign_sha256="a" * 64,
    )
    from pchsi.reference_loop.canonical import domain_hash

    assert selected[0]["source_evidence_index_row_sha256"] == domain_hash(
        "PI0_I1_TRAIN_UPDATE_EVIDENCE_INDEX_ROW_V1",
        source,
    )
