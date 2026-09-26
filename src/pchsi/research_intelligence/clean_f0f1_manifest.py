from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pchsi.reference_loop.canonical import domain_hash


FROZEN_PAIRED_SEEDS: tuple[int, ...] = (17, 31, 47, 73, 101)
STABLE_DIRECTION_MIN_PAIRS = 4
_EXECUTION_SCHEMA = "CLEAN_REFERENCE_F0F1_EXECUTION_MANIFEST_V1"
_BRANCH_SCHEMA = "CLEAN_REFERENCE_F0F1_BRANCH_BINDING_V1"


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{name} must be non-empty NUL-free str")
    return value


def _state_row(value: Mapping[str, object], position: int) -> dict[str, object]:
    required = {
        "source_state_sha256",
        "research_candidate_id",
        "source_candidate_sha256",
        "candidate_artifact_path",
        "candidate_artifact_file_sha256",
        "replay_source_path",
        "replay_source_file_sha256",
        "registered_repair_action",
    }
    if set(value) != required:
        raise ValueError("clean F0/F1 source-state row fields mismatch")
    row = dict(value)
    for name in (
        "source_state_sha256",
        "research_candidate_id",
        "source_candidate_sha256",
        "candidate_artifact_file_sha256",
        "replay_source_file_sha256",
    ):
        _sha(row[name], name)
    for name in (
        "candidate_artifact_path",
        "replay_source_path",
        "registered_repair_action",
    ):
        _text(row[name], name)
    for name in ("candidate_artifact_path", "replay_source_path"):
        if not Path(str(row[name])).is_absolute():
            raise ValueError(name + " must be absolute")
    row["state_position"] = position
    return row


def build_clean_f0f1_execution_manifest(
    *,
    round_id: str,
    implementation_commit: str,
    handoff_sha256: str,
    field_adjudication_file_sha256: str,
    runtime_binding_path: str,
    runtime_binding_file_sha256: str,
    active_snapshot_sha256: str,
    token_budget_contract_sha256: str,
    policy_model: str,
    policy_version: str,
    states: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    _text(round_id, "round_id")
    if not isinstance(implementation_commit, str) or len(implementation_commit) != 40:
        raise ValueError("implementation_commit must be 40-char git SHA")
    for name, value in (
        ("handoff_sha256", handoff_sha256),
        ("field_adjudication_file_sha256", field_adjudication_file_sha256),
        ("runtime_binding_file_sha256", runtime_binding_file_sha256),
        ("active_snapshot_sha256", active_snapshot_sha256),
        ("token_budget_contract_sha256", token_budget_contract_sha256),
    ):
        _sha(value, name)
    _text(runtime_binding_path, "runtime_binding_path")
    if not Path(runtime_binding_path).is_absolute():
        raise ValueError("runtime_binding_path must be absolute")
    _text(policy_model, "policy_model")
    _text(policy_version, "policy_version")

    source_rows = tuple(_state_row(row, index) for index, row in enumerate(states))
    if not source_rows:
        raise ValueError("at least one F0/F1 source state is required")
    if len({row["source_state_sha256"] for row in source_rows}) != len(source_rows):
        raise ValueError("duplicate F0/F1 source state")

    branches: list[dict[str, object]] = []
    for row in source_rows:
        for repetition, seed in enumerate(FROZEN_PAIRED_SEEDS, start=1):
            pair_payload = {
                "round_id": round_id,
                "source_state_sha256": row["source_state_sha256"],
                "source_candidate_sha256": row["source_candidate_sha256"],
                "repetition": repetition,
                "continuation_seed": seed,
            }
            pair_id = domain_hash("CLEAN_REFERENCE_F0F1_PAIR_ID_V1", pair_payload)
            for branch in ("F0", "F1"):
                branches.append(
                    {
                        "round_id": round_id,
                        "pair_id": pair_id,
                        "state_position": row["state_position"],
                        "repetition": repetition,
                        "branch": branch,
                        "continuation_seed": seed,
                        "source_state_sha256": row["source_state_sha256"],
                        "research_candidate_id": row["research_candidate_id"],
                        "source_candidate_sha256": row["source_candidate_sha256"],
                        "candidate_artifact_path": row["candidate_artifact_path"],
                        "candidate_artifact_file_sha256": row["candidate_artifact_file_sha256"],
                        "replay_source_path": row["replay_source_path"],
                        "replay_source_file_sha256": row["replay_source_file_sha256"],
                        "runtime_binding_path": runtime_binding_path,
                        "runtime_binding_file_sha256": runtime_binding_file_sha256,
                        "registered_repair_action": row["registered_repair_action"],
                        "active_snapshot_sha256": active_snapshot_sha256,
                        "token_budget_contract_sha256": token_budget_contract_sha256,
                        "policy_model": policy_model,
                        "policy_version": policy_version,
                    }
                )

    payload: dict[str, Any] = {
        "schema_id": _EXECUTION_SCHEMA,
        "schema_version": 1,
        "round_id": round_id,
        "implementation_commit": implementation_commit,
        "handoff_sha256": handoff_sha256,
        "field_adjudication_file_sha256": field_adjudication_file_sha256,
        "seed_schedule": list(FROZEN_PAIRED_SEEDS),
        "state_budget_mode": "FROZEN_REGISTERED_UNIVERSE",
        "max_selected_states": len(source_rows),
        "stable_direction_min_pairs": STABLE_DIRECTION_MIN_PAIRS,
        "outcome_adaptive_reselection_allowed": False,
        "state_count": len(source_rows),
        "pair_count": len(source_rows) * len(FROZEN_PAIRED_SEEDS),
        "branch_count": len(source_rows) * len(FROZEN_PAIRED_SEEDS) * 2,
        "policy_model": policy_model,
        "policy_version": policy_version,
        "branches": branches,
        "scientific_execution_authorized": False,
        "execution_manifest_sha256": "0" * 64,
    }
    payload["execution_manifest_sha256"] = domain_hash(
        _EXECUTION_SCHEMA,
        payload,
        excluded_field="execution_manifest_sha256",
    )
    return payload


def build_clean_f0f1_branch_bindings(manifest: Mapping[str, object]) -> tuple[dict[str, Any], ...]:
    if manifest.get("schema_id") != _EXECUTION_SCHEMA or manifest.get("schema_version") != 1:
        raise ValueError("clean F0/F1 execution manifest schema mismatch")
    observed_manifest_sha = domain_hash(
        _EXECUTION_SCHEMA,
        dict(manifest),
        excluded_field="execution_manifest_sha256",
    )
    if manifest.get("execution_manifest_sha256") != observed_manifest_sha:
        raise ValueError("clean F0/F1 execution manifest SHA mismatch")
    branches = manifest.get("branches")
    if not isinstance(branches, list) or len(branches) != manifest.get("branch_count"):
        raise ValueError("clean F0/F1 branch population mismatch")
    output: list[dict[str, Any]] = []
    for row in branches:
        if not isinstance(row, Mapping):
            raise ValueError("clean F0/F1 branch row must be object")
        binding: dict[str, Any] = {
            "schema_id": _BRANCH_SCHEMA,
            "schema_version": 1,
            "execution_manifest_sha256": observed_manifest_sha,
            "handoff_sha256": manifest["handoff_sha256"],
            "field_adjudication_file_sha256": manifest["field_adjudication_file_sha256"],
            "implementation_commit": manifest["implementation_commit"],
            **dict(row),
            "branch_binding_sha256": "0" * 64,
        }
        binding["branch_binding_sha256"] = domain_hash(
            _BRANCH_SCHEMA,
            binding,
            excluded_field="branch_binding_sha256",
        )
        output.append(binding)
    return tuple(output)
# Planner-bound extension over the existing V1 manifest and branch-binding
# machinery. It does not introduce a second F0/F1 runner.
def build_research_planner_f0f1_handoff_v2(
    *,
    verification_plan: Mapping[str, object],
    states: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    from pchsi.research_intelligence.research_planner_reference_trace import (
        validate_research_planner_verification_plan_v2,
    )

    plan = validate_research_planner_verification_plan_v2(verification_plan)
    source_rows = tuple(_state_row(row, index) for index, row in enumerate(states))
    state_ids = [str(row["source_state_sha256"]) for row in source_rows]
    candidate_ids = [str(row["source_candidate_sha256"]) for row in source_rows]
    if set(state_ids) != set(plan["selected_source_state_ids"]):
        raise ValueError("handoff state universe differs from Planner selection")
    if set(candidate_ids) != set(plan["selected_candidate_ids"]):
        raise ValueError("handoff candidate universe differs from Planner selection")
    if len(source_rows) != plan["registered_state_budget"]:
        raise ValueError("handoff state count differs from Planner budget")
    value: dict[str, Any] = {
        "schema_id": "RESEARCH_PLANNER_F0F1_HANDOFF_V2",
        "schema_version": 2,
        "round_id": plan["round_id"],
        "parent_policy_id": plan["parent_policy_id"],
        "verification_plan_sha256": plan["verification_plan_sha256"],
        "selected_state_count": len(source_rows),
        "selected_source_state_ids": state_ids,
        "selected_candidate_ids": candidate_ids,
        "selected_state_rows": [
            {
                "source_state_sha256": row["source_state_sha256"],
                "research_candidate_id": row["research_candidate_id"],
                "source_candidate_sha256": row["source_candidate_sha256"],
                "registered_repair_action": row["registered_repair_action"],
            }
            for row in source_rows
        ],
        "paired_seeds": list(plan["paired_seeds"]),
        "paired_repetitions_per_state": plan[
            "paired_repetitions_per_state"
        ],
        "branch_arms_per_repetition": 2,
        "paired_experiment_count": plan["paired_experiment_count"],
        "total_branch_run_budget": plan["total_branch_run_budget"],
        "reuse_existing_runner": True,
        "new_branch_runner_allowed": False,
        "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
        "outcome_adaptive_reselection_allowed": False,
        "handoff_sha256": "0" * 64,
    }
    value["handoff_sha256"] = domain_hash(
        "RESEARCH_PLANNER_F0F1_HANDOFF_V2",
        value,
        excluded_field="handoff_sha256",
    )
    return value


def build_planner_bound_clean_f0f1_execution_manifest(
    *,
    verification_plan: Mapping[str, object],
    handoff: Mapping[str, object],
    round_id: str,
    implementation_commit: str,
    field_adjudication_file_sha256: str,
    runtime_binding_path: str,
    runtime_binding_file_sha256: str,
    active_snapshot_sha256: str,
    token_budget_contract_sha256: str,
    policy_model: str,
    policy_version: str,
    states: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    from pchsi.research_intelligence.research_planner_reference_trace import (
        validate_research_planner_verification_plan_v2,
    )

    plan = validate_research_planner_verification_plan_v2(verification_plan)
    if handoff.get("schema_id") != "RESEARCH_PLANNER_F0F1_HANDOFF_V2":
        raise ValueError("Planner F0/F1 handoff schema mismatch")
    observed_handoff_sha = domain_hash(
        "RESEARCH_PLANNER_F0F1_HANDOFF_V2",
        dict(handoff),
        excluded_field="handoff_sha256",
    )
    if handoff.get("handoff_sha256") != observed_handoff_sha:
        raise ValueError("Planner F0/F1 handoff SHA mismatch")
    if handoff.get("verification_plan_sha256") != plan[
        "verification_plan_sha256"
    ]:
        raise ValueError("handoff does not bind the Planner verification plan")
    if plan["round_id"] != round_id or plan["parent_policy_id"] != policy_version:
        raise ValueError("Planner plan round/policy differs from execution")

    source_rows = tuple(_state_row(row, index) for index, row in enumerate(states))
    state_ids = [str(row["source_state_sha256"]) for row in source_rows]
    candidate_ids = [str(row["source_candidate_sha256"]) for row in source_rows]
    if set(state_ids) != set(plan["selected_source_state_ids"]):
        raise ValueError("execution states differ from Planner-selected universe")
    if set(candidate_ids) != set(plan["selected_candidate_ids"]):
        raise ValueError("execution candidates differ from Planner-selected universe")

    manifest = build_clean_f0f1_execution_manifest(
        round_id=round_id,
        implementation_commit=implementation_commit,
        handoff_sha256=str(handoff["handoff_sha256"]),
        field_adjudication_file_sha256=field_adjudication_file_sha256,
        runtime_binding_path=runtime_binding_path,
        runtime_binding_file_sha256=runtime_binding_file_sha256,
        active_snapshot_sha256=active_snapshot_sha256,
        token_budget_contract_sha256=token_budget_contract_sha256,
        policy_model=policy_model,
        policy_version=policy_version,
        states=states,
    )
    manifest["verification_plan_sha256"] = plan[
        "verification_plan_sha256"
    ]
    manifest["state_budget_authority"] = (
        "RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE"
    )
    manifest["planner_selected_state_count"] = plan[
        "registered_state_budget"
    ]
    manifest["legacy_fixed_12_state_authority_used"] = False
    manifest["state_budget_consistency_verified"] = True
    manifest["execution_manifest_sha256"] = domain_hash(
        _EXECUTION_SCHEMA,
        manifest,
        excluded_field="execution_manifest_sha256",
    )
    return manifest
