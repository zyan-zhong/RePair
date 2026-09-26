from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from pchsi.research_intelligence.final_two_slot_resolution import (
    POLICY_SLOT,
    TASK_SET_SLOT,
    resolve_policy_config_slot_v1,
    resolve_task_set_slot_v1,
    stitch_final_hydration_manifest_v1,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _slot(
    slot_id: str,
    target: str,
    *,
    status: str,
    readable_view: object | None = None,
) -> dict[str, object]:
    lane, field = slot_id.split(".", 1)
    return {
        "slot_id": slot_id,
        "lane": lane,
        "field": field,
        "reference_sha256": target,
        "status": status,
        "required_readable": True,
        "identity_only_allowed": False,
        "selected_match": (
            None
            if status != "RESOLVED_READABLE"
            else {
                "source_path": "/frozen/leaf.json",
                "source_file_sha256": _sha(slot_id),
                "match_type": "IDENTITY_FIELD",
                "score": 9000,
                "json_path": "$",
                "schema_id": "FROZEN_LEAF_V1",
                "identity_fields": [field],
                "object_sha256": _sha("object:" + slot_id),
            }
        ),
        "all_matches": [],
        "readable_view": readable_view,
    }


def _base_manifest(
    *,
    policy_target: str,
    task_target: str,
) -> dict[str, object]:
    lineage_target = _sha("lineage")
    rollout_target = _sha("rollout")
    slots = [
        _slot(
            "policy_scorecard.policy_lineage_sha256",
            lineage_target,
            status="RESOLVED_READABLE",
            readable_view={
                "projection_kind": "FULL_JSON_OBJECT",
                "content": {
                    "schema_id": "FORMAL_PI1_POLICY_LINEAGE_BINDING_V1",
                    "policy_lineage_sha256": lineage_target,
                    "policy_condition_manifest_sha256": policy_target,
                    "policy_version": "P4-R1-Q2-BAD-TRAIN17",
                },
            },
        ),
        _slot(
            POLICY_SLOT,
            policy_target,
            status="QUERY_REQUIRED_MISSING",
        ),
        _slot(
            TASK_SET_SLOT,
            task_target,
            status="QUERY_REQUIRED_MISSING",
        ),
        _slot(
            "policy_scorecard.rollout_census_sha256",
            rollout_target,
            status="RESOLVED_READABLE",
            readable_view={
                "projection_kind": "FULL_JSON_OBJECT",
                "content": {
                    "schema_id": "FORMAL_PI1_ROLLOUT_CENSUS_V1",
                    "rollout_census_sha256": rollout_target,
                    "source_state_count": 30,
                },
            },
        ),
    ]
    lane_views = {
        "policy_scorecard": {
            row["field"]: {
                "reference_sha256": row["reference_sha256"],
                "status": row["status"],
                "readable_view": row["readable_view"],
            }
            for row in slots
        }
    }
    value = {
        "schema_id": "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1",
        "schema_version": 1,
        "source_blind_input_v1_sha256": _sha("blind-v1"),
        "slot_count": len(slots),
        "required_bound_slot_count": len(slots),
        "resolved_required_slot_count": 2,
        "unresolved_required_slot_ids": [
            POLICY_SLOT,
            TASK_SET_SLOT,
        ],
        "hydration_ready": False,
        "slots": slots,
        "lane_views": lane_views,
        "scan_roots": [],
        "scan_statistics": {},
        "future_outcomes_visible": False,
        "human_decision_visible": False,
        "benchmark_per_task_results_visible": False,
        "success_trajectory_optimization_active": False,
        "hydration_manifest_sha256": _sha("old-manifest"),
    }
    return value


def test_policy_config_resolves_only_as_lineage_bound_policy_condition_manifest(
    tmp_path: Path,
) -> None:
    target = _sha("policy-condition-manifest")
    base = _base_manifest(
        policy_target=target,
        task_target=_sha("task-set"),
    )
    manifest = {
        "schema_id": "P4_POLICY_CONDITION_MANIFEST_V1",
        "policy_condition_manifest_sha256": target,
        "policy_condition_id": "P4-R1-Q2-BAD-TRAIN17",
        "training_seed": 17,
        "policy_runtime_manifest_sha256": _sha("runtime"),
    }
    _write_json(
        tmp_path / "POLICY_CONDITION_MANIFEST_V1.json",
        manifest,
    )

    result = resolve_policy_config_slot_v1(
        hydration_manifest=base,
        roots=[tmp_path],
    )

    assert result["status"] == "RESOLVED_READABLE"
    slot = result["slot"]
    assert slot["selected_match"]["schema_id"] == (
        "P4_POLICY_CONDITION_MANIFEST_V1"
    )
    assert slot["readable_view"]["alias_metadata"][
        "resolved_semantics"
    ] == "policy_condition_manifest"


def test_policy_config_alias_rejects_lineage_target_mismatch(
    tmp_path: Path,
) -> None:
    target = _sha("policy-condition-manifest")
    base = _base_manifest(
        policy_target=target,
        task_target=_sha("task-set"),
    )
    base["lane_views"]["policy_scorecard"][
        "policy_lineage_sha256"
    ]["readable_view"]["content"][
        "policy_condition_manifest_sha256"
    ] = _sha("different")

    with pytest.raises(ValueError, match="not the sealed"):
        resolve_policy_config_slot_v1(
            hydration_manifest=base,
            roots=[tmp_path],
        )


def test_attempt_records_do_not_substitute_for_policy_condition_manifest(
    tmp_path: Path,
) -> None:
    target = _sha("policy-condition-manifest")
    base = _base_manifest(
        policy_target=target,
        task_target=_sha("task-set"),
    )
    _write_json(
        tmp_path / "attempt.json",
        {
            "schema_id": "E1_EPISODE_ARTIFACT_V1",
            "policy_condition_manifest_sha256": target,
            "policy_condition_id": "P4-R1-Q2-BAD-TRAIN17",
            "scientific_outcome_status": "FAILURE",
        },
    )

    result = resolve_policy_config_slot_v1(
        hydration_manifest=base,
        roots=[tmp_path],
    )
    assert result["status"] == "QUERY_REQUIRED_MISSING"
    assert result["candidate_occurrence_count"] == 1


def test_task_access_and_scientific_unit_identity_never_substitute_task_set(
    tmp_path: Path,
) -> None:
    target = _sha("task-set")
    base = _base_manifest(
        policy_target=_sha("policy"),
        task_target=target,
    )
    _write_json(
        tmp_path / "SCIENTIFIC_UNIT_IDENTITY_V1.json",
        {
            "schema_id": "SCIENTIFIC_UNIT_IDENTITY_V1",
            "task_set_manifest_sha256": target,
            "scientific_unit_id": "group-1",
        },
    )
    _write_json(
        tmp_path / "TASK_ACCESS_MANIFEST_V1.json",
        {
            "schema_id": "TASK_ACCESS_MANIFEST_V1",
            "task_set_manifest_sha256": target,
            "task_access_manifest_sha256": _sha("task-access"),
        },
    )

    result = resolve_task_set_slot_v1(
        hydration_manifest=base,
        roots=[tmp_path],
    )
    assert result["status"] == "QUERY_REQUIRED_MISSING"
    assert result["reference_occurrence_count"] == 2


def test_exact_task_set_file_sha_is_authoritative(
    tmp_path: Path,
) -> None:
    task_set = {
        "schema_id": "ALFWORLD_TASK_SET_MANIFEST_V1",
        "split": "valid_unseen",
        "task_count": 134,
        "task_ids": ["t0", "t1"],
    }
    path = tmp_path / "registered_task_set.json"
    target = _write_json(path, task_set)
    base = _base_manifest(
        policy_target=_sha("policy"),
        task_target=target,
    )

    result = resolve_task_set_slot_v1(
        hydration_manifest=base,
        roots=[tmp_path],
    )
    assert result["status"] == "RESOLVED_READABLE"
    assert result["slot"]["selected_match"][
        "resolution_mode"
    ] == "TASK_SET_EXACT_FILE_SHA256"
    assert result["slot"]["readable_view"]["artifact_view"][
        "content"
    ]["task_count"] == 134


def test_registered_task_set_manifest_identity_is_authoritative(
    tmp_path: Path,
) -> None:
    target = _sha("task-set")
    base = _base_manifest(
        policy_target=_sha("policy"),
        task_target=target,
    )
    _write_json(
        tmp_path / "FORMAL_PI1_TASK_SET_MANIFEST_V1.json",
        {
            "schema_id": "FORMAL_PI1_TASK_SET_MANIFEST_V1",
            "task_set_manifest_sha256": target,
            "split": "valid_unseen",
            "task_count": 134,
        },
    )

    result = resolve_task_set_slot_v1(
        hydration_manifest=base,
        roots=[tmp_path],
    )
    assert result["status"] == "RESOLVED_READABLE"


def test_stitch_changes_only_final_two_slots_and_becomes_ready(
    tmp_path: Path,
) -> None:
    policy_target = _sha("policy")
    task_target = _sha("task")
    base = _base_manifest(
        policy_target=policy_target,
        task_target=task_target,
    )
    rollout_before = copy.deepcopy(
        next(
            row
            for row in base["slots"]
            if row["slot_id"]
            == "policy_scorecard.rollout_census_sha256"
        )
    )

    policy_slot = copy.deepcopy(
        next(row for row in base["slots"] if row["slot_id"] == POLICY_SLOT)
    )
    policy_slot.update(
        status="RESOLVED_READABLE",
        selected_match={"schema_id": "P4_POLICY_CONDITION_MANIFEST_V1"},
        readable_view={"projection_kind": "BOUND_SEMANTIC_RESOLUTION_V1"},
    )
    task_slot = copy.deepcopy(
        next(row for row in base["slots"] if row["slot_id"] == TASK_SET_SLOT)
    )
    task_slot.update(
        status="RESOLVED_READABLE",
        selected_match={"schema_id": "FORMAL_PI1_TASK_SET_MANIFEST_V1"},
        readable_view={"projection_kind": "BOUND_SEMANTIC_RESOLUTION_V1"},
    )

    stitched = stitch_final_hydration_manifest_v1(
        base_manifest=base,
        policy_resolution={"status": "RESOLVED_READABLE", "slot": policy_slot},
        task_set_resolution={"status": "RESOLVED_READABLE", "slot": task_slot},
    )
    assert stitched["hydration_ready"] is True
    assert stitched["unresolved_required_slot_ids"] == []
    rollout_after = next(
        row
        for row in stitched["slots"]
        if row["slot_id"]
        == "policy_scorecard.rollout_census_sha256"
    )
    assert rollout_after == rollout_before


def test_stitch_stays_blocked_when_task_set_is_missing(
    tmp_path: Path,
) -> None:
    policy_target = _sha("policy")
    task_target = _sha("task")
    base = _base_manifest(
        policy_target=policy_target,
        task_target=task_target,
    )

    policy_slot = copy.deepcopy(
        next(row for row in base["slots"] if row["slot_id"] == POLICY_SLOT)
    )
    policy_slot.update(
        status="RESOLVED_READABLE",
        selected_match={"schema_id": "P4_POLICY_CONDITION_MANIFEST_V1"},
        readable_view={"projection_kind": "BOUND_SEMANTIC_RESOLUTION_V1"},
    )
    task_slot = copy.deepcopy(
        next(row for row in base["slots"] if row["slot_id"] == TASK_SET_SLOT)
    )

    stitched = stitch_final_hydration_manifest_v1(
        base_manifest=base,
        policy_resolution={"status": "RESOLVED_READABLE", "slot": policy_slot},
        task_set_resolution={"status": "QUERY_REQUIRED_MISSING", "slot": task_slot},
    )
    assert stitched["hydration_ready"] is False
    assert stitched["unresolved_required_slot_ids"] == [TASK_SET_SLOT]
