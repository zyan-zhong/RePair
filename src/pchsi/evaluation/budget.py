"""Immutable dual-budget accounting for E1 RAW_WITH_MENU_V1.

The state machine separately tracks:

- completed policy generations;
- executed environment actions;
- format/protocol failures;
- inadmissible actions;
- consecutive policy responses that execute no environment action.

This module does not parse model responses, inspect action menus, call an
environment, construct prompts or perform episode rollout.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


__all__ = [
    "BudgetAttemptOutcome",
    "BudgetLimits",
    "BudgetState",
    "EpisodeTerminationReason",
    "apply_completed_attempt",
    "can_start_policy_attempt",
    "resolve_after_environment",
    "resolve_nonexecuted_termination",
]


class BudgetAttemptOutcome(str, Enum):
    """Frozen outcomes that affect the E1 budgets."""

    ACTION_EXECUTED = "ACTION_EXECUTED"
    FORMAT_PROTOCOL_FAILURE = "FORMAT_PROTOCOL_FAILURE"
    ACTION_NOT_ADMISSIBLE = "ACTION_NOT_ADMISSIBLE"


class EpisodeTerminationReason(str, Enum):
    """Frozen public episode termination reasons."""

    ENVIRONMENT_TERMINATED = "ENVIRONMENT_TERMINATED"
    POLICY_ATTEMPT_BUDGET_EXHAUSTED = (
        "POLICY_ATTEMPT_BUDGET_EXHAUSTED"
    )
    ENVIRONMENT_STEP_BUDGET_EXHAUSTED = (
        "ENVIRONMENT_STEP_BUDGET_EXHAUSTED"
    )
    CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED = (
        "CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED"
    )
    PROTOCOL_CONFIGURATION_ERROR = (
        "PROTOCOL_CONFIGURATION_ERROR"
    )
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"


def _require_nonnegative_integer(
    *,
    name: str,
    value: object,
) -> int:
    """Validate one nonnegative integer, rejecting bool explicitly."""

    if type(value) is not int:
        raise TypeError(
            f"{name} must be int"
        )

    if value < 0:
        raise ValueError(
            f"{name} must be >= 0"
        )

    return value


@dataclass(frozen=True, slots=True)
class BudgetLimits:
    """Immutable E1 rollout-budget limits."""

    max_policy_attempts: int = 60
    max_environment_steps: int = 30
    max_consecutive_nonexecuted_attempts: int = 3

    def __post_init__(self) -> None:
        _require_nonnegative_integer(
            name="max_policy_attempts",
            value=self.max_policy_attempts,
        )

        _require_nonnegative_integer(
            name="max_environment_steps",
            value=self.max_environment_steps,
        )

        _require_nonnegative_integer(
            name=(
                "max_consecutive_nonexecuted_attempts"
            ),
            value=(
                self.max_consecutive_nonexecuted_attempts
            ),
        )


@dataclass(frozen=True, slots=True)
class BudgetState:
    """Immutable counters for one E1 episode."""

    policy_attempt_count: int = 0
    environment_step_count: int = 0
    protocol_failure_count: int = 0
    inadmissible_action_count: int = 0
    consecutive_nonexecuted_attempt_count: int = 0

    def __post_init__(self) -> None:
        for name in (
            "policy_attempt_count",
            "environment_step_count",
            "protocol_failure_count",
            "inadmissible_action_count",
            "consecutive_nonexecuted_attempt_count",
        ):
            _require_nonnegative_integer(
                name=name,
                value=getattr(self, name),
            )


def _validate_limits(
    limits: BudgetLimits,
) -> None:
    """Reject non-BudgetLimits callers explicitly."""

    if not isinstance(limits, BudgetLimits):
        raise TypeError(
            "limits must be BudgetLimits"
        )


def _validate_state_against_limits(
    state: BudgetState,
    limits: BudgetLimits,
) -> None:
    """Validate one state before or after a transition."""

    if not isinstance(state, BudgetState):
        raise TypeError(
            "state must be BudgetState"
        )

    _validate_limits(limits)

    if (
        state.policy_attempt_count
        > limits.max_policy_attempts
    ):
        raise ValueError(
            "policy_attempt_count exceeds "
            "max_policy_attempts"
        )

    if (
        state.environment_step_count
        > limits.max_environment_steps
    ):
        raise ValueError(
            "environment_step_count exceeds "
            "max_environment_steps"
        )

    if (
        state.consecutive_nonexecuted_attempt_count
        > limits.max_consecutive_nonexecuted_attempts
    ):
        raise ValueError(
            "consecutive_nonexecuted_attempt_count "
            "exceeds "
            "max_consecutive_nonexecuted_attempts"
        )


def can_start_policy_attempt(
    state: BudgetState,
    limits: BudgetLimits,
) -> bool:
    """Return whether one more policy generation is available."""

    _validate_state_against_limits(
        state,
        limits,
    )

    return (
        state.policy_attempt_count
        < limits.max_policy_attempts
    )


def apply_completed_attempt(
    state: BudgetState,
    outcome: BudgetAttemptOutcome,
    limits: BudgetLimits,
) -> BudgetState:
    """Apply exactly one completed model generation immutably."""

    _validate_state_against_limits(
        state,
        limits,
    )

    if not isinstance(
        outcome,
        BudgetAttemptOutcome,
    ):
        raise TypeError(
            "outcome must be BudgetAttemptOutcome"
        )

    if not can_start_policy_attempt(
        state,
        limits,
    ):
        raise ValueError(
            "policy attempt budget is exhausted"
        )

    next_policy_attempt_count = (
        state.policy_attempt_count + 1
    )

    if (
        outcome
        is BudgetAttemptOutcome.ACTION_EXECUTED
    ):
        if (
            state.environment_step_count
            >= limits.max_environment_steps
        ):
            raise ValueError(
                "environment step budget is exhausted"
            )

        updated = BudgetState(
            policy_attempt_count=(
                next_policy_attempt_count
            ),
            environment_step_count=(
                state.environment_step_count + 1
            ),
            protocol_failure_count=(
                state.protocol_failure_count
            ),
            inadmissible_action_count=(
                state.inadmissible_action_count
            ),
            consecutive_nonexecuted_attempt_count=0,
        )

    elif (
        outcome
        is (
            BudgetAttemptOutcome
            .FORMAT_PROTOCOL_FAILURE
        )
    ):
        updated = BudgetState(
            policy_attempt_count=(
                next_policy_attempt_count
            ),
            environment_step_count=(
                state.environment_step_count
            ),
            protocol_failure_count=(
                state.protocol_failure_count + 1
            ),
            inadmissible_action_count=(
                state.inadmissible_action_count
            ),
            consecutive_nonexecuted_attempt_count=(
                state
                .consecutive_nonexecuted_attempt_count
                + 1
            ),
        )

    elif (
        outcome
        is (
            BudgetAttemptOutcome
            .ACTION_NOT_ADMISSIBLE
        )
    ):
        updated = BudgetState(
            policy_attempt_count=(
                next_policy_attempt_count
            ),
            environment_step_count=(
                state.environment_step_count
            ),
            protocol_failure_count=(
                state.protocol_failure_count
            ),
            inadmissible_action_count=(
                state.inadmissible_action_count + 1
            ),
            consecutive_nonexecuted_attempt_count=(
                state
                .consecutive_nonexecuted_attempt_count
                + 1
            ),
        )

    else:
        raise AssertionError(
            "unreachable BudgetAttemptOutcome"
        )

    _validate_state_against_limits(
        updated,
        limits,
    )

    return updated


def resolve_nonexecuted_termination(
    state: BudgetState,
    limits: BudgetLimits,
) -> EpisodeTerminationReason | None:
    """Resolve termination after a response executed no action.

    Priority:

    1. consecutive nonexecuted-attempt exhaustion;
    2. total policy-attempt exhaustion.
    """

    _validate_state_against_limits(
        state,
        limits,
    )

    if (
        state.consecutive_nonexecuted_attempt_count
        >= (
            limits
            .max_consecutive_nonexecuted_attempts
        )
    ):
        return (
            EpisodeTerminationReason
            .CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
        )

    if (
        state.policy_attempt_count
        >= limits.max_policy_attempts
    ):
        return (
            EpisodeTerminationReason
            .POLICY_ATTEMPT_BUDGET_EXHAUSTED
        )

    return None


def resolve_after_environment(
    state: BudgetState,
    limits: BudgetLimits,
    *,
    infrastructure_error: bool,
    environment_terminated: bool,
) -> EpisodeTerminationReason | None:
    """Resolve termination after a reserved environment action.

    Priority:

    1. infrastructure error;
    2. environment termination;
    3. environment-step exhaustion;
    4. policy-attempt exhaustion.
    """

    _validate_state_against_limits(
        state,
        limits,
    )

    if type(infrastructure_error) is not bool:
        raise TypeError(
            "infrastructure_error must be bool"
        )

    if type(environment_terminated) is not bool:
        raise TypeError(
            "environment_terminated must be bool"
        )

    if infrastructure_error:
        return (
            EpisodeTerminationReason
            .INFRASTRUCTURE_ERROR
        )

    if environment_terminated:
        return (
            EpisodeTerminationReason
            .ENVIRONMENT_TERMINATED
        )

    if (
        state.environment_step_count
        >= limits.max_environment_steps
    ):
        return (
            EpisodeTerminationReason
            .ENVIRONMENT_STEP_BUDGET_EXHAUSTED
        )

    if (
        state.policy_attempt_count
        >= limits.max_policy_attempts
    ):
        return (
            EpisodeTerminationReason
            .POLICY_ATTEMPT_BUDGET_EXHAUSTED
        )

    return None
