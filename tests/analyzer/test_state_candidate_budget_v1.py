from __future__ import annotations

from copy import deepcopy

import pytest

from pchsi.analyzer.state_candidate_budget import (
    deduplicate_execution_equivalent,
    execution_identity_sha256,
    materialize_state_condition_k1,
)


STATE = "a" * 64
MENU = "b" * 64


def _candidate(
    *,
    candidate_sha: str,
    proposal_sha: str,
    exact: str | None = "go to fridge 1",
    option: list[str] | None = None,
    termination: str | None = None,
    status: str = "EXECUTABLE_EXACT_ACTION",
):
    return {
        "schema_id": "ANALYZER_REPAIR_CANDIDATE_V1",
        "schema_version": 1,
        "candidate_kind": "FAILURE_REPAIR",
        "source_state_sha256": STATE,
        "menu_sha256": MENU,
        "source_proposal_sha256": proposal_sha,
        "candidate_status": status,
        "exact_action": exact,
        "option_actions": [] if option is None else option,
        "termination_condition": termination,
        "requires_environment_verification": True,
        "candidate_sha256": candidate_sha,
        "live_menu_revalidation_required": True,
        "all_intervention_actions_count_against_environment_budget": True,
    }


def test_execution_identity_ignores_proposal_and_candidate_provenance():
    a = _candidate(candidate_sha="1" * 64, proposal_sha="2" * 64)
    b = _candidate(candidate_sha="3" * 64, proposal_sha="4" * 64)
    assert execution_identity_sha256(a) == execution_identity_sha256(b)
    buckets = deduplicate_execution_equivalent([a, b])
    assert len(buckets) == 1


def test_equivalent_candidates_materialize_one_formal_candidate():
    a = _candidate(candidate_sha="1" * 64, proposal_sha="2" * 64)
    b = _candidate(candidate_sha="3" * 64, proposal_sha="4" * 64)
    out = materialize_state_condition_k1(
        condition_id="A2", source_state_sha256=STATE, candidates=[b, a]
    )
    assert out["candidate_count"] == 1
    assert out["formal_disposition"] == "FORMAL_CANDIDATE_REGISTERED"
    assert out["equivalent_candidate_sha256s"] == ["1" * 64, "3" * 64]


def test_genuinely_distinct_actions_fail_closed_without_winner_selection():
    a = _candidate(candidate_sha="1" * 64, proposal_sha="2" * 64)
    b = _candidate(
        candidate_sha="3" * 64,
        proposal_sha="4" * 64,
        exact="go to cabinet 1",
    )
    out = materialize_state_condition_k1(
        condition_id="A2", source_state_sha256=STATE, candidates=[a, b]
    )
    assert out["candidate_count"] == 0
    assert out["abstained"] is True
    assert out["voluntary_abstention"] is False
    assert out["formal_disposition"] == "METHOD_INVALID_K1_STATE_BUDGET_COLLISION"
    assert out["selected_candidate_sha256"] is None


def test_short_option_termination_is_part_of_execution_identity():
    a = _candidate(
        candidate_sha="1" * 64,
        proposal_sha="2" * 64,
        exact=None,
        option=["go to fridge 1", "open fridge 1"],
        termination="stop when fridge is open",
        status="EXECUTABLE_SHORT_OPTION",
    )
    b = deepcopy(a)
    b["candidate_sha256"] = "3" * 64
    b["source_proposal_sha256"] = "4" * 64
    assert execution_identity_sha256(a) == execution_identity_sha256(b)

    c = deepcopy(b)
    c["candidate_sha256"] = "5" * 64
    c["termination_condition"] = "stop after first action"
    assert execution_identity_sha256(a) != execution_identity_sha256(c)


def test_rejected_artifacts_do_not_consume_k1_budget():
    rejected = _candidate(
        candidate_sha="1" * 64,
        proposal_sha="2" * 64,
        exact=None,
        status="REJECTED_CROSSCHECK",
    )
    out = materialize_state_condition_k1(
        condition_id="A3",
        source_state_sha256=STATE,
        candidates=[rejected],
        zero_candidate_disposition="X_REQUIRES_ABSTENTION",
    )
    assert out["candidate_count"] == 0
    assert out["formal_disposition"] == "X_REQUIRES_ABSTENTION"
    assert out["voluntary_abstention"] is False


def test_model_abstention_is_distinct_from_method_failure():
    out = materialize_state_condition_k1(
        condition_id="A2",
        source_state_sha256=STATE,
        candidates=[],
        zero_candidate_disposition="MODEL_ABSTAIN",
    )
    assert out["candidate_count"] == 0
    assert out["abstained"] is True
    assert out["voluntary_abstention"] is True
    assert out["method_failure_reason"] is None


def test_method_source_binding_failure_remains_method_failure():
    out = materialize_state_condition_k1(
        condition_id="A1",
        source_state_sha256=STATE,
        candidates=[],
        zero_candidate_disposition="METHOD_SOURCE_BINDING_FAILURE",
    )
    assert out["candidate_count"] == 0
    assert out["voluntary_abstention"] is False
    assert out["method_failure_reason"] == "METHOD_SOURCE_BINDING_FAILURE"


def test_input_order_does_not_change_materialization():
    a = _candidate(candidate_sha="1" * 64, proposal_sha="2" * 64)
    b = _candidate(candidate_sha="3" * 64, proposal_sha="4" * 64)
    x = materialize_state_condition_k1(
        condition_id="A2", source_state_sha256=STATE, candidates=[a, b]
    )
    y = materialize_state_condition_k1(
        condition_id="A2", source_state_sha256=STATE, candidates=[b, a]
    )
    assert x == y


def test_candidate_for_another_state_is_rejected():
    a = _candidate(candidate_sha="1" * 64, proposal_sha="2" * 64)
    a["source_state_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="outside requested source state"):
        materialize_state_condition_k1(
            condition_id="A2", source_state_sha256=STATE, candidates=[a]
        )
