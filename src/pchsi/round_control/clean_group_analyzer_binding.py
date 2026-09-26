"""Thin group-level access and resource-authority binding.

This module does not modify Analyzer prompts, schemas, grouping, Memory,
provider transport, F0/F1, Research Planner, or training logic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pchsi.cognitive_runtime.access import validate_task_access
from pchsi.reference_loop.canonical import domain_hash


GROUP_ACCESS_SCHEMA_ID = "CLEAN_ANALYZER_GROUP_TASK_ACCESS_V1"
GROUP_RESOURCE_AUTHORITY_SCHEMA_ID = (
    "ROUND_GROUP_ANALYZER_RESOURCE_AUTHORITY_V1"
)
GROUP_UNIVERSE_SCHEMA_ID = "CLEAN_ANALYZER_GROUP_UNIVERSE_V1"

ALLOWED_RESOURCE_PRODUCERS = frozenset(
    {
        "REFERENCE_EXPERIMENT_CONTRACT",
        "HUMAN_RESEARCH_PLANNER",
        "STRONG_RESEARCH_PLANNER",
        "LOCAL_RESEARCH_PLANNER",
    }
)

_REQUIRED_GROUP_STAGE_CONTRACT = {
    "G-A2": ("A2", False),
    "G-A3": ("A3", True),
}


def _text(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ch in value for ch in "\x00\r\n")
    ):
        raise ValueError(f"{name} must be non-empty single-line text")
    return value


def _sha(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _positive_int(name: str, value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be positive integer")
    return value


def _verify_single_source_access(
    value: Mapping[str, object],
) -> None:
    if value.get("schema_id") != "CLEAN_ANALYZER_TASK_ACCESS_RECORD_V1":
        raise ValueError("single-source task access schema mismatch")
    validate_task_access(value, live_call=True)
    observed = domain_hash(
        "CLEAN_ANALYZER_TASK_ACCESS_RECORD_V1",
        value,
        excluded_field="task_access_sha256",
    )
    if value.get("task_access_sha256") != observed:
        raise ValueError("single-source task access hash mismatch")
    if value.get("access_class") != "TRAIN_UPDATE_ANALYZER_VISIBLE":
        raise ValueError("single-source Analyzer access class mismatch")
    if value.get("dataset_split") != "train":
        raise ValueError("single-source Analyzer access split mismatch")
    if value.get("source_pool") != "TRAIN_UPDATE":
        raise ValueError("single-source Analyzer access pool mismatch")
    if value.get("benchmark_result_values_visible") is not False:
        raise ValueError("single-source Analyzer access exposes benchmark")
    if value.get("policy_action_authority") is not False:
        raise ValueError("single-source Analyzer access has policy authority")


def build_clean_group_task_access_record(
    *,
    round_id: str,
    group_id: str,
    group_manifest_sha256: str,
    member_contexts: Sequence[Mapping[str, object]],
    task_access_by_source_unit: Mapping[
        str, Mapping[str, object]
    ],
) -> dict[str, object]:
    _text("round_id", round_id)
    _sha("group_id", group_id)
    _sha("group_manifest_sha256", group_manifest_sha256)
    if not member_contexts:
        raise ValueError("group member contexts must be non-empty")

    member_rows: list[dict[str, object]] = []
    source_ids: set[str] = set()
    member_keys: set[tuple[str, str]] = set()

    for context in member_contexts:
        source = _text(
            "source_unit_id",
            context.get("source_unit_id"),
        )
        local_sha = _sha(
            "local_result_sha256",
            context.get("local_result_sha256"),
        )
        error_id = _text(
            "error_instance_id",
            context.get("error_instance_id"),
        )
        state_sha = _sha(
            "source_state_sha256",
            context.get("source_state_sha256"),
        )
        key = (local_sha, error_id)
        if key in member_keys:
            raise ValueError("duplicate group member context")
        member_keys.add(key)
        source_ids.add(source)
        member_rows.append(
            {
                "source_unit_id": source,
                "local_result_sha256": local_sha,
                "error_instance_id": error_id,
                "source_state_sha256": state_sha,
            }
        )

    source_rows: list[dict[str, object]] = []
    campaign_values: set[str] = set()
    cutoff_values: set[str] = set()
    task_ids: set[str] = set()

    for source in sorted(source_ids):
        access = task_access_by_source_unit.get(source)
        if not isinstance(access, Mapping):
            raise ValueError(
                "group source lacks exact task-access record"
            )
        _verify_single_source_access(access)
        if access.get("source_unit_id") != source:
            raise ValueError("source/task-access identity mismatch")
        task_id = _text("task_id", access.get("task_id"))
        if task_id in task_ids:
            raise ValueError("different source units share task identity")
        task_ids.add(task_id)
        campaign_values.add(
            _sha(
                "source_campaign_sha256",
                access.get("source_campaign_sha256"),
            )
        )
        cutoff_values.add(
            _sha(
                "evidence_cutoff_sha256",
                access.get("evidence_cutoff_sha256"),
            )
        )
        source_rows.append(
            {
                "source_unit_id": source,
                "task_id": task_id,
                "gamefile_sha256": _sha(
                    "gamefile_sha256",
                    access.get("gamefile_sha256"),
                ),
                "task_access_sha256": _sha(
                    "task_access_sha256",
                    access.get("task_access_sha256"),
                ),
            }
        )

    if len(campaign_values) != 1:
        raise ValueError("group members span source campaigns")
    if len(cutoff_values) != 1:
        raise ValueError("group members span evidence cutoffs")

    member_rows.sort(
        key=lambda row: (
            str(row["local_result_sha256"]),
            str(row["error_instance_id"]),
        )
    )

    value: dict[str, object] = {
        "schema_id": GROUP_ACCESS_SCHEMA_ID,
        "schema_version": 1,
        "round_id": round_id,
        "scientific_unit_type": "GROUP",
        "group_id": group_id,
        "group_manifest_sha256": group_manifest_sha256,
        "access_class": "TRAIN_UPDATE_ANALYZER_GROUP_VISIBLE",
        "dataset_split": "train",
        "source_pool": "TRAIN_UPDATE",
        "source_campaign_sha256": next(iter(campaign_values)),
        "evidence_cutoff_sha256": next(iter(cutoff_values)),
        "member_count": len(member_rows),
        "source_unit_count": len(source_rows),
        "unique_task_count": len(task_ids),
        "source_access_rows": source_rows,
        "group_member_source_bindings": member_rows,
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
        GROUP_ACCESS_SCHEMA_ID,
        value,
        excluded_field="group_task_access_sha256",
    )
    validate_task_access(value, live_call=True)
    return value


def build_group_universe(
    *,
    round_id: str,
    group_manifest_sha256s: Sequence[str],
) -> dict[str, object]:
    _text("round_id", round_id)
    values = sorted(
        {
            _sha("group_manifest_sha256", value)
            for value in group_manifest_sha256s
        }
    )
    if not values:
        raise ValueError("group universe must be non-empty")
    if len(values) != len(group_manifest_sha256s):
        raise ValueError("group universe contains duplicate group manifests")

    result: dict[str, object] = {
        "schema_id": GROUP_UNIVERSE_SCHEMA_ID,
        "schema_version": 1,
        "round_id": round_id,
        "group_count": len(values),
        "group_manifest_sha256s": values,
        "group_universe_sha256": "0" * 64,
    }
    result["group_universe_sha256"] = domain_hash(
        GROUP_UNIVERSE_SCHEMA_ID,
        result,
        excluded_field="group_universe_sha256",
    )
    return result


def build_round_group_analyzer_resource_authority(
    *,
    round_id: str,
    policy_version: str,
    producer_role: str,
    source_authority_sha256: str,
    group_universe: Mapping[str, object],
    group_stage_rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    _text("round_id", round_id)
    _text("policy_version", policy_version)
    if producer_role not in ALLOWED_RESOURCE_PRODUCERS:
        raise ValueError("unsupported group resource producer")
    _sha("source_authority_sha256", source_authority_sha256)

    if group_universe.get("schema_id") != GROUP_UNIVERSE_SCHEMA_ID:
        raise ValueError("group universe schema mismatch")
    observed_universe_sha = domain_hash(
        GROUP_UNIVERSE_SCHEMA_ID,
        group_universe,
        excluded_field="group_universe_sha256",
    )
    if group_universe.get("group_universe_sha256") != observed_universe_sha:
        raise ValueError("group universe hash mismatch")
    group_count = _positive_int(
        "group_count",
        group_universe.get("group_count"),
    )

    stage_rows: list[dict[str, object]] = []
    observed: dict[str, tuple[str, bool]] = {}
    per_group = 0

    for raw in group_stage_rows:
        stage_id = _text("stage_id", raw.get("stage_id"))
        if stage_id in observed:
            raise ValueError("duplicate group stage")
        if raw.get("role") != "ANALYZER":
            raise ValueError("group resource stage is not Analyzer")
        if raw.get("scientific_unit_type") != "GROUP":
            raise ValueError("group resource stage unit type mismatch")
        condition_id = _text(
            "condition_id",
            raw.get("condition_id"),
        )
        memory_exposure = raw.get("memory_exposure")
        if type(memory_exposure) is not bool:
            raise ValueError("group stage memory_exposure invalid")
        calls = _positive_int(
            "logical_call_budget_per_unit",
            raw.get("logical_call_budget_per_unit"),
        )
        observed[stage_id] = (condition_id, memory_exposure)
        per_group += calls
        stage_rows.append(
            {
                "stage_id": stage_id,
                "condition_id": condition_id,
                "memory_exposure": memory_exposure,
                "logical_call_budget_per_unit": calls,
            }
        )

    if observed != _REQUIRED_GROUP_STAGE_CONTRACT:
        raise ValueError(
            "group stage contract must be exactly G-A2/A2 OFF "
            "and G-A3/A3 ON"
        )
    stage_rows.sort(key=lambda row: str(row["stage_id"]))

    required = group_count * per_group

    value: dict[str, object] = {
        "schema_id": GROUP_RESOURCE_AUTHORITY_SCHEMA_ID,
        "schema_version": 1,
        "round_id": round_id,
        "policy_version": policy_version,
        "producer_role": producer_role,
        "source_authority_sha256": source_authority_sha256,
        "budget_unit": "LOGICAL_ANALYZER_CALL",
        "budget_decision_authority": (
            "REFERENCE_EXPERIMENT_CONTRACT_OR_RESEARCH_PLANNER"
        ),
        "budget_policy_id": (
            "COMPLETE_DETERMINISTIC_GROUP_UNIVERSE_V1"
        ),
        "group_universe_sha256": group_universe[
            "group_universe_sha256"
        ],
        "group_count": group_count,
        "stage_rows": stage_rows,
        "per_group_logical_calls": per_group,
        "required_group_logical_calls": required,
        "group_logical_call_cap": required,
        "complete_group_universe_required": True,
        "group_sampling_allowed": False,
        "manual_group_count_input_allowed": False,
        "manual_group_subset_input_allowed": False,
        "analyzer_self_budgeting_allowed": False,
        "analyzer_self_denominator_selection_allowed": False,
        "human_group_subset_selection_allowed": False,
        "live_group_execution_authorized": False,
        "resource_authority_sha256": "0" * 64,
    }
    value["resource_authority_sha256"] = domain_hash(
        GROUP_RESOURCE_AUTHORITY_SCHEMA_ID,
        value,
        excluded_field="resource_authority_sha256",
    )
    return value


def validate_round_group_analyzer_resource_authority(
    value: Mapping[str, object],
) -> None:
    if value.get("schema_id") != GROUP_RESOURCE_AUTHORITY_SCHEMA_ID:
        raise ValueError("group resource authority schema mismatch")
    observed = domain_hash(
        GROUP_RESOURCE_AUTHORITY_SCHEMA_ID,
        value,
        excluded_field="resource_authority_sha256",
    )
    if value.get("resource_authority_sha256") != observed:
        raise ValueError("group resource authority hash mismatch")
    if value.get("schema_version") != 1:
        raise ValueError("group resource authority schema version mismatch")
    _text("round_id", value.get("round_id"))
    _text("policy_version", value.get("policy_version"))
    if value.get("producer_role") not in ALLOWED_RESOURCE_PRODUCERS:
        raise ValueError("invalid group resource producer")
    _sha(
        "source_authority_sha256",
        value.get("source_authority_sha256"),
    )
    _sha(
        "group_universe_sha256",
        value.get("group_universe_sha256"),
    )
    if value.get("budget_unit") != "LOGICAL_ANALYZER_CALL":
        raise ValueError("group resource budget unit mismatch")
    if value.get("budget_decision_authority") != (
        "REFERENCE_EXPERIMENT_CONTRACT_OR_RESEARCH_PLANNER"
    ):
        raise ValueError("group resource decision authority mismatch")

    stage_rows = value.get("stage_rows")
    if not isinstance(stage_rows, list):
        raise ValueError("group resource stage_rows must be array")
    observed_contract: dict[str, tuple[str, bool]] = {}
    observed_per_group = 0
    for row in stage_rows:
        if not isinstance(row, Mapping):
            raise ValueError("group resource stage row must be object")
        stage_id = _text("stage_id", row.get("stage_id"))
        if stage_id in observed_contract:
            raise ValueError("duplicate group resource stage")
        condition_id = _text(
            "condition_id",
            row.get("condition_id"),
        )
        memory_exposure = row.get("memory_exposure")
        if type(memory_exposure) is not bool:
            raise ValueError("group resource memory_exposure invalid")
        observed_contract[stage_id] = (
            condition_id,
            memory_exposure,
        )
        observed_per_group += _positive_int(
            "logical_call_budget_per_unit",
            row.get("logical_call_budget_per_unit"),
        )
    if observed_contract != _REQUIRED_GROUP_STAGE_CONTRACT:
        raise ValueError(
            "group resource stage contract must remain "
            "G-A2/A2 OFF and G-A3/A3 ON"
        )
    if value.get("budget_policy_id") != (
        "COMPLETE_DETERMINISTIC_GROUP_UNIVERSE_V1"
    ):
        raise ValueError("group resource budget policy mismatch")
    if value.get("complete_group_universe_required") is not True:
        raise ValueError("complete group universe is not required")
    if value.get("group_sampling_allowed") is not False:
        raise ValueError("group sampling must remain disabled")
    if value.get("manual_group_count_input_allowed") is not False:
        raise ValueError("manual group count is forbidden")
    if value.get("manual_group_subset_input_allowed") is not False:
        raise ValueError("manual group subset is forbidden")
    if value.get("analyzer_self_budgeting_allowed") is not False:
        raise ValueError("Analyzer self-budgeting is forbidden")
    if value.get("analyzer_self_denominator_selection_allowed") is not False:
        raise ValueError("Analyzer denominator selection is forbidden")
    if value.get("human_group_subset_selection_allowed") is not False:
        raise ValueError("Human group subset selection is forbidden")
    if value.get("live_group_execution_authorized") is not False:
        raise ValueError(
            "Stage 3J authority must not authorize live execution"
        )

    group_count = _positive_int("group_count", value.get("group_count"))
    per_group = _positive_int(
        "per_group_logical_calls",
        value.get("per_group_logical_calls"),
    )
    if per_group != observed_per_group:
        raise ValueError(
            "per-group logical-call cost differs from stage rows"
        )
    required = _positive_int(
        "required_group_logical_calls",
        value.get("required_group_logical_calls"),
    )
    cap = _positive_int(
        "group_logical_call_cap",
        value.get("group_logical_call_cap"),
    )
    if required != group_count * per_group:
        raise ValueError("derived group logical-call requirement mismatch")
    if cap != required:
        raise ValueError("reference group budget must fund complete universe")
