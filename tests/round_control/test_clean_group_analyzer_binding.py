from __future__ import annotations

import pytest

from pchsi.reference_loop.canonical import domain_hash
from pchsi.round_control.clean_group_analyzer_binding import (
    build_clean_group_task_access_record,
    build_group_universe,
    build_round_group_analyzer_resource_authority,
    validate_round_group_analyzer_resource_authority,
)


def _sha(ch: str) -> str:
    return ch * 64


def _rehash_resource(value: dict[str, object]) -> None:
    value["resource_authority_sha256"] = domain_hash(
        "ROUND_GROUP_ANALYZER_RESOURCE_AUTHORITY_V1",
        value,
        excluded_field="resource_authority_sha256",
    )


def _stages() -> list[dict[str, object]]:
    return [
        {
            "stage_id": "G-A2",
            "condition_id": "A2",
            "role": "ANALYZER",
            "scientific_unit_type": "GROUP",
            "memory_exposure": False,
            "logical_call_budget_per_unit": 1,
        },
        {
            "stage_id": "G-A3",
            "condition_id": "A3",
            "role": "ANALYZER",
            "scientific_unit_type": "GROUP",
            "memory_exposure": True,
            "logical_call_budget_per_unit": 1,
        },
    ]


def _task_access(
    source: str,
    task: str,
    game: str,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_id": "CLEAN_ANALYZER_TASK_ACCESS_RECORD_V1",
        "schema_version": 1,
        "round_id": "round",
        "source_unit_id": source,
        "task_id": task,
        "gamefile_sha256": _sha(game),
        "access_class": "TRAIN_UPDATE_ANALYZER_VISIBLE",
        "dataset_split": "train",
        "source_pool": "TRAIN_UPDATE",
        "source_campaign_sha256": _sha("a"),
        "evidence_cutoff_sha256": _sha("b"),
        "teacher_call_permitted": True,
        "training_permitted": False,
        "select_evaluation_permitted": False,
        "confirmatory_permitted": False,
        "benchmark_result_values_visible": False,
        "policy_action_authority": False,
        "task_access_sha256": "0" * 64,
    }
    value["task_access_sha256"] = domain_hash(
        "CLEAN_ANALYZER_TASK_ACCESS_RECORD_V1",
        value,
        excluded_field="task_access_sha256",
    )
    return value


def test_builds_cross_source_group_access_without_representative_task() -> None:
    contexts = [
        {
            "source_unit_id": "u1",
            "local_result_sha256": _sha("1"),
            "error_instance_id": "e1",
            "source_state_sha256": _sha("2"),
        },
        {
            "source_unit_id": "u2",
            "local_result_sha256": _sha("3"),
            "error_instance_id": "e2",
            "source_state_sha256": _sha("4"),
        },
    ]
    value = build_clean_group_task_access_record(
        round_id="round",
        group_id=_sha("5"),
        group_manifest_sha256=_sha("6"),
        member_contexts=contexts,
        task_access_by_source_unit={
            "u1": _task_access("u1", "t1", "7"),
            "u2": _task_access("u2", "t2", "8"),
        },
    )

    assert value["member_count"] == 2
    assert value["source_unit_count"] == 2
    assert value["unique_task_count"] == 2
    assert value["synthetic_single_task_identity_used"] is False


def test_group_access_rejects_missing_source_authority() -> None:
    contexts = [
        {
            "source_unit_id": "u1",
            "local_result_sha256": _sha("1"),
            "error_instance_id": "e1",
            "source_state_sha256": _sha("2"),
        },
        {
            "source_unit_id": "u2",
            "local_result_sha256": _sha("3"),
            "error_instance_id": "e2",
            "source_state_sha256": _sha("4"),
        },
    ]
    with pytest.raises(ValueError):
        build_clean_group_task_access_record(
            round_id="round",
            group_id=_sha("5"),
            group_manifest_sha256=_sha("6"),
            member_contexts=contexts,
            task_access_by_source_unit={
                "u1": _task_access("u1", "t1", "7"),
            },
        )


def test_group_resource_authority_is_round_adaptive() -> None:
    universe = build_group_universe(
        round_id="round",
        group_manifest_sha256s=[
            _sha("1"),
            _sha("2"),
            _sha("3"),
        ],
    )
    stages = _stages()
    value = build_round_group_analyzer_resource_authority(
        round_id="round",
        policy_version="pi0-clean",
        producer_role="REFERENCE_EXPERIMENT_CONTRACT",
        source_authority_sha256=_sha("4"),
        group_universe=universe,
        group_stage_rows=stages,
    )
    validate_round_group_analyzer_resource_authority(value)

    assert value["group_count"] == 3
    assert value["per_group_logical_calls"] == 2
    assert value["required_group_logical_calls"] == 6
    assert value["group_logical_call_cap"] == 6
    assert value["group_sampling_allowed"] is False
    assert value["live_group_execution_authorized"] is False


def test_group_resource_authority_rejects_memory_contract_drift() -> None:
    universe = build_group_universe(
        round_id="round",
        group_manifest_sha256s=[_sha("1")],
    )
    stages = [
        {
            "stage_id": "G-A2",
            "condition_id": "A2",
            "role": "ANALYZER",
            "scientific_unit_type": "GROUP",
            "memory_exposure": True,
            "logical_call_budget_per_unit": 1,
        },
        {
            "stage_id": "G-A3",
            "condition_id": "A3",
            "role": "ANALYZER",
            "scientific_unit_type": "GROUP",
            "memory_exposure": True,
            "logical_call_budget_per_unit": 1,
        },
    ]
    with pytest.raises(ValueError):
        build_round_group_analyzer_resource_authority(
            round_id="round",
            policy_version="pi0-clean",
            producer_role="REFERENCE_EXPERIMENT_CONTRACT",
            source_authority_sha256=_sha("4"),
            group_universe=universe,
            group_stage_rows=stages,
        )


def test_group_resource_validator_rejects_unapproved_producer_even_if_rehashed() -> None:
    universe = build_group_universe(
        round_id="round",
        group_manifest_sha256s=[_sha("1")],
    )
    value = build_round_group_analyzer_resource_authority(
        round_id="round",
        policy_version="pi0-clean",
        producer_role="REFERENCE_EXPERIMENT_CONTRACT",
        source_authority_sha256=_sha("4"),
        group_universe=universe,
        group_stage_rows=_stages(),
    )
    value["producer_role"] = "ANALYZER"
    _rehash_resource(value)
    with pytest.raises(ValueError):
        validate_round_group_analyzer_resource_authority(value)


def test_group_resource_validator_rejects_stage_contract_drift_even_if_rehashed() -> None:
    universe = build_group_universe(
        round_id="round",
        group_manifest_sha256s=[_sha("1")],
    )
    value = build_round_group_analyzer_resource_authority(
        round_id="round",
        policy_version="pi0-clean",
        producer_role="REFERENCE_EXPERIMENT_CONTRACT",
        source_authority_sha256=_sha("4"),
        group_universe=universe,
        group_stage_rows=_stages(),
    )
    value["stage_rows"][0]["memory_exposure"] = True
    _rehash_resource(value)
    with pytest.raises(ValueError):
        validate_round_group_analyzer_resource_authority(value)


def test_group_resource_validator_rejects_budget_unit_drift_even_if_rehashed() -> None:
    universe = build_group_universe(
        round_id="round",
        group_manifest_sha256s=[_sha("1")],
    )
    value = build_round_group_analyzer_resource_authority(
        round_id="round",
        policy_version="pi0-clean",
        producer_role="REFERENCE_EXPERIMENT_CONTRACT",
        source_authority_sha256=_sha("4"),
        group_universe=universe,
        group_stage_rows=_stages(),
    )
    value["budget_unit"] = "SOMETHING_ELSE"
    _rehash_resource(value)
    with pytest.raises(ValueError):
        validate_round_group_analyzer_resource_authority(value)
