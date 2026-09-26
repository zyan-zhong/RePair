from __future__ import annotations

import pytest

from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.budget import BudgetLimits, BudgetState
from pchsi.research_intelligence.human_f0f1_runtime import (
    aggregate_five_pair_effects_v1,
    classify_pair_effect_v1,
    reserve_registered_repair_environment_step_v1,
    validate_executable_exact_candidate_v1,
)


STATE = "1" * 64
CANDIDATE = "2" * 64


def _candidate(commands=("go to fridge 1", "open fridge 1")):
    return {
        "candidate_sha256": CANDIDATE,
        "source_state_sha256": STATE,
        "candidate_status": "EXECUTABLE_EXACT_ACTION",
        "requires_environment_verification": True,
        "live_menu_revalidation_required": True,
        "all_intervention_actions_count_against_environment_budget": True,
        "menu_sha256": sha256_string_sequence(commands),
        "exact_action": "open fridge 1",
        "option_actions": [],
        "termination_condition": None,
    }


def test_registered_repair_consumes_env_step_not_policy_attempt():
    before = BudgetState(
        policy_attempt_count=7,
        environment_step_count=11,
        protocol_failure_count=2,
        inadmissible_action_count=1,
        consecutive_nonexecuted_attempt_count=3,
    )
    after = reserve_registered_repair_environment_step_v1(before)
    assert after.policy_attempt_count == 7
    assert after.environment_step_count == 12
    assert after.protocol_failure_count == 2
    assert after.inadmissible_action_count == 1
    assert after.consecutive_nonexecuted_attempt_count == 0


def test_registered_repair_rejects_exhausted_environment_budget():
    limits = BudgetLimits(max_policy_attempts=60, max_environment_steps=30)
    before = BudgetState(environment_step_count=30)
    with pytest.raises(ValueError, match="environment step budget is exhausted"):
        reserve_registered_repair_environment_step_v1(before, limits)


def test_exact_candidate_passes_only_exact_live_menu_revalidation():
    commands = ("go to fridge 1", "open fridge 1")
    action = validate_executable_exact_candidate_v1(
        _candidate(commands),
        expected_candidate_sha256=CANDIDATE,
        expected_source_state_sha256=STATE,
        live_commands=commands,
    )
    assert action == "open fridge 1"


def test_exact_candidate_rejects_menu_reordering_even_with_same_members():
    registered = ("go to fridge 1", "open fridge 1")
    live = tuple(reversed(registered))
    with pytest.raises(ValueError, match="live menu SHA differs"):
        validate_executable_exact_candidate_v1(
            _candidate(registered),
            expected_candidate_sha256=CANDIDATE,
            expected_source_state_sha256=STATE,
            live_commands=live,
        )


def test_exact_candidate_rejects_case_changed_action():
    commands = ("go to fridge 1", "Open fridge 1")
    candidate = _candidate(commands)
    candidate["exact_action"] = "open fridge 1"
    with pytest.raises(ValueError, match="exact live-menu member"):
        validate_executable_exact_candidate_v1(
            candidate,
            expected_candidate_sha256=CANDIDATE,
            expected_source_state_sha256=STATE,
            live_commands=commands,
        )


@pytest.mark.parametrize(
    ("f0", "f1", "effect", "relation"),
    [
        (False, True, "BENEFIT", "F0_FAIL_F1_SUCCESS"),
        (True, False, "HARM", "F0_SUCCESS_F1_FAIL"),
        (True, True, "NEUTRAL", "BOTH_SUCCESS"),
        (False, False, "NEUTRAL", "BOTH_FAILURE"),
    ],
)
def test_pair_effect_uses_terminal_environment_outcomes_only(f0, f1, effect, relation):
    result = classify_pair_effect_v1(f0_success=f0, f1_success=f1)
    assert result == {"effect": effect, "terminal_relation": relation}


def test_incomplete_pair_is_uncertain():
    assert classify_pair_effect_v1(
        f0_success=None,
        f1_success=True,
        f0_complete=False,
        f1_complete=True,
    )["effect"] == "UNCERTAIN"


def test_four_of_five_stability():
    stable = aggregate_five_pair_effects_v1(
        ["BENEFIT", "BENEFIT", "BENEFIT", "BENEFIT", "HARM"]
    )
    assert stable["stable_effect"] == "BENEFIT"
    assert stable["four_of_five_stable"] is True

    unstable = aggregate_five_pair_effects_v1(
        ["BENEFIT", "BENEFIT", "HARM", "HARM", "NEUTRAL"]
    )
    assert unstable["stable_effect"] == "UNCERTAIN"
    assert unstable["four_of_five_stable"] is False
