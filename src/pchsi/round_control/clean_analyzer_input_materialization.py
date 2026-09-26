"""Round-adaptive clean Analyzer input materialization contracts.

This module is a thin binding layer. It does not change Analyzer prompts,
output schemas, grouping, Memory, F0/F1, Research Planner, or training logic.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pchsi.reference_loop.canonical import domain_hash


RESOURCE_BUDGET_SCHEMA_ID = "ROUND_ANALYZER_RESOURCE_BUDGET_V1"
LOCAL_U_REG_SCHEMA_ID = "CLEAN_ANALYZER_LOCAL_U_REG_V1"
TASK_ACCESS_SCHEMA_ID = "CLEAN_ANALYZER_TASK_ACCESS_RECORD_V1"
ACTOR_INPUT_BINDING_SCHEMA_ID = "CLEAN_ANALYZER_ACTOR_INPUT_BINDING_V1"
SELECTION_POLICY_ID = (
    "FAILURE_ONLY_TASK_FAMILY_ROUND_ROBIN_WITHIN_FAMILY_HASH_V1"
)
ALLOWED_BUDGET_PRODUCERS = frozenset(
    {
        "REFERENCE_EXPERIMENT_CONTRACT",
        "HUMAN_RESEARCH_PLANNER",
        "STRONG_RESEARCH_PLANNER",
        "LOCAL_RESEARCH_PLANNER",
    }
)
REQUIRED_LOCAL_STAGE_CONTRACT = {"L-A0": "A0", "L-A1": "A1"}


def _nonempty_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or any(ch in value for ch in "\x00\r\n"):
        raise ValueError(f"{name} must be non-empty single-line text")
    return value


def _sha256(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _positive_int(name: str, value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _validate_hash(
    *,
    value: Mapping[str, object],
    schema_id: str,
    domain: str,
    hash_field: str,
) -> None:
    if value.get("schema_id") != schema_id:
        raise ValueError(f"{schema_id} schema mismatch")
    observed = domain_hash(domain, value, excluded_field=hash_field)
    if value.get(hash_field) != observed:
        raise ValueError(f"{schema_id} hash mismatch")


def build_round_analyzer_resource_budget(
    *,
    round_id: str,
    policy_version: str,
    producer_role: str,
    source_authority_sha256: str,
    local_stage_rows: Sequence[Mapping[str, object]],
    local_logical_call_cap: int,
) -> dict[str, object]:
    """Build one role-neutral round resource budget.

    The materializer never accepts a manually supplied source-state count.
    The maximum state count is derived from a round-level logical-call cap and
    the frozen per-state local-stage cost.
    """
    _nonempty_text("round_id", round_id)
    _nonempty_text("policy_version", policy_version)
    if producer_role not in ALLOWED_BUDGET_PRODUCERS:
        raise ValueError("unsupported budget producer role")
    _sha256("source_authority_sha256", source_authority_sha256)
    _positive_int("local_logical_call_cap", local_logical_call_cap)

    rows: list[dict[str, object]] = []
    observed_stage_ids: set[str] = set()
    per_state_logical_calls = 0
    for raw in local_stage_rows:
        stage_id = _nonempty_text("stage_id", raw.get("stage_id"))
        if stage_id in observed_stage_ids:
            raise ValueError("duplicate local stage")
        observed_stage_ids.add(stage_id)
        if raw.get("role") != "ANALYZER":
            raise ValueError("local budget contains non-Analyzer stage")
        if raw.get("scientific_unit_type") != "EPISODE":
            raise ValueError("local stage must use EPISODE units")
        if raw.get("memory_exposure") is not False:
            raise ValueError("local A0/A1 materialization must remain Memory OFF")
        calls = _positive_int(
            "logical_call_budget_per_unit",
            raw.get("logical_call_budget_per_unit"),
        )
        per_state_logical_calls += calls
        rows.append(
            {
                "stage_id": stage_id,
                "condition_id": _nonempty_text(
                    "condition_id", raw.get("condition_id")
                ),
                "logical_call_budget_per_unit": calls,
            }
        )

    rows.sort(key=lambda row: str(row["stage_id"]))
    if {str(row["stage_id"]): str(row["condition_id"]) for row in rows} != (
        REQUIRED_LOCAL_STAGE_CONTRACT
    ):
        raise ValueError("local stage contract must be exactly L-A0/A0 and L-A1/A1")
    maximum_source_state_count = local_logical_call_cap // per_state_logical_calls
    if maximum_source_state_count <= 0:
        raise ValueError("logical-call cap cannot fund one complete source state")

    value: dict[str, object] = {
        "schema_id": RESOURCE_BUDGET_SCHEMA_ID,
        "schema_version": 1,
        "round_id": round_id,
        "policy_version": policy_version,
        "producer_role": producer_role,
        "source_authority_sha256": source_authority_sha256,
        "budget_unit": "LOGICAL_ANALYZER_CALL",
        "budget_decision_authority": "ROUND_CONTROL_OR_RESEARCH_PLANNER",
        "analyzer_self_budgeting_allowed": False,
        "analyzer_self_denominator_selection_allowed": False,
        "selection_is_deterministic_after_budget_freeze": True,
        "local_stage_rows": rows,
        "local_logical_call_cap": local_logical_call_cap,
        "per_source_state_logical_calls": per_state_logical_calls,
        "maximum_source_state_count": maximum_source_state_count,
        "unallocated_local_logical_call_count": (
            local_logical_call_cap % per_state_logical_calls
        ),
        "source_state_count_is_derived": True,
        "manual_source_state_count_input_allowed": False,
        "failure_success_ratio_input_allowed": False,
        "selection_policy_id": SELECTION_POLICY_ID,
        "future_round_producer_roles": [
            "HUMAN_RESEARCH_PLANNER",
            "STRONG_RESEARCH_PLANNER",
            "LOCAL_RESEARCH_PLANNER",
        ],
        "budget_sha256": "0" * 64,
    }
    value["budget_sha256"] = domain_hash(
        RESOURCE_BUDGET_SCHEMA_ID,
        value,
        excluded_field="budget_sha256",
    )
    return value


def validate_round_analyzer_resource_budget(
    value: Mapping[str, object],
) -> None:
    _validate_hash(
        value=value,
        schema_id=RESOURCE_BUDGET_SCHEMA_ID,
        domain=RESOURCE_BUDGET_SCHEMA_ID,
        hash_field="budget_sha256",
    )
    _nonempty_text("round_id", value.get("round_id"))
    _nonempty_text("policy_version", value.get("policy_version"))
    if value.get("producer_role") not in ALLOWED_BUDGET_PRODUCERS:
        raise ValueError("invalid budget producer")
    _sha256("source_authority_sha256", value.get("source_authority_sha256"))
    if value.get("budget_unit") != "LOGICAL_ANALYZER_CALL":
        raise ValueError("budget unit mismatch")
    if value.get("budget_decision_authority") != (
        "ROUND_CONTROL_OR_RESEARCH_PLANNER"
    ):
        raise ValueError("budget decision authority mismatch")
    if value.get("analyzer_self_budgeting_allowed") is not False:
        raise ValueError("Analyzer self-budgeting is forbidden")
    if value.get("analyzer_self_denominator_selection_allowed") is not False:
        raise ValueError("Analyzer self-denominator selection is forbidden")
    if value.get("selection_is_deterministic_after_budget_freeze") is not True:
        raise ValueError("selection must be deterministic after budget freeze")
    if value.get("source_state_count_is_derived") is not True:
        raise ValueError("source-state count must be derived")
    if value.get("manual_source_state_count_input_allowed") is not False:
        raise ValueError("manual source-state count is forbidden")
    if value.get("failure_success_ratio_input_allowed") is not False:
        raise ValueError("manual failure/success ratio is forbidden")
    if value.get("selection_policy_id") != SELECTION_POLICY_ID:
        raise ValueError("selection policy mismatch")
    if value.get("future_round_producer_roles") != [
        "HUMAN_RESEARCH_PLANNER",
        "STRONG_RESEARCH_PLANNER",
        "LOCAL_RESEARCH_PLANNER",
    ]:
        raise ValueError("future round producer roles mismatch")

    stage_rows = value.get("local_stage_rows")
    if not isinstance(stage_rows, list):
        raise ValueError("local_stage_rows must be an array")
    observed_contract: dict[str, str] = {}
    observed_per_state = 0
    for row in stage_rows:
        if not isinstance(row, Mapping):
            raise ValueError("local stage row must be object")
        stage_id = _nonempty_text("stage_id", row.get("stage_id"))
        condition_id = _nonempty_text("condition_id", row.get("condition_id"))
        if stage_id in observed_contract:
            raise ValueError("duplicate local stage")
        observed_contract[stage_id] = condition_id
        observed_per_state += _positive_int(
            "logical_call_budget_per_unit",
            row.get("logical_call_budget_per_unit"),
        )
    if observed_contract != REQUIRED_LOCAL_STAGE_CONTRACT:
        raise ValueError("local stage contract must be exactly L-A0/A0 and L-A1/A1")

    cap = _positive_int("local_logical_call_cap", value.get("local_logical_call_cap"))
    per_state = _positive_int(
        "per_source_state_logical_calls",
        value.get("per_source_state_logical_calls"),
    )
    if per_state != observed_per_state:
        raise ValueError("per-state logical-call cost differs from stage rows")
    maximum = _positive_int(
        "maximum_source_state_count",
        value.get("maximum_source_state_count"),
    )
    if maximum != cap // per_state:
        raise ValueError("derived source-state count mismatch")
    unallocated = value.get("unallocated_local_logical_call_count")
    if type(unallocated) is not int or unallocated < 0:
        raise ValueError("unallocated logical-call count must be non-negative integer")
    if unallocated != cap % per_state:
        raise ValueError("unallocated logical-call count mismatch")


def _failure_order_score(
    row: Mapping[str, object], *, source_campaign_sha256: str
) -> str:
    return domain_hash(
        "CLEAN_ANALYZER_FAILURE_SELECTION_ORDER_V1",
        {
            "source_campaign_sha256": source_campaign_sha256,
            "scientific_cell_id": row["scientific_cell_id"],
            "execution_attempt_id": row["execution_attempt_id"],
            "task_id": row["task_id"],
            "task_type": row["task_type"],
            "attempt_bundle_sha256": row["attempt_bundle_sha256"],
            "episode_semantic_sha256": row["episode_semantic_sha256"],
        },
    )


def select_failure_only_u_reg(
    *,
    failure_rows: Iterable[Mapping[str, object]],
    resource_budget: Mapping[str, object],
    source_campaign_sha256: str,
) -> list[dict[str, object]]:
    """Select a deterministic, family-covering failure-only local U_reg."""
    validate_round_analyzer_resource_budget(resource_budget)
    _sha256("source_campaign_sha256", source_campaign_sha256)
    maximum = int(resource_budget["maximum_source_state_count"])

    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    seen_cells: set[str] = set()
    seen_tasks: set[str] = set()
    for raw in failure_rows:
        if raw.get("classification") != "TASK_FAILURE":
            raise ValueError("formal local U_reg must be failure-only")
        if raw.get("source_campaign_sha256") != source_campaign_sha256:
            raise ValueError("failure row source campaign mismatch")
        if raw.get("policy_interface_profile_id") != "I1_EXECUTION_PROFILE_V1":
            raise ValueError("failure row is not I1")
        cell = _nonempty_text("scientific_cell_id", raw.get("scientific_cell_id"))
        task_id = _nonempty_text("task_id", raw.get("task_id"))
        family = _nonempty_text("task_type", raw.get("task_type"))
        if cell in seen_cells:
            raise ValueError("duplicate scientific cell")
        if task_id in seen_tasks:
            raise ValueError("duplicate task in failure universe")
        seen_cells.add(cell)
        seen_tasks.add(task_id)
        _sha256("attempt_bundle_sha256", raw.get("attempt_bundle_sha256"))
        _sha256("episode_semantic_sha256", raw.get("episode_semantic_sha256"))
        row = dict(raw)
        row["source_evidence_index_row_sha256"] = domain_hash(
            "PI0_I1_TRAIN_UPDATE_EVIDENCE_INDEX_ROW_V1",
            dict(raw),
        )
        row["selection_score"] = _failure_order_score(
            row,
            source_campaign_sha256=source_campaign_sha256,
        )
        by_family[family].append(row)

    if not by_family:
        raise ValueError("failure universe is empty")
    for family in by_family:
        by_family[family].sort(
            key=lambda row: (
                str(row["selection_score"]),
                str(row["scientific_cell_id"]),
            )
        )

    selected: list[dict[str, object]] = []
    family_offsets = {family: 0 for family in by_family}
    families = sorted(by_family)
    target = min(maximum, sum(len(rows) for rows in by_family.values()))
    cycle_index = 0
    while len(selected) < target:
        made_progress = False
        for family in families:
            offset = family_offsets[family]
            rows = by_family[family]
            if offset >= len(rows):
                continue
            chosen = dict(rows[offset])
            chosen["selection_rank"] = len(selected)
            chosen["family_cycle_index"] = cycle_index
            chosen["within_family_rank"] = offset
            selected.append(chosen)
            family_offsets[family] = offset + 1
            made_progress = True
            if len(selected) >= target:
                break
        if not made_progress:
            break
        cycle_index += 1

    if len(selected) != target:
        raise ValueError("deterministic selection did not fill the derived budget")
    return selected


def build_local_u_reg_manifest(
    *,
    round_id: str,
    policy_version: str,
    evidence_cutoff_sha256: str,
    failure_universe_file_sha256: str,
    source_campaign_sha256: str,
    resource_budget: Mapping[str, object],
    selected_units: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    validate_round_analyzer_resource_budget(resource_budget)
    for name, value in (
        ("evidence_cutoff_sha256", evidence_cutoff_sha256),
        ("failure_universe_file_sha256", failure_universe_file_sha256),
        ("source_campaign_sha256", source_campaign_sha256),
    ):
        _sha256(name, value)
    if not selected_units:
        raise ValueError("selected_units must be non-empty")

    family_counts: dict[str, int] = defaultdict(int)
    task_ids: set[str] = set()
    gamefile_shas: set[str] = set()
    rows: list[dict[str, object]] = []
    for raw in selected_units:
        family = _nonempty_text("task_type", raw.get("task_type"))
        task_id = _nonempty_text("task_id", raw.get("task_id"))
        gamefile_sha = _sha256("gamefile_sha256", raw.get("gamefile_sha256"))
        if task_id in task_ids or gamefile_sha in gamefile_shas:
            raise ValueError("local U_reg must have unique task and gamefile identities")
        task_ids.add(task_id)
        gamefile_shas.add(gamefile_sha)
        family_counts[family] += 1
        rows.append(
            {
                "selection_rank": int(raw["selection_rank"]),
                "family_cycle_index": int(raw["family_cycle_index"]),
                "within_family_rank": int(raw["within_family_rank"]),
                "selection_score": _sha256(
                    "selection_score", raw.get("selection_score")
                ),
                "source_evidence_index_row_sha256": _sha256(
                    "source_evidence_index_row_sha256",
                    raw.get("source_evidence_index_row_sha256"),
                ),
                "source_unit_id": _nonempty_text(
                    "source_unit_id", raw.get("source_unit_id")
                ),
                "scientific_cell_id": _nonempty_text(
                    "scientific_cell_id", raw.get("scientific_cell_id")
                ),
                "execution_attempt_id": _nonempty_text(
                    "execution_attempt_id", raw.get("execution_attempt_id")
                ),
                "task_id": task_id,
                "task_type": family,
                "gamefile_sha256": gamefile_sha,
                "attempt_bundle_sha256": _sha256(
                    "attempt_bundle_sha256", raw.get("attempt_bundle_sha256")
                ),
                "episode_semantic_sha256": _sha256(
                    "episode_semantic_sha256", raw.get("episode_semantic_sha256")
                ),
            }
        )
    rows.sort(key=lambda row: int(row["selection_rank"]))

    value: dict[str, object] = {
        "schema_id": LOCAL_U_REG_SCHEMA_ID,
        "schema_version": 1,
        "round_id": round_id,
        "policy_version": policy_version,
        "policy_interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "source_split": "ALFWORLD_TRAIN",
        "source_train_pool": "TRAIN_UPDATE",
        "source_campaign_sha256": source_campaign_sha256,
        "evidence_cutoff_sha256": evidence_cutoff_sha256,
        "failure_universe_file_sha256": failure_universe_file_sha256,
        "resource_budget_sha256": resource_budget["budget_sha256"],
        "selection_policy_id": SELECTION_POLICY_ID,
        "selected_source_state_count": len(rows),
        "selected_failure_count": len(rows),
        "selected_success_count": 0,
        "unique_task_count": len(task_ids),
        "unique_gamefile_count": len(gamefile_shas),
        "task_family_counts": dict(sorted(family_counts.items())),
        "human_selected_state_count": 0,
        "semantic_priority_score_used": False,
        "mechanical_outcome_sampling_scheduler_used": False,
        "failure_only": True,
        "selected_units": rows,
        "u_reg_sha256": "0" * 64,
    }
    value["u_reg_sha256"] = domain_hash(
        LOCAL_U_REG_SCHEMA_ID,
        value,
        excluded_field="u_reg_sha256",
    )
    return value


def build_clean_analyzer_task_access_record(
    *,
    round_id: str,
    source_unit_id: str,
    task_id: str,
    gamefile_sha256: str,
    source_campaign_sha256: str,
    evidence_cutoff_sha256: str,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_id": TASK_ACCESS_SCHEMA_ID,
        "schema_version": 1,
        "round_id": _nonempty_text("round_id", round_id),
        "source_unit_id": _nonempty_text("source_unit_id", source_unit_id),
        "task_id": _nonempty_text("task_id", task_id),
        "gamefile_sha256": _sha256("gamefile_sha256", gamefile_sha256),
        "access_class": "TRAIN_UPDATE_ANALYZER_VISIBLE",
        "dataset_split": "train",
        "source_pool": "TRAIN_UPDATE",
        "source_campaign_sha256": _sha256(
            "source_campaign_sha256", source_campaign_sha256
        ),
        "evidence_cutoff_sha256": _sha256(
            "evidence_cutoff_sha256", evidence_cutoff_sha256
        ),
        "teacher_call_permitted": True,
        "training_permitted": False,
        "select_evaluation_permitted": False,
        "confirmatory_permitted": False,
        "benchmark_result_values_visible": False,
        "policy_action_authority": False,
        "task_access_sha256": "0" * 64,
    }
    value["task_access_sha256"] = domain_hash(
        TASK_ACCESS_SCHEMA_ID,
        value,
        excluded_field="task_access_sha256",
    )
    return value


def build_actor_input_binding(
    *,
    round_id: str,
    runtime_registry_sha256: str,
    local_u_reg_sha256: str,
    human_primary_authorized: bool,
    strong_shadow_authorized: bool,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_id": ACTOR_INPUT_BINDING_SCHEMA_ID,
        "schema_version": 1,
        "round_id": _nonempty_text("round_id", round_id),
        "runtime_registry_sha256": _sha256(
            "runtime_registry_sha256", runtime_registry_sha256
        ),
        "local_u_reg_sha256": _sha256("local_u_reg_sha256", local_u_reg_sha256),
        "shared_input_registry_for_human_and_strong": True,
        "human_primary_authorized": bool(human_primary_authorized),
        "strong_shadow_authorized": bool(strong_shadow_authorized),
        "strong_shadow_human_content_visible": False,
        "strong_shadow_human_hash_visible": False,
        "local_shadow_currently_authorized": False,
        "local_shadow_future_compatible": True,
        "analyzer_prompt_or_schema_modified": False,
        "memory_exposure": False,
        "benefit_harm_authority": False,
        "training_label_authority": False,
        "binding_sha256": "0" * 64,
    }
    value["binding_sha256"] = domain_hash(
        ACTOR_INPUT_BINDING_SCHEMA_ID,
        value,
        excluded_field="binding_sha256",
    )
    return value
