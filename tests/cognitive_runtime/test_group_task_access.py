from __future__ import annotations

import pytest

from pchsi.cognitive_runtime.access import validate_task_access
from pchsi.reference_loop.canonical import domain_hash


def _sha(ch: str) -> str:
    return ch * 64


def _group() -> dict[str, object]:
    value: dict[str, object] = {
        "schema_id": "CLEAN_ANALYZER_GROUP_TASK_ACCESS_V1",
        "schema_version": 1,
        "round_id": "round",
        "scientific_unit_type": "GROUP",
        "group_id": _sha("1"),
        "group_manifest_sha256": _sha("2"),
        "access_class": "TRAIN_UPDATE_ANALYZER_GROUP_VISIBLE",
        "dataset_split": "train",
        "source_pool": "TRAIN_UPDATE",
        "source_campaign_sha256": _sha("3"),
        "evidence_cutoff_sha256": _sha("4"),
        "member_count": 2,
        "source_unit_count": 2,
        "unique_task_count": 2,
        "source_access_rows": [
            {
                "source_unit_id": "u1",
                "task_id": "t1",
                "gamefile_sha256": _sha("5"),
                "task_access_sha256": _sha("6"),
            },
            {
                "source_unit_id": "u2",
                "task_id": "t2",
                "gamefile_sha256": _sha("7"),
                "task_access_sha256": _sha("8"),
            },
        ],
        "group_member_source_bindings": [
            {
                "source_unit_id": "u1",
                "local_result_sha256": _sha("9"),
                "error_instance_id": "e1",
                "source_state_sha256": _sha("a"),
            },
            {
                "source_unit_id": "u2",
                "local_result_sha256": _sha("b"),
                "error_instance_id": "e2",
                "source_state_sha256": _sha("c"),
            },
        ],
        "teacher_call_permitted": True,
        "training_permitted": False,
        "select_evaluation_permitted": False,
        "confirmatory_permitted": False,
        "benchmark_result_values_visible": False,
        "policy_action_authority": False,
        "synthetic_single_task_identity_used": False,
        "all_member_task_access_validated": True,
        "group_task_access_sha256": "0" * 64,
    }
    value["group_task_access_sha256"] = domain_hash(
        "CLEAN_ANALYZER_GROUP_TASK_ACCESS_V1",
        value,
        excluded_field="group_task_access_sha256",
    )
    return value


def _rehash(value: dict[str, object]) -> None:
    value["group_task_access_sha256"] = domain_hash(
        "CLEAN_ANALYZER_GROUP_TASK_ACCESS_V1",
        value,
        excluded_field="group_task_access_sha256",
    )


def test_group_task_access_is_accepted() -> None:
    validate_task_access(_group(), live_call=True)


def test_group_task_access_rejects_synthetic_representative_task() -> None:
    value = _group()
    value["synthetic_single_task_identity_used"] = True
    with pytest.raises(ValueError):
        validate_task_access(value, live_call=True)


def test_group_task_access_requires_every_member_source_authority() -> None:
    value = _group()
    value["source_access_rows"] = value["source_access_rows"][:1]
    value["source_unit_count"] = 1
    value["unique_task_count"] = 1
    with pytest.raises(ValueError):
        validate_task_access(value, live_call=True)


def test_existing_single_task_access_contract_is_unchanged() -> None:
    value = {
        "task_id": "t",
        "gamefile_sha256": _sha("1"),
        "access_class": "TRAIN_UPDATE_ANALYZER_VISIBLE",
        "dataset_split": "train",
        "training_permitted": False,
        "select_evaluation_permitted": False,
        "confirmatory_permitted": False,
        "teacher_call_permitted": True,
    }
    validate_task_access(value, live_call=True)


def test_group_task_access_rejects_stale_hash_after_payload_change() -> None:
    value = _group()
    value["round_id"] = "changed-round"
    with pytest.raises(ValueError):
        validate_task_access(value, live_call=True)


def test_group_task_access_requires_schema_version_one() -> None:
    value = _group()
    value["schema_version"] = 2
    _rehash(value)
    with pytest.raises(ValueError):
        validate_task_access(value, live_call=True)


def test_group_task_access_requires_validated_member_authorities() -> None:
    value = _group()
    value["all_member_task_access_validated"] = False
    _rehash(value)
    with pytest.raises(ValueError):
        validate_task_access(value, live_call=True)
