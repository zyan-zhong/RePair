"""Pure Runtime Core contracts for E1 RAW_WITH_MENU_V1.

This module implements:

- exact three-party menu validation;
- pre-policy protocol and budget gating;
- strict completed-generation processing;
- exact, case-sensitive admissibility;
- immutable budget transitions;
- environment-result finalization.

It does not call a model or environment, perform an environment transition,
repair an action, sort or deduplicate a menu, construct prompts, or perform rollout.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import cast

from pchsi.evaluation.action_trace import (
    sha256_string_sequence,
)
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
from pchsi.evaluation.raw_policy_parser import (
    FailureStage as ParserFailureStage,
    ParserFailureCode,
    ParserStatus,
    RawPolicyParseResult,
    parse_raw_policy_response,
)
from pchsi.evaluation.raw_policy_prompt import (
    InterfaceFeedbackCode,
)


__all__ = [
    "AdmissibilityStatus",
    "AttemptFailureStage",
    "AttemptOutcome",
    "MenuFailureCode",
    "MenuValidationResult",
    "ProtocolPreconditionResult",
    "RuntimeDecision",
    "RuntimeFailureCode",
    "finalize_environment_result",
    "process_completed_generation",
    "validate_menu_contract",
    "validate_runtime_preconditions",
]


class AttemptOutcome(str, Enum):
    """Frozen externally visible attempt outcomes."""

    ACTION_EXECUTED = "ACTION_EXECUTED"
    FORMAT_PROTOCOL_FAILURE = (
        "FORMAT_PROTOCOL_FAILURE"
    )
    ACTION_NOT_ADMISSIBLE = (
        "ACTION_NOT_ADMISSIBLE"
    )
    INFRASTRUCTURE_ERROR = (
        "INFRASTRUCTURE_ERROR"
    )


class AdmissibilityStatus(str, Enum):
    """Frozen Stage-3 admissibility states."""

    NOT_CHECKED = "not_checked"
    EXACT_MEMBER = "exact_member"
    NOT_ADMISSIBLE = "not_admissible"


class AttemptFailureStage(str, Enum):
    """Frozen stage attribution for failed attempts."""

    ENVELOPE = "envelope"
    ACTION_NORMALIZATION = "action_normalization"
    ADMISSIBILITY = "admissibility"
    INFRASTRUCTURE = "infrastructure"


class RuntimeFailureCode(str, Enum):
    """Frozen non-parser runtime failure codes."""

    ACTION_NOT_ADMISSIBLE = (
        "ACTION_NOT_ADMISSIBLE"
    )
    ENVIRONMENT_STEP_FAILED = (
        "ENVIRONMENT_STEP_FAILED"
    )


class MenuFailureCode(str, Enum):
    """Frozen failures for the three-party menu contract."""

    POLICY_MENU_COUNT_MISMATCH = (
        "POLICY_MENU_COUNT_MISMATCH"
    )
    POLICY_MENU_SEQUENCE_MISMATCH = (
        "POLICY_MENU_SEQUENCE_MISMATCH"
    )
    HARNESS_MENU_COUNT_MISMATCH = (
        "HARNESS_MENU_COUNT_MISMATCH"
    )
    HARNESS_MENU_SEQUENCE_MISMATCH = (
        "HARNESS_MENU_SEQUENCE_MISMATCH"
    )
    MENU_COMMAND_NOT_STRING = (
        "MENU_COMMAND_NOT_STRING"
    )
    MENU_COMMAND_EMPTY = "MENU_COMMAND_EMPTY"
    MENU_COMMAND_BOUNDARY_SPACE = (
        "MENU_COMMAND_BOUNDARY_SPACE"
    )
    MENU_COMMAND_MULTILINE = (
        "MENU_COMMAND_MULTILINE"
    )
    MENU_COMMAND_CONTROL_CHARACTER = (
        "MENU_COMMAND_CONTROL_CHARACTER"
    )
    MENU_COMMAND_TOO_LONG = (
        "MENU_COMMAND_TOO_LONG"
    )


@dataclass(frozen=True, slots=True)
class MenuValidationResult:
    """Immutable result of validating one three-party menu."""

    valid: bool
    failure_code: MenuFailureCode | None
    sequence_sha256: str | None


@dataclass(frozen=True, slots=True)
class ProtocolPreconditionResult:
    """Immutable decision made before any policy generation."""

    menu_validation: MenuValidationResult
    budget_before: BudgetState
    budget_after: BudgetState
    should_call_policy: bool
    termination_reason: EpisodeTerminationReason | None
    budget_limits: BudgetLimits = BudgetLimits()


@dataclass(frozen=True, slots=True)
class RuntimeDecision:
    """Immutable decision for one completed model generation."""

    budget_before: BudgetState
    budget_after: BudgetState
    parse_result: RawPolicyParseResult
    attempt_outcome: AttemptOutcome
    failure_stage: AttemptFailureStage | None
    failure_code: (
        ParserFailureCode
        | RuntimeFailureCode
        | None
    )
    normalized_action: str | None
    admissibility_status: AdmissibilityStatus
    feedback_code: InterfaceFeedbackCode | None
    should_call_env: bool
    candidate_environment_action: str | None
    termination_reason: EpisodeTerminationReason | None
    budget_limits: BudgetLimits = BudgetLimits()


def _require_action_limit(
    max_action_codepoints: object,
) -> int:
    """Validate the command-length limit."""

    if type(max_action_codepoints) is not int:
        raise TypeError(
            "max_action_codepoints must be int"
        )

    if max_action_codepoints < 0:
        raise ValueError(
            "max_action_codepoints must be >= 0"
        )

    return max_action_codepoints


def _freeze_menu(
    *,
    parameter_name: str,
    commands: Sequence[str],
) -> tuple[object, ...]:
    """Freeze one supplied menu without changing its order."""

    if isinstance(
        commands,
        (str, bytes, bytearray),
    ):
        raise TypeError(
            f"{parameter_name} must be a sequence "
            "of command strings, not a string-like object"
        )

    try:
        return tuple(commands)
    except TypeError as error:
        raise TypeError(
            f"{parameter_name} must be a sequence"
        ) from error


def _contains_forbidden_control_character(
    command: str,
) -> bool:
    """Detect C0, DEL and C1 controls."""

    for character in command:
        codepoint = ord(character)

        if codepoint <= 0x1F:
            return True

        if 0x7F <= codepoint <= 0x9F:
            return True

    return False


def _command_shape_failure(
    commands: tuple[object, ...],
    *,
    max_action_codepoints: int,
) -> MenuFailureCode | None:
    """Return the first deterministic command-shape failure."""

    for command in commands:
        if not isinstance(command, str):
            return (
                MenuFailureCode
                .MENU_COMMAND_NOT_STRING
            )

        if command == "":
            return (
                MenuFailureCode
                .MENU_COMMAND_EMPTY
            )

        if (
            command.startswith(" ")
            or command.endswith(" ")
        ):
            return (
                MenuFailureCode
                .MENU_COMMAND_BOUNDARY_SPACE
            )

        if "\n" in command or "\r" in command:
            return (
                MenuFailureCode
                .MENU_COMMAND_MULTILINE
            )

        if _contains_forbidden_control_character(
            command
        ):
            return (
                MenuFailureCode
                .MENU_COMMAND_CONTROL_CHARACTER
            )

        if len(command) > max_action_codepoints:
            return (
                MenuFailureCode
                .MENU_COMMAND_TOO_LONG
            )

    return None


def _invalid_menu(
    failure_code: MenuFailureCode,
) -> MenuValidationResult:
    """Construct one immutable invalid-menu result."""

    return MenuValidationResult(
        valid=False,
        failure_code=failure_code,
        sequence_sha256=None,
    )


def validate_menu_contract(
    *,
    policy_visible_commands: Sequence[str],
    harness_visible_commands: Sequence[str],
    environment_commands: Sequence[str],
    max_action_codepoints: int = 256,
) -> MenuValidationResult:
    """Validate exact three-party menu equality.

    No menu is sorted, filtered, deduplicated, truncated,
    case-normalized or otherwise repaired.
    """

    action_limit = _require_action_limit(
        max_action_codepoints
    )

    policy_commands = _freeze_menu(
        parameter_name="policy_visible_commands",
        commands=policy_visible_commands,
    )

    harness_commands = _freeze_menu(
        parameter_name="harness_visible_commands",
        commands=harness_visible_commands,
    )

    environment_commands_tuple = _freeze_menu(
        parameter_name="environment_commands",
        commands=environment_commands,
    )

    for commands in (
        environment_commands_tuple,
        policy_commands,
        harness_commands,
    ):
        failure_code = _command_shape_failure(
            commands,
            max_action_codepoints=action_limit,
        )

        if failure_code is not None:
            return _invalid_menu(
                failure_code
            )

    if (
        len(policy_commands)
        != len(environment_commands_tuple)
    ):
        return _invalid_menu(
            MenuFailureCode
            .POLICY_MENU_COUNT_MISMATCH
        )

    if (
        len(harness_commands)
        != len(environment_commands_tuple)
    ):
        return _invalid_menu(
            MenuFailureCode
            .HARNESS_MENU_COUNT_MISMATCH
        )

    if (
        policy_commands
        != environment_commands_tuple
    ):
        return _invalid_menu(
            MenuFailureCode
            .POLICY_MENU_SEQUENCE_MISMATCH
        )

    if (
        harness_commands
        != environment_commands_tuple
    ):
        return _invalid_menu(
            MenuFailureCode
            .HARNESS_MENU_SEQUENCE_MISMATCH
        )

    validated_environment_commands = cast(
        tuple[str, ...],
        environment_commands_tuple,
    )

    return MenuValidationResult(
        valid=True,
        failure_code=None,
        sequence_sha256=sha256_string_sequence(
            validated_environment_commands
        ),
    )


def validate_runtime_preconditions(
    *,
    policy_visible_commands: Sequence[str],
    harness_visible_commands: Sequence[str],
    environment_commands: Sequence[str],
    budget_state: BudgetState,
    budget_limits: BudgetLimits = BudgetLimits(),
    max_action_codepoints: int = 256,
) -> ProtocolPreconditionResult:
    """Validate all conditions required before a model call."""

    if not isinstance(
        budget_state,
        BudgetState,
    ):
        raise TypeError(
            "budget_state must be BudgetState"
        )

    if not isinstance(
        budget_limits,
        BudgetLimits,
    ):
        raise TypeError(
            "budget_limits must be BudgetLimits"
        )

    menu_validation = validate_menu_contract(
        policy_visible_commands=(
            policy_visible_commands
        ),
        harness_visible_commands=(
            harness_visible_commands
        ),
        environment_commands=(
            environment_commands
        ),
        max_action_codepoints=(
            max_action_codepoints
        ),
    )

    if not menu_validation.valid:
        return ProtocolPreconditionResult(
            menu_validation=menu_validation,
            budget_limits=budget_limits,
            budget_before=budget_state,
            budget_after=budget_state,
            should_call_policy=False,
            termination_reason=(
                EpisodeTerminationReason
                .PROTOCOL_CONFIGURATION_ERROR
            ),
        )

    policy_attempt_available = (
        can_start_policy_attempt(
            budget_state,
            budget_limits,
        )
    )

    if (
        budget_state.environment_step_count
        >= budget_limits.max_environment_steps
    ):
        return ProtocolPreconditionResult(
            menu_validation=menu_validation,
            budget_limits=budget_limits,
            budget_before=budget_state,
            budget_after=budget_state,
            should_call_policy=False,
            termination_reason=(
                EpisodeTerminationReason
                .ENVIRONMENT_STEP_BUDGET_EXHAUSTED
            ),
        )

    if (
        budget_state
        .consecutive_nonexecuted_attempt_count
        >= budget_limits
        .max_consecutive_nonexecuted_attempts
    ):
        return ProtocolPreconditionResult(
            menu_validation=menu_validation,
            budget_limits=budget_limits,
            budget_before=budget_state,
            budget_after=budget_state,
            should_call_policy=False,
            termination_reason=(
                EpisodeTerminationReason
                .CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
            ),
        )

    if not policy_attempt_available:
        return ProtocolPreconditionResult(
            menu_validation=menu_validation,
            budget_limits=budget_limits,
            budget_before=budget_state,
            budget_after=budget_state,
            should_call_policy=False,
            termination_reason=(
                EpisodeTerminationReason
                .POLICY_ATTEMPT_BUDGET_EXHAUSTED
            ),
        )

    return ProtocolPreconditionResult(
        menu_validation=menu_validation,
        budget_limits=budget_limits,
        budget_before=budget_state,
        budget_after=budget_state,
        should_call_policy=True,
        termination_reason=None,
    )


def _require_process_precondition(
    precondition_result: ProtocolPreconditionResult,
) -> None:
    """Require an unconsumed, successful pre-policy gate."""

    if not isinstance(
        precondition_result,
        ProtocolPreconditionResult,
    ):
        raise TypeError(
            "precondition_result must be "
            "ProtocolPreconditionResult"
        )

    if not isinstance(
        precondition_result.budget_limits,
        BudgetLimits,
    ):
        raise TypeError(
            "precondition_result.budget_limits "
            "must be BudgetLimits"
        )

    if (
        precondition_result.should_call_policy
        is not True
    ):
        raise ValueError(
            "precondition does not authorize "
            "a policy generation"
        )

    if (
        precondition_result.termination_reason
        is not None
    ):
        raise ValueError(
            "precondition already has a "
            "termination reason"
        )

    if (
        not precondition_result
        .menu_validation
        .valid
        or precondition_result
        .menu_validation
        .sequence_sha256
        is None
    ):
        raise ValueError(
            "precondition has no valid menu"
        )

    if (
        precondition_result.budget_before
        != precondition_result.budget_after
    ):
        raise ValueError(
            "precondition budget changed before "
            "the policy generation"
        )


def _validate_processing_menu(
    *,
    visible_admissible_commands: Sequence[str],
    precondition_result: ProtocolPreconditionResult,
    max_action_codepoints: int,
) -> tuple[str, ...]:
    """Validate that the generation uses the frozen menu."""

    current_validation = validate_menu_contract(
        policy_visible_commands=(
            visible_admissible_commands
        ),
        harness_visible_commands=(
            visible_admissible_commands
        ),
        environment_commands=(
            visible_admissible_commands
        ),
        max_action_codepoints=(
            max_action_codepoints
        ),
    )

    if not current_validation.valid:
        raise ValueError(
            "visible menu does not satisfy "
            "the menu contract"
        )

    if (
        current_validation.sequence_sha256
        != precondition_result
        .menu_validation
        .sequence_sha256
    ):
        raise ValueError(
            "visible menu does not match "
            "the precondition menu"
        )

    frozen_commands = _freeze_menu(
        parameter_name=(
            "visible_admissible_commands"
        ),
        commands=visible_admissible_commands,
    )

    return cast(
        tuple[str, ...],
        frozen_commands,
    )


def _map_parser_failure_stage(
    failure_stage: ParserFailureStage | None,
) -> AttemptFailureStage:
    """Map parser-local stages into attempt attribution."""

    if failure_stage is ParserFailureStage.ENVELOPE:
        return AttemptFailureStage.ENVELOPE

    if (
        failure_stage
        is ParserFailureStage.ACTION_NORMALIZATION
    ):
        return (
            AttemptFailureStage
            .ACTION_NORMALIZATION
        )

    raise AssertionError(
        "failed parser result has no known "
        "failure stage"
    )


def process_completed_generation(
    *,
    raw_response: str,
    visible_admissible_commands: Sequence[str],
    precondition_result: ProtocolPreconditionResult,
    budget_limits: BudgetLimits = BudgetLimits(),
    max_action_codepoints: int = 256,
) -> RuntimeDecision:
    """Process exactly one completed model generation.

    The function never calls an environment. An exact admissible action
    merely reserves one environment step and sets should_call_env=True.
    """

    if not isinstance(
        budget_limits,
        BudgetLimits,
    ):
        raise TypeError(
            "budget_limits must be BudgetLimits"
        )

    _require_process_precondition(
        precondition_result
    )

    if (
        budget_limits
        != precondition_result.budget_limits
    ):
        raise ValueError(
            "budget_limits do not match "
            "precondition_result.budget_limits"
        )

    # Preserve the exact immutable object frozen before the model call.
    budget_limits = (
        precondition_result.budget_limits
    )

    visible_commands = _validate_processing_menu(
        visible_admissible_commands=(
            visible_admissible_commands
        ),
        precondition_result=(
            precondition_result
        ),
        max_action_codepoints=(
            max_action_codepoints
        ),
    )

    budget_before = (
        precondition_result.budget_after
    )

    parse_result = parse_raw_policy_response(
        raw_response,
        max_action_codepoints=(
            max_action_codepoints
        ),
    )

    if parse_result.status is ParserStatus.FAILED:
        budget_after = apply_completed_attempt(
            budget_before,
            (
                BudgetAttemptOutcome
                .FORMAT_PROTOCOL_FAILURE
            ),
            budget_limits,
        )

        termination_reason = (
            resolve_nonexecuted_termination(
                budget_after,
                budget_limits,
            )
        )

        return RuntimeDecision(
            budget_before=budget_before,
            budget_limits=budget_limits,
            budget_after=budget_after,
            parse_result=parse_result,
            attempt_outcome=(
                AttemptOutcome
                .FORMAT_PROTOCOL_FAILURE
            ),
            failure_stage=(
                _map_parser_failure_stage(
                    parse_result.failure_stage
                )
            ),
            failure_code=(
                parse_result.failure_code
            ),
            normalized_action=None,
            admissibility_status=(
                AdmissibilityStatus
                .NOT_CHECKED
            ),
            feedback_code=(
                InterfaceFeedbackCode
                .FORMAT_ERROR_V1
            ),
            should_call_env=False,
            candidate_environment_action=None,
            termination_reason=(
                termination_reason
            ),
        )

    if parse_result.status is not ParserStatus.SUCCESS:
        raise AssertionError(
            "unknown parser status"
        )

    action = parse_result.normalized_action

    if action is None:
        raise AssertionError(
            "successful parser result has no action"
        )

    if action not in visible_commands:
        budget_after = apply_completed_attempt(
            budget_before,
            (
                BudgetAttemptOutcome
                .ACTION_NOT_ADMISSIBLE
            ),
            budget_limits,
        )

        termination_reason = (
            resolve_nonexecuted_termination(
                budget_after,
                budget_limits,
            )
        )

        return RuntimeDecision(
            budget_before=budget_before,
            budget_limits=budget_limits,
            budget_after=budget_after,
            parse_result=parse_result,
            attempt_outcome=(
                AttemptOutcome
                .ACTION_NOT_ADMISSIBLE
            ),
            failure_stage=(
                AttemptFailureStage
                .ADMISSIBILITY
            ),
            failure_code=(
                RuntimeFailureCode
                .ACTION_NOT_ADMISSIBLE
            ),
            normalized_action=action,
            admissibility_status=(
                AdmissibilityStatus
                .NOT_ADMISSIBLE
            ),
            feedback_code=(
                InterfaceFeedbackCode
                .INVALID_ACTION_V1
            ),
            should_call_env=False,
            candidate_environment_action=None,
            termination_reason=(
                termination_reason
            ),
        )

    budget_after = apply_completed_attempt(
        budget_before,
        BudgetAttemptOutcome.ACTION_EXECUTED,
        budget_limits,
    )

    return RuntimeDecision(
        budget_before=budget_before,
        budget_limits=budget_limits,
        budget_after=budget_after,
        parse_result=parse_result,
        attempt_outcome=(
            AttemptOutcome.ACTION_EXECUTED
        ),
        failure_stage=None,
        failure_code=None,
        normalized_action=action,
        admissibility_status=(
            AdmissibilityStatus.EXACT_MEMBER
        ),
        feedback_code=None,
        should_call_env=True,
        candidate_environment_action=action,
        termination_reason=None,
    )


def finalize_environment_result(
    decision: RuntimeDecision,
    *,
    environment_terminated: bool,
    infrastructure_error: bool,
) -> RuntimeDecision:
    """Finalize the result of one reserved environment action."""

    if not isinstance(
        decision,
        RuntimeDecision,
    ):
        raise TypeError(
            "decision must be RuntimeDecision"
        )

    if type(environment_terminated) is not bool:
        raise TypeError(
            "environment_terminated must be bool"
        )

    if type(infrastructure_error) is not bool:
        raise TypeError(
            "infrastructure_error must be bool"
        )

    if (
        decision.should_call_env is not True
        or decision
        .candidate_environment_action
        is None
        or decision.attempt_outcome
        is not AttemptOutcome.ACTION_EXECUTED
    ):
        raise ValueError(
            "decision does not authorize "
            "environment finalization"
        )

    termination_reason = (
        resolve_after_environment(
            decision.budget_after,
            decision.budget_limits,
            infrastructure_error=(
                infrastructure_error
            ),
            environment_terminated=(
                environment_terminated
            ),
        )
    )

    if infrastructure_error:
        return replace(
            decision,
            should_call_env=False,
            attempt_outcome=(
                AttemptOutcome
                .INFRASTRUCTURE_ERROR
            ),
            failure_stage=(
                AttemptFailureStage
                .INFRASTRUCTURE
            ),
            failure_code=(
                RuntimeFailureCode
                .ENVIRONMENT_STEP_FAILED
            ),
            termination_reason=(
                termination_reason
            ),
        )

    return replace(
        decision,
        should_call_env=False,
        termination_reason=termination_reason,
    )
