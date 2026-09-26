from __future__ import annotations

import importlib

import pytest

from pchsi.reference_loop.canonical import domain_hash


def _m():
    return importlib.import_module("pchsi.analyzer.local_results")


GAME_SHA = "b" * 64


def _pack(*, success: bool = False) -> dict[str, object]:
    pack = {
        "schema_id": "ANALYZER_EVIDENCE_PACK_V1",
        "schema_version": 1,
        "pack_role": "COMMON_EVIDENCE_IDENTICAL_ACROSS_A0_A1_A2_A3",
        "task_identity": {
            "task_id": "task-1",
            "task_type": "pick_and_place_simple",
            "gamefile_sha256": GAME_SHA,
        },
        "trajectory_identity": {"fixture": "semantic-red-green"},
        "trajectory": [
            {
                "model_call_index": 0,
                "admissible_commands": ["look", "go to fridge 1"],
            },
            {
                "model_call_index": 1,
                "admissible_commands": ["look", "go to fridge 1"],
            },
            {
                "model_call_index": 2,
                "admissible_commands": ["look"],
            },
        ],
        "mechanical_evidence": {
            "generic_episode_facts": {
                "terminal_success": success,
                "environment_error_count": 0,
                "experiment_protocol_valid": True,
            },
            "generic": {"no_effect_transition_count": 1},
        },
        "memory_support_port": {
            "base_pack_exposes_memory": False,
            "memory_packet": None,
        },
        "analyzer_output_authority": {
            "benefit_harm_authority": False,
            "training_label_authority": False,
            "promotion_authority": False,
        },
        "requires_environment_verification": True,
        "evidence_pack_sha256": "0" * 64,
    }
    pack["evidence_pack_sha256"] = domain_hash(
        "ANALYZER_EVIDENCE_PACK_V1",
        pack,
        excluded_field="evidence_pack_sha256",
    )
    return pack


def _ref(pack: dict[str, object], index: int = 0) -> dict[str, object]:
    return {
        "artifact_sha256": pack["evidence_pack_sha256"],
        "evidence_kind": "TRAJECTORY_CALL",
        "local_selector": f"trajectory:{index}",
        "authority": "DETERMINISTIC_FACT",
    }


def _base(
    pack: dict[str, object],
    *,
    outcome: str = "FAILURE",
    condition: str = "A1_MULTI_HYPOTHESIS_LOCAL",
) -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_LOCAL_RESULT_V2",
        "schema_version": 2,
        "analyzer_run_id": "run-1",
        "condition_id": condition,
        "scientific_use": "PRIVILEGED_OFFLINE_ANALYSIS",
        "analysis_time_information_boundary": "POST_EPISODE_DEV_ONLY",
        "evidence_pack_sha256": pack["evidence_pack_sha256"],
        "task_id": "task-1",
        "gamefile_sha256": GAME_SHA,
        "route_status": "SCIENTIFIC_OUTCOME_AVAILABLE",
        "trajectory_outcome": outcome,
        "analysis_objective": (
            "FAILURE_DIAGNOSIS" if outcome == "FAILURE" else "SUCCESS_QUALITY"
        ),
        "error_instances": [],
        "success_analysis": None,
        "local_repairs": [],
        "abstained": False,
        "abstain_reason": None,
        "raw_response_sha256": "c" * 64,
        "validated_result_sha256": "0" * 64,
        "local_result_sha256": "0" * 64,
    }


def _error(
    pack: dict[str, object],
    eid: str,
    hid: str,
    index: int,
) -> dict[str, object]:
    return {
        "error_instance_id": eid,
        "trigger_call_index": index,
        "relevant_start_call_index": 0,
        "critical_window_start_call_index": 0,
        "critical_window_end_call_index": 2,
        "resolution_status": "ACTIVE",
        "terminal_footprint": "DIRECT_TERMINAL_IMPACT",
        "supporting_evidence_refs": [_ref(pack, index)],
        "counterevidence_refs": [],
        "mechanism_hypotheses": [
            {
                "hypothesis_id": hid,
                "rank": 1,
                "mechanism_family": "GOAL_AND_PHASE_PROGRESS_TRACKING",
                "statement": "Candidate mechanism.",
                "supporting_evidence_refs": [_ref(pack, index)],
                "counterevidence_refs": [],
                "counterevidence_status": (
                    "NONE_FOUND_WITHIN_VISIBLE_EVIDENCE"
                ),
                "alternative_explanation_ids": [],
                "confidence": 0.7,
                "uncertainty": "Unverified.",
            }
        ],
        "candidate_principal": eid == "e1",
        "uncertainty": "Unverified.",
    }


def _failure(
    module,
    pack: dict[str, object],
    *,
    two_errors: bool = True,
) -> dict[str, object]:
    payload = _base(pack)
    payload["error_instances"] = [_error(pack, "e1", "h1", 1)]
    if two_errors:
        payload["error_instances"].append(_error(pack, "e2", "h2", 2))
    payload["local_repairs"] = [
        {
            "local_repair_id": "r1",
            "rank": 1,
            "repair_kind": "EXACT_ACTION",
            "decision_call_index": 1,
            "exact_action": "go to fridge 1",
            "option_actions": [],
            "termination_condition": None,
            "trainable_rule": None,
            "supporting_hypothesis_ids": ["h1"],
            "supporting_evidence_refs": [_ref(pack, 1)],
            "known_risks": ["May interrupt baseline."],
            "requires_environment_verification": True,
        }
    ]
    return module.finalize_local_result(payload)


def test_real_multiple_error_instances_remain_valid() -> None:
    m = _m()
    pack = _pack()
    result = m.validate_local_result(_failure(m, pack), evidence_pack=pack)
    assert len(result["error_instances"]) == 2


def test_fake_mechanical_reference_is_rejected_by_exact_resolver() -> None:
    m = _m()
    pack = _pack()
    payload = _failure(m, pack)
    payload["error_instances"][0]["supporting_evidence_refs"] = [
        {
            "artifact_sha256": pack["evidence_pack_sha256"],
            "evidence_kind": "MECHANICAL_FACT",
            "local_selector": "mechanical:THIS_FACT_DOES_NOT_EXIST",
            "authority": "DETERMINISTIC_FACT",
        }
    ]
    payload = m.finalize_local_result(payload)
    with pytest.raises(ValueError, match="does not exist"):
        m.validate_local_result(payload, evidence_pack=pack)


def test_duplicate_error_instance_id_is_rejected() -> None:
    m = _m()
    pack = _pack()
    payload = _failure(m, pack)
    payload["error_instances"][1]["error_instance_id"] = "e1"
    payload = m.finalize_local_result(payload)
    with pytest.raises(ValueError, match="duplicate error_instance_id"):
        m.validate_local_result(payload, evidence_pack=pack)


def test_dangling_supporting_hypothesis_is_rejected() -> None:
    m = _m()
    pack = _pack()
    payload = _failure(m, pack)
    payload["local_repairs"][0]["supporting_hypothesis_ids"] = ["missing"]
    payload = m.finalize_local_result(payload)
    with pytest.raises(ValueError, match="hypothesis"):
        m.validate_local_result(payload, evidence_pack=pack)


def test_route_lane_mismatch_is_rejected() -> None:
    m = _m()
    failure_pack = _pack(success=False)
    payload = _base(failure_pack, outcome="SUCCESS")
    payload["success_analysis"] = {
        "progress_instances": [],
        "necessary_decisions": [],
        "critical_success_transitions": [],
        "useful_exploration": [],
        "self_recovery_events": [],
        "redundancy_candidates": [],
        "workflow_references": [],
        "regression_guards": [],
        "efficiency_candidates": [],
    }
    payload = m.finalize_local_result(payload)
    with pytest.raises(ValueError, match="outcome/lane"):
        m.validate_local_result(payload, evidence_pack=failure_pack)


def test_exact_action_must_exist_in_source_menu() -> None:
    m = _m()
    pack = _pack()
    payload = _failure(m, pack)
    payload["local_repairs"][0]["exact_action"] = "invented action"
    payload = m.finalize_local_result(payload)
    with pytest.raises(ValueError, match="source menu"):
        m.validate_local_result(payload, evidence_pack=pack)


def test_success_lane_is_bound_to_success_evidence_pack() -> None:
    m = _m()
    pack = _pack(success=True)
    payload = _base(pack, outcome="SUCCESS")
    payload["success_analysis"] = {
        "progress_instances": [
            {
                "event_id": "progress-1",
                "start_call_index": 0,
                "end_call_index": 1,
                "statement": "Observed progress.",
                "supporting_evidence_refs": [_ref(pack, 0)],
                "uncertainty": "Necessity is unverified.",
                "requires_environment_verification": False,
            }
        ],
        "necessary_decisions": [],
        "critical_success_transitions": [],
        "useful_exploration": [],
        "self_recovery_events": [],
        "redundancy_candidates": [],
        "workflow_references": [],
        "regression_guards": [],
        "efficiency_candidates": [],
    }
    payload = m.finalize_local_result(payload)
    result = m.validate_local_result(payload, evidence_pack=pack)
    assert result["trajectory_outcome"] == "SUCCESS"


def test_top_level_abstention_is_exclusive() -> None:
    m = _m()
    pack = _pack()
    payload = _base(pack)
    payload["abstained"] = True
    payload["abstain_reason"] = "Insufficient evidence."
    payload = m.finalize_local_result(payload)
    assert m.validate_local_result(payload, evidence_pack=pack)["abstained"] is True

    invalid = _failure(m, pack)
    invalid["abstained"] = True
    invalid["abstain_reason"] = "Insufficient evidence."
    invalid = m.finalize_local_result(invalid)
    with pytest.raises(ValueError, match="abstain|abstention"):
        m.validate_local_result(invalid, evidence_pack=pack)
