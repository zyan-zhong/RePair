from __future__ import annotations
from collections.abc import Mapping

from pchsi.reference_loop.canonical import domain_hash


_GROUP_ACCESS_SCHEMA_ID = "CLEAN_ANALYZER_GROUP_TASK_ACCESS_V1"


def _require_text(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ch in value for ch in "\x00\r\n")
    ):
        raise ValueError(f"{name} must be non-empty single-line text")
    return value


def _require_sha256(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _validate_group_access(
    record: Mapping[str, object],
    *,
    live_call: bool,
) -> None:
    if record.get("schema_id") != _GROUP_ACCESS_SCHEMA_ID:
        raise ValueError("group task-access schema mismatch")
    if record.get("schema_version") != 1:
        raise ValueError("group task-access schema version mismatch")
    observed_hash = domain_hash(
        _GROUP_ACCESS_SCHEMA_ID,
        record,
        excluded_field="group_task_access_sha256",
    )
    if record.get("group_task_access_sha256") != observed_hash:
        raise ValueError("group task-access hash mismatch")
    if record.get("scientific_unit_type") != "GROUP":
        raise ValueError("group task-access scientific unit mismatch")
    if record.get("access_class") != "TRAIN_UPDATE_ANALYZER_GROUP_VISIBLE":
        raise ValueError("group task-access class mismatch")
    if record.get("dataset_split") != "train":
        raise ValueError("group task-access split mismatch")
    if record.get("source_pool") != "TRAIN_UPDATE":
        raise ValueError("group task-access source pool mismatch")
    if live_call and record.get("teacher_call_permitted") is not True:
        raise ValueError("teacher_call_permitted=false")
    for key in (
        "training_permitted",
        "select_evaluation_permitted",
        "confirmatory_permitted",
        "benchmark_result_values_visible",
        "policy_action_authority",
    ):
        if record.get(key) is not False:
            raise ValueError(f"group task-access authority mismatch: {key}")
    if record.get("synthetic_single_task_identity_used") is not False:
        raise ValueError("group access cannot synthesize one representative task")
    if record.get("all_member_task_access_validated") is not True:
        raise ValueError("group member task-access validation is incomplete")

    _require_text("round_id", record.get("round_id"))
    _require_sha256("group_id", record.get("group_id"))
    _require_sha256(
        "group_manifest_sha256",
        record.get("group_manifest_sha256"),
    )
    _require_sha256(
        "source_campaign_sha256",
        record.get("source_campaign_sha256"),
    )
    _require_sha256(
        "evidence_cutoff_sha256",
        record.get("evidence_cutoff_sha256"),
    )
    _require_sha256(
        "group_task_access_sha256",
        record.get("group_task_access_sha256"),
    )

    source_rows = record.get("source_access_rows")
    member_rows = record.get("group_member_source_bindings")
    if not isinstance(source_rows, list) or not source_rows:
        raise ValueError("group task-access source rows must be non-empty")
    if not isinstance(member_rows, list) or not member_rows:
        raise ValueError("group task-access member rows must be non-empty")

    source_ids: set[str] = set()
    task_ids: set[str] = set()
    access_shas: set[str] = set()
    for row in source_rows:
        if not isinstance(row, Mapping):
            raise ValueError("group source access row must be object")
        source = _require_text("source_unit_id", row.get("source_unit_id"))
        task_id = _require_text("task_id", row.get("task_id"))
        _require_sha256("gamefile_sha256", row.get("gamefile_sha256"))
        access_sha = _require_sha256(
            "task_access_sha256",
            row.get("task_access_sha256"),
        )
        if source in source_ids:
            raise ValueError("duplicate group source access authority")
        if task_id in task_ids:
            raise ValueError("duplicate group task access authority")
        if access_sha in access_shas:
            raise ValueError("duplicate group task-access SHA")
        source_ids.add(source)
        task_ids.add(task_id)
        access_shas.add(access_sha)

    member_keys: set[tuple[str, str]] = set()
    observed_member_sources: set[str] = set()
    for row in member_rows:
        if not isinstance(row, Mapping):
            raise ValueError("group member/source binding must be object")
        source = _require_text("source_unit_id", row.get("source_unit_id"))
        local_sha = _require_sha256(
            "local_result_sha256",
            row.get("local_result_sha256"),
        )
        error_id = _require_text(
            "error_instance_id",
            row.get("error_instance_id"),
        )
        _require_sha256(
            "source_state_sha256",
            row.get("source_state_sha256"),
        )
        if source not in source_ids:
            raise ValueError("group member lacks source access authority")
        key = (local_sha, error_id)
        if key in member_keys:
            raise ValueError("duplicate group member identity")
        member_keys.add(key)
        observed_member_sources.add(source)

    if observed_member_sources != source_ids:
        raise ValueError("unused or missing group source access authority")

    if record.get("member_count") != len(member_rows):
        raise ValueError("group member count mismatch")
    if record.get("source_unit_count") != len(source_ids):
        raise ValueError("group source-unit count mismatch")
    if record.get("unique_task_count") != len(task_ids):
        raise ValueError("group unique-task count mismatch")


def validate_task_access(
    record: Mapping[str, object],
    *,
    live_call: bool = True,
) -> None:
    if record.get("schema_id") == _GROUP_ACCESS_SCHEMA_ID:
        _validate_group_access(record, live_call=live_call)
        return

    if live_call and record.get("teacher_call_permitted") is not True:
        raise ValueError("teacher_call_permitted=false")
    for key in (
        "task_id",
        "gamefile_sha256",
        "access_class",
        "dataset_split",
        "training_permitted",
        "select_evaluation_permitted",
        "confirmatory_permitted",
    ):
        if key not in record:
            raise ValueError(f"task-access record missing {key}")
