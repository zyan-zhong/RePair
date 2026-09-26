from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pchsi.research_intelligence.strong_researcher_evidence_hydration import (
    build_hydration_manifest_v1,
    build_reference_trace_v3,
    build_strong_blind_pre_input_v2,
    validate_hydrated_blind_input_v2,
)


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


def _blind_input(
    refs: dict[str, str | None],
) -> dict[str, object]:
    value = {
        "schema_id": "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1",
        "schema_version": 1,
        "round_id": "round-k",
        "parent_policy_id": "pi1",
        "evidence_cutoff_sha256": "a" * 64,
        "round_evidence_package_sha256": "b" * 64,
        "policy_scorecard": {
            "policy_lineage_sha256": refs["policy_lineage_sha256"],
            "policy_checkpoint_sha256": refs["policy_checkpoint_sha256"],
            "policy_config_sha256": refs["policy_config_sha256"],
            "task_set_manifest_sha256": refs["task_set_manifest_sha256"],
            "rollout_census_sha256": refs["rollout_census_sha256"],
            "mechanical_failure_census_sha256": refs[
                "mechanical_failure_census_sha256"
            ],
        },
        "analyzer_evidence": {
            "formal_result_manifest_sha256": refs[
                "formal_result_manifest_sha256"
            ],
            "metric_report_sha256": refs["metric_report_sha256"],
            "repair_effect_authority": False,
        },
        "experiment_history": {
            "historical_f0f1_summary_sha256": refs[
                "historical_f0f1_summary_sha256"
            ],
            "historical_go_nogo_ledger_sha256": refs[
                "historical_go_nogo_ledger_sha256"
            ],
            "previous_researcher_decisions_sha256": refs[
                "previous_researcher_decisions_sha256"
            ],
            "training_history_sha256": refs[
                "training_history_sha256"
            ],
            "code_config_diff_manifest_sha256": refs[
                "code_config_diff_manifest_sha256"
            ],
        },
        "resource_and_cost": {
            "resource_budget_manifest_sha256": refs[
                "resource_budget_manifest_sha256"
            ],
            "budget_interpretation_status": "BOUND",
        },
        "researcher_memory_view": {
            "schema_id": "COMPACT_RESEARCHER_MEMORY_VIEW_V1",
            "train_side_record_count": 0,
            "train_side_records": [],
        },
        "verification_budget_plan": {
            "registered_state_budget": 12,
            "paired_repetitions_per_state": 5,
            "branch_arms_per_repetition": 2,
            "total_branch_run_budget": 120,
        },
        "registered_candidate_universe": {
            "candidate_count": 60,
            "source_state_count": 30,
            "condition_counts": {"A2": 30, "A3": 30},
            "pair_table": [],
        },
        "researcher_role_contract": {
            "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
        },
        "required_output_contract": {
            "selected_state_budget": 12,
        },
        "visibility_boundary": {
            "human_pre_visible": False,
            "human_pre_hash_visible": False,
            "human_selection_visible": False,
            "human_rationale_visible": False,
            "current_f0f1_outcomes_visible": False,
            "future_policy_evaluation_visible": False,
            "strong_model_benchmark_per_task_results_visible": False,
            "success_trajectory_optimization_active": False,
        },
        "blind_input_sha256": "0" * 64,
    }
    payload = dict(value)
    payload.pop("blind_input_sha256")
    value["blind_input_sha256"] = hashlib.sha256(
        (
            "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1"
            + "\0"
            + json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    return value


def _make_complete_fixture(tmp_path: Path):
    root = tmp_path / "evidence"
    refs: dict[str, str | None] = {
        "historical_f0f1_summary_sha256": None,
        "historical_go_nogo_ledger_sha256": None,
        "previous_researcher_decisions_sha256": None,
        "training_history_sha256": None,
    }

    artifacts = {
        "policy_lineage_sha256": {
            "schema_id": "POLICY_LINEAGE_V1",
            "policy_lineage": ["pi0", "pi1"],
            "status": "FROZEN",
        },
        "policy_config_sha256": {
            "schema_id": "POLICY_CONFIG_V1",
            "model": "qwen",
            "max_steps": 50,
        },
        "task_set_manifest_sha256": {
            "schema_id": "TASK_SET_MANIFEST_V1",
            "task_count": 134,
            "split": "valid_unseen",
        },
        "rollout_census_sha256": {
            "schema_id": "ROLLOUT_CENSUS_V1",
            "success_count": 10,
            "failure_count": 124,
            "task_family_counts": {"family-a": 20},
        },
        "mechanical_failure_census_sha256": {
            "schema_id": "MECHANICAL_FAILURE_CENSUS_V1",
            "failure_count": 124,
            "error_counts": {"loop": 17, "off_list": 3},
        },
        "formal_result_manifest_sha256": {
            "schema_id": "FORMAL_RESULT_MANIFEST_V1",
            "selected_candidate_count": 60,
            "source_state_count": 30,
        },
        "metric_report_sha256": {
            "schema_id": "ANALYZER_METRIC_REPORT_V1",
            "group_count": 30,
            "candidate_count": 60,
        },
        "code_config_diff_manifest_sha256": {
            "schema_id": "CODE_CONFIG_DIFF_MANIFEST_V1",
            "commit_count": 3,
            "changed_paths": ["a.py"],
        },
        "resource_budget_manifest_sha256": {
            "schema_id": "RESOURCE_BUDGET_MANIFEST_V1",
            "environment_branch_budget": 120,
            "api_call_budget": 1,
            "gpu_hours": 0.0,
        },
    }

    for field, value in artifacts.items():
        refs[field] = _write_json(
            root / (field + ".json"),
            value,
        )

    # Checkpoint is identity-only and need not exist as a readable file.
    refs["policy_checkpoint_sha256"] = "c" * 64

    blind = _blind_input(refs)
    return root, refs, blind


def test_complete_hydration_resolves_readable_lanes_and_preserves_null_history(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)

    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root],
    )

    assert manifest["hydration_ready"] is True
    assert manifest["unresolved_required_slot_ids"] == []
    slots = {
        row["slot_id"]: row for row in manifest["slots"]
    }
    assert slots[
        "policy_scorecard.rollout_census_sha256"
    ]["status"] == "RESOLVED_READABLE"
    assert slots[
        "experiment_history.historical_f0f1_summary_sha256"
    ]["status"] == "ABSENT_NOT_BOUND"
    assert slots[
        "policy_scorecard.policy_checkpoint_sha256"
    ]["status"] == "IDENTITY_ONLY"

    rollout = manifest["lane_views"]["policy_scorecard"][
        "rollout_census_sha256"
    ]["readable_view"]["content"]
    assert rollout["success_count"] == 10
    assert rollout["failure_count"] == 124


def test_duplicate_copies_of_same_artifact_are_not_ambiguous(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)
    copy_root = tmp_path / "copy"
    copy_root.mkdir()
    source = root / "rollout_census_sha256.json"
    (copy_root / "rollout-copy.json").write_bytes(
        source.read_bytes()
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root, copy_root],
    )
    slot = {
        row["slot_id"]: row for row in manifest["slots"]
    }["policy_scorecard.rollout_census_sha256"]
    assert slot["status"] == "RESOLVED_READABLE"
    assert len(slot["all_matches"]) >= 2


def test_reference_container_match_is_not_used_as_hydrated_evidence(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)
    target = refs["rollout_census_sha256"]
    _write_json(
        root / "round_evidence.json",
        {
            "schema_id": "ROUND_EVIDENCE_PACKAGE_V1",
            "rollout_census_sha256": target,
            "round_evidence_package_sha256": "d" * 64,
        },
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root],
    )
    slot = {
        row["slot_id"]: row for row in manifest["slots"]
    }["policy_scorecard.rollout_census_sha256"]
    assert slot["status"] == "RESOLVED_READABLE"
    assert slot["selected_match"]["schema_id"] == "ROLLOUT_CENSUS_V1"


def test_missing_required_artifact_blocks_blind_v2(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)
    (root / "mechanical_failure_census_sha256.json").unlink()

    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root],
    )
    assert manifest["hydration_ready"] is False
    assert (
        "policy_scorecard.mechanical_failure_census_sha256"
        in manifest["unresolved_required_slot_ids"]
    )
    with pytest.raises(ValueError, match="unresolved required"):
        build_strong_blind_pre_input_v2(
            blind_input_v1=blind,
            hydration_manifest=manifest,
        )


def test_conflicting_identity_claims_are_ambiguous(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)

    target = "e" * 64
    refs["metric_report_sha256"] = target
    blind = _blind_input(refs)

    first = {
        "schema_id": "ANALYZER_METRIC_REPORT_V1",
        "metric_report_sha256": target,
        "candidate_count": 60,
    }
    second = {
        "schema_id": "ANALYZER_METRIC_REPORT_V2",
        "metric_report_sha256": target,
        "candidate_count": 61,
    }
    _write_json(root / "metric-a.json", first)
    _write_json(root / "metric-b.json", second)

    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root],
    )
    slot = {
        row["slot_id"]: row for row in manifest["slots"]
    }["analyzer_evidence.metric_report_sha256"]
    assert slot["status"] == "QUERY_REQUIRED_AMBIGUOUS"
    assert manifest["hydration_ready"] is False


def test_blind_v2_adds_readable_views_without_human_decision_fields(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)
    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root],
    )
    hydrated = build_strong_blind_pre_input_v2(
        blind_input_v1=blind,
        hydration_manifest=manifest,
    )

    assert hydrated["schema_id"] == (
        "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2"
    )
    assert hydrated["evidence_hydration_contract"][
        "all_non_null_required_references_resolved"
    ] is True
    assert hydrated["readable_evidence_views"][
        "resource_and_cost"
    ]["resource_budget_manifest_sha256"][
        "readable_view"
    ]["content"]["environment_branch_budget"] == 120

    forbidden_keys = {
        "selected_candidate_sha256s",
        "selected_source_state_sha256s",
        "human_selection_rationale",
        "current_f0f1_outcomes",
    }

    def walk_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from walk_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk_keys(child)

    assert not forbidden_keys.intersection(walk_keys(hydrated))


def test_reference_trace_v3_binds_hydrated_blind_input(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)
    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root],
    )
    hydrated = build_strong_blind_pre_input_v2(
        blind_input_v1=blind,
        hydration_manifest=manifest,
    )
    trace_v2 = {
        "schema_id": "RESEARCH_PLANNER_REFERENCE_TRACE_V2",
        "schema_version": 2,
        "round_id": "round-k",
        "pre_decision": {
            "strong_blind_input_sha256": blind[
                "blind_input_sha256"
            ],
        },
        "trace_sha256": "f" * 64,
    }

    trace_v3 = build_reference_trace_v3(
        reference_trace_v2=trace_v2,
        hydration_manifest=manifest,
        blind_input_v2=hydrated,
    )
    assert trace_v3["schema_id"] == (
        "RESEARCH_PLANNER_REFERENCE_TRACE_V3"
    )
    assert trace_v3["pre_decision"][
        "source_strong_blind_input_v1_sha256"
    ] == blind["blind_input_sha256"]
    assert trace_v3["pre_decision"][
        "strong_blind_input_sha256"
    ] == hydrated["blind_input_sha256"]



def test_hydrated_blind_validator_rejects_tampered_content(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)
    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root],
    )
    hydrated = build_strong_blind_pre_input_v2(
        blind_input_v1=blind,
        hydration_manifest=manifest,
    )

    validate_hydrated_blind_input_v2(
        blind_input_v2=hydrated,
        hydration_manifest=manifest,
    )

    hydrated["readable_evidence_views"]["policy_scorecard"][
        "rollout_census_sha256"
    ]["readable_view"]["content"]["success_count"] = 999

    with pytest.raises(ValueError, match="blind V2 SHA mismatch"):
        validate_hydrated_blind_input_v2(
            blind_input_v2=hydrated,
            hydration_manifest=manifest,
        )


def test_formal_pre_outcome_selected_candidate_list_is_not_human_leak(
    tmp_path: Path,
) -> None:
    root, refs, blind = _make_complete_fixture(tmp_path)
    formal_path = root / "formal_result_manifest_sha256.json"
    formal_value = {
        "schema_id": "FORMAL_RESULT_MANIFEST_V1",
        "selected_candidate_count": 60,
        "selected_candidate_sha256s": [
            f"{index:064x}" for index in range(60)
        ],
        "source_state_count": 30,
    }
    refs["formal_result_manifest_sha256"] = _write_json(
        formal_path,
        formal_value,
    )
    blind = _blind_input(refs)

    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind,
        roots=[root],
    )

    assert manifest["hydration_ready"] is True
    formal = manifest["lane_views"]["analyzer_evidence"][
        "formal_result_manifest_sha256"
    ]["readable_view"]["content"]
    assert len(formal["selected_candidate_sha256s"]) == 60
