from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pchsi.evaluation.budget import (
    BudgetAttemptOutcome,
    BudgetLimits,
    BudgetState,
    EpisodeTerminationReason,
    apply_completed_attempt,
    can_start_policy_attempt,
    resolve_after_environment,
    resolve_nonexecuted_termination,
)


DEFAULT_LIMITS = BudgetLimits()


def test_budget_enums_are_exact() -> None:
    assert {
        item.name: item.value
        for item in BudgetAttemptOutcome
    } == {
        "ACTION_EXECUTED": "ACTION_EXECUTED",
        "FORMAT_PROTOCOL_FAILURE": (
            "FORMAT_PROTOCOL_FAILURE"
        ),
        "ACTION_NOT_ADMISSIBLE": (
            "ACTION_NOT_ADMISSIBLE"
        ),
    }

    assert {
        item.name: item.value
        for item in EpisodeTerminationReason
    } == {
        "ENVIRONMENT_TERMINATED": (
            "ENVIRONMENT_TERMINATED"
        ),
        "POLICY_ATTEMPT_BUDGET_EXHAUSTED": (
            "POLICY_ATTEMPT_BUDGET_EXHAUSTED"
        ),
        "ENVIRONMENT_STEP_BUDGET_EXHAUSTED": (
            "ENVIRONMENT_STEP_BUDGET_EXHAUSTED"
        ),
        (
            "CONSECUTIVE_NONEXECUTED_"
            "ATTEMPTS_EXHAUSTED"
        ): (
            "CONSECUTIVE_NONEXECUTED_"
            "ATTEMPTS_EXHAUSTED"
        ),
        "PROTOCOL_CONFIGURATION_ERROR": (
            "PROTOCOL_CONFIGURATION_ERROR"
        ),
        "INFRASTRUCTURE_ERROR": (
            "INFRASTRUCTURE_ERROR"
        ),
    }


def test_default_limits_are_exact_and_immutable() -> None:
    limits = BudgetLimits()

    assert limits.max_policy_attempts == 60
    assert limits.max_environment_steps == 30
    assert (
        limits.max_consecutive_nonexecuted_attempts
        == 3
    )

    with pytest.raises(FrozenInstanceError):
        limits.max_policy_attempts = 61  # type: ignore[misc]


def test_default_state_is_zero_and_immutable() -> None:
    state = BudgetState()

    assert state == BudgetState(
        policy_attempt_count=0,
        environment_step_count=0,
        protocol_failure_count=0,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=0,
    )

    with pytest.raises(FrozenInstanceError):
        state.policy_attempt_count = 1  # type: ignore[misc]


def test_generation_sixty_is_allowed() -> None:
    state = BudgetState(
        policy_attempt_count=59,
    )

    assert can_start_policy_attempt(
        state,
        DEFAULT_LIMITS,
    ) is True


def test_generation_sixty_one_is_rejected() -> None:
    state = BudgetState(
        policy_attempt_count=60,
    )

    assert can_start_policy_attempt(
        state,
        DEFAULT_LIMITS,
    ) is False


def test_format_failure_updates_only_required_counts() -> None:
    state = BudgetState(
        policy_attempt_count=10,
        environment_step_count=4,
        protocol_failure_count=2,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=1,
    )

    updated = apply_completed_attempt(
        state,
        BudgetAttemptOutcome.FORMAT_PROTOCOL_FAILURE,
        DEFAULT_LIMITS,
    )

    assert updated == BudgetState(
        policy_attempt_count=11,
        environment_step_count=4,
        protocol_failure_count=3,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=2,
    )

    assert updated is not state

    assert state == BudgetState(
        policy_attempt_count=10,
        environment_step_count=4,
        protocol_failure_count=2,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=1,
    )


def test_inadmissible_action_updates_only_required_counts() -> None:
    state = BudgetState(
        policy_attempt_count=7,
        environment_step_count=3,
        protocol_failure_count=2,
        inadmissible_action_count=4,
        consecutive_nonexecuted_attempt_count=1,
    )

    updated = apply_completed_attempt(
        state,
        BudgetAttemptOutcome.ACTION_NOT_ADMISSIBLE,
        DEFAULT_LIMITS,
    )

    assert updated == BudgetState(
        policy_attempt_count=8,
        environment_step_count=3,
        protocol_failure_count=2,
        inadmissible_action_count=5,
        consecutive_nonexecuted_attempt_count=2,
    )

    assert updated is not state


def test_executed_action_updates_both_budgets_and_resets() -> None:
    state = BudgetState(
        policy_attempt_count=10,
        environment_step_count=4,
        protocol_failure_count=2,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=2,
    )

    updated = apply_completed_attempt(
        state,
        BudgetAttemptOutcome.ACTION_EXECUTED,
        DEFAULT_LIMITS,
    )

    assert updated == BudgetState(
        policy_attempt_count=11,
        environment_step_count=5,
        protocol_failure_count=2,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=0,
    )

    assert updated is not state


def test_alternating_nonexecuted_attempts_reach_three() -> None:
    state = BudgetState()

    state = apply_completed_attempt(
        state,
        BudgetAttemptOutcome.FORMAT_PROTOCOL_FAILURE,
        DEFAULT_LIMITS,
    )

    state = apply_completed_attempt(
        state,
        BudgetAttemptOutcome.ACTION_NOT_ADMISSIBLE,
        DEFAULT_LIMITS,
    )

    state = apply_completed_attempt(
        state,
        BudgetAttemptOutcome.FORMAT_PROTOCOL_FAILURE,
        DEFAULT_LIMITS,
    )

    assert state.policy_attempt_count == 3
    assert state.protocol_failure_count == 2
    assert state.inadmissible_action_count == 1
    assert (
        state.consecutive_nonexecuted_attempt_count
        == 3
    )


def test_environment_step_thirty_is_allowed() -> None:
    state = BudgetState(
        policy_attempt_count=29,
        environment_step_count=29,
    )

    updated = apply_completed_attempt(
        state,
        BudgetAttemptOutcome.ACTION_EXECUTED,
        DEFAULT_LIMITS,
    )

    assert updated.policy_attempt_count == 30
    assert updated.environment_step_count == 30


def test_environment_step_thirty_one_is_rejected() -> None:
    state = BudgetState(
        policy_attempt_count=30,
        environment_step_count=30,
    )

    with pytest.raises(ValueError):
        apply_completed_attempt(
            state,
            BudgetAttemptOutcome.ACTION_EXECUTED,
            DEFAULT_LIMITS,
        )

    assert state.environment_step_count == 30


@pytest.mark.parametrize(
    "outcome",
    list(BudgetAttemptOutcome),
)
def test_no_attempt_is_allowed_after_policy_sixty(
    outcome: BudgetAttemptOutcome,
) -> None:
    state = BudgetState(
        policy_attempt_count=60,
    )

    with pytest.raises(ValueError):
        apply_completed_attempt(
            state,
            outcome,
            DEFAULT_LIMITS,
        )

    assert state.policy_attempt_count == 60


def test_third_invalid_attempt_at_policy_sixty_uses_consecutive_reason(
) -> None:
    state = BudgetState(
        policy_attempt_count=59,
        protocol_failure_count=10,
        consecutive_nonexecuted_attempt_count=2,
    )

    updated = apply_completed_attempt(
        state,
        BudgetAttemptOutcome.FORMAT_PROTOCOL_FAILURE,
        DEFAULT_LIMITS,
    )

    assert updated.policy_attempt_count == 60
    assert (
        updated.consecutive_nonexecuted_attempt_count
        == 3
    )

    assert resolve_nonexecuted_termination(
        updated,
        DEFAULT_LIMITS,
    ) is (
        EpisodeTerminationReason
        .CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
    )


def test_consecutive_exhaustion_precedes_policy_exhaustion(
) -> None:
    state = BudgetState(
        policy_attempt_count=60,
        consecutive_nonexecuted_attempt_count=3,
    )

    assert resolve_nonexecuted_termination(
        state,
        DEFAULT_LIMITS,
    ) is (
        EpisodeTerminationReason
        .CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
    )


def test_policy_exhaustion_after_nonexecuted_attempt() -> None:
    state = BudgetState(
        policy_attempt_count=60,
        consecutive_nonexecuted_attempt_count=2,
    )

    assert resolve_nonexecuted_termination(
        state,
        DEFAULT_LIMITS,
    ) is (
        EpisodeTerminationReason
        .POLICY_ATTEMPT_BUDGET_EXHAUSTED
    )


def test_no_nonexecuted_termination_below_limits() -> None:
    state = BudgetState(
        policy_attempt_count=59,
        consecutive_nonexecuted_attempt_count=2,
    )

    assert resolve_nonexecuted_termination(
        state,
        DEFAULT_LIMITS,
    ) is None


def test_infrastructure_error_has_highest_priority() -> None:
    state = BudgetState(
        policy_attempt_count=60,
        environment_step_count=30,
    )

    assert resolve_after_environment(
        state,
        DEFAULT_LIMITS,
        infrastructure_error=True,
        environment_terminated=True,
    ) is EpisodeTerminationReason.INFRASTRUCTURE_ERROR


def test_environment_termination_precedes_environment_budget(
) -> None:
    state = BudgetState(
        policy_attempt_count=60,
        environment_step_count=30,
    )

    assert resolve_after_environment(
        state,
        DEFAULT_LIMITS,
        infrastructure_error=False,
        environment_terminated=True,
    ) is (
        EpisodeTerminationReason
        .ENVIRONMENT_TERMINATED
    )


def test_environment_budget_precedes_policy_budget() -> None:
    state = BudgetState(
        policy_attempt_count=60,
        environment_step_count=30,
    )

    assert resolve_after_environment(
        state,
        DEFAULT_LIMITS,
        infrastructure_error=False,
        environment_terminated=False,
    ) is (
        EpisodeTerminationReason
        .ENVIRONMENT_STEP_BUDGET_EXHAUSTED
    )


def test_policy_budget_resolves_when_environment_budget_remains(
) -> None:
    state = BudgetState(
        policy_attempt_count=60,
        environment_step_count=29,
    )

    assert resolve_after_environment(
        state,
        DEFAULT_LIMITS,
        infrastructure_error=False,
        environment_terminated=False,
    ) is (
        EpisodeTerminationReason
        .POLICY_ATTEMPT_BUDGET_EXHAUSTED
    )


def test_no_after_environment_termination_below_limits(
) -> None:
    state = BudgetState(
        policy_attempt_count=59,
        environment_step_count=29,
    )

    assert resolve_after_environment(
        state,
        DEFAULT_LIMITS,
        infrastructure_error=False,
        environment_terminated=False,
    ) is None


@pytest.mark.parametrize(
    (
        "field_name",
        "kwargs",
    ),
    [
        (
            "max_policy_attempts",
            {"max_policy_attempts": -1},
        ),
        (
            "max_environment_steps",
            {"max_environment_steps": -1},
        ),
        (
            "max_consecutive_nonexecuted_attempts",
            {
                "max_consecutive_nonexecuted_attempts": -1,
            },
        ),
    ],
)
def test_negative_limits_are_rejected(
    field_name: str,
    kwargs: dict[str, int],
) -> None:
    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        BudgetLimits(**kwargs)


@pytest.mark.parametrize(
    "field_name",
    [
        "policy_attempt_count",
        "environment_step_count",
        "protocol_failure_count",
        "inadmissible_action_count",
        "consecutive_nonexecuted_attempt_count",
    ],
)
def test_negative_state_counters_are_rejected(
    field_name: str,
) -> None:
    kwargs = {
        field_name: -1,
    }

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        BudgetState(**kwargs)


def test_boolean_budget_values_are_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="max_policy_attempts",
    ):
        BudgetLimits(
            max_policy_attempts=True,  # type: ignore[arg-type]
        )

    with pytest.raises(
        TypeError,
        match="policy_attempt_count",
    ):
        BudgetState(
            policy_attempt_count=False,  # type: ignore[arg-type]
        )


def test_zero_policy_budget_prevents_generation() -> None:
    limits = BudgetLimits(
        max_policy_attempts=0,
        max_environment_steps=0,
        max_consecutive_nonexecuted_attempts=0,
    )

    assert can_start_policy_attempt(
        BudgetState(),
        limits,
    ) is False


def test_state_above_policy_limit_is_rejected() -> None:
    state = BudgetState(
        policy_attempt_count=61,
    )

    with pytest.raises(
        ValueError,
        match="policy_attempt_count",
    ):
        can_start_policy_attempt(
            state,
            DEFAULT_LIMITS,
        )


def test_state_above_environment_limit_is_rejected() -> None:
    state = BudgetState(
        environment_step_count=31,
    )

    with pytest.raises(
        ValueError,
        match="environment_step_count",
    ):
        resolve_after_environment(
            state,
            DEFAULT_LIMITS,
            infrastructure_error=False,
            environment_terminated=False,
        )


def test_state_above_consecutive_limit_is_rejected() -> None:
    state = BudgetState(
        consecutive_nonexecuted_attempt_count=4,
    )

    with pytest.raises(
        ValueError,
        match="consecutive_nonexecuted_attempt_count",
    ):
        resolve_nonexecuted_termination(
            state,
            DEFAULT_LIMITS,
        )


def test_outcome_must_be_frozen_enum() -> None:
    with pytest.raises(
        TypeError,
        match="outcome",
    ):
        apply_completed_attempt(
            BudgetState(),
            "ACTION_EXECUTED",  # type: ignore[arg-type]
            DEFAULT_LIMITS,
        )


@pytest.mark.parametrize(
    (
        "infrastructure_error",
        "environment_terminated",
        "expected_parameter",
    ),
    [
        (
            1,
            False,
            "infrastructure_error",
        ),
        (
            False,
            0,
            "environment_terminated",
        ),
    ],
)
def test_environment_flags_must_be_bool(
    infrastructure_error: object,
    environment_terminated: object,
    expected_parameter: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=expected_parameter,
    ):
        resolve_after_environment(
            BudgetState(),
            DEFAULT_LIMITS,
            infrastructure_error=(
                infrastructure_error  # type: ignore[arg-type]
            ),
            environment_terminated=(
                environment_terminated  # type: ignore[arg-type]
            ),
        )
