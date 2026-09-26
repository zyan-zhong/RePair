from __future__ import annotations

from types import SimpleNamespace

import pytest

from pchsi.analyzer.act3_registration import build_group_signature_binding


def _trace():
    return SimpleNamespace(
        attempt_outcome="ACTION_NOT_ADMISSIBLE",
        failure_code="ACTION_NOT_ADMISSIBLE",
        admissibility_status="not_admissible",
        feedback_code="INVALID_ACTION_V1",
        normalized_action="go to fridge 1",
        policy_attempt_count_before=1,
        policy_attempt_count_after=2,
        environment_step_count_before=1,
        environment_step_count_after=1,
        protocol_failure_count_before=0,
        protocol_failure_count=0,
        inadmissible_action_count_before=0,
        inadmissible_action_count=1,
        consecutive_nonexecuted_attempt_count=1,
    )


def _mechanical():
    return {
        "generic_episode_facts": {"budget_exhaustion": False},
        "registered_domain_progress_facts": {
            "goal_object_parse_status": "PARSED",
            "goal_object_visible_events": [0],
            "goal_take_available_events": [0],
            "goal_object_acquired_events": [],
            "inventory_change_events": [],
            "required_treatment_completed_events": [],
            "placement_completed_events": [],
        },
    }


def _error():
    return {
        "error_instance_id": "e1",
        "critical_window_start_call_index": 1,
        "critical_window_end_call_index": 1,
    }


def test_group_signature_accepts_canonical_nested_task_identity():
    pack = {
        "task_identity": {"task_type": "pick_and_place_simple"},
        "mechanical_evidence": _mechanical(),
    }
    out = build_group_signature_binding(
        local_result={"local_result_sha256": "1" * 64},
        error=_error(),
        evidence_pack=pack,
        action_traces_by_call={1: _trace()},
    )
    assert out["task_family"] == "pick_and_place_simple"


def test_group_signature_rejects_conflicting_task_family_aliases():
    pack = {
        "task_type": "legacy_family",
        "task_identity": {"task_type": "canonical_family"},
        "mechanical_evidence": _mechanical(),
    }
    with pytest.raises(ValueError, match="task family identity mismatch"):
        build_group_signature_binding(
            local_result={"local_result_sha256": "1" * 64},
            error=_error(),
            evidence_pack=pack,
            action_traces_by_call={1: _trace()},
        )
