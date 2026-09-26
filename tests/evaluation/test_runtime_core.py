from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pchsi.evaluation.action_trace import (
    sha256_string_sequence,
)
from pchsi.evaluation.budget import (
    BudgetLimits,
    BudgetState,
    EpisodeTerminationReason,
)
from pchsi.evaluation.runtime_core import (
    MenuFailureCode,
    MenuValidationResult,
    ProtocolPreconditionResult,
    validate_menu_contract,
    validate_runtime_preconditions,
)


DEFAULT_LIMITS = BudgetLimits()

VALID_COMMANDS = (
    "look",
    "go to desk 1",
    "take pencil 1 from desk 1",
)


def _validate_identical_menus(
    commands: tuple[object, ...],
    *,
    max_action_codepoints: int = 256,
) -> MenuValidationResult:
    return validate_menu_contract(
        policy_visible_commands=commands,
        harness_visible_commands=commands,
        environment_commands=commands,
        max_action_codepoints=max_action_codepoints,
    )


def test_menu_failure_codes_are_exact() -> None:
    assert {
        item.name: item.value
        for item in MenuFailureCode
    } == {
        "POLICY_MENU_COUNT_MISMATCH": (
            "POLICY_MENU_COUNT_MISMATCH"
        ),
        "POLICY_MENU_SEQUENCE_MISMATCH": (
            "POLICY_MENU_SEQUENCE_MISMATCH"
        ),
        "HARNESS_MENU_COUNT_MISMATCH": (
            "HARNESS_MENU_COUNT_MISMATCH"
        ),
        "HARNESS_MENU_SEQUENCE_MISMATCH": (
            "HARNESS_MENU_SEQUENCE_MISMATCH"
        ),
        "MENU_COMMAND_NOT_STRING": (
            "MENU_COMMAND_NOT_STRING"
        ),
        "MENU_COMMAND_EMPTY": (
            "MENU_COMMAND_EMPTY"
        ),
        "MENU_COMMAND_BOUNDARY_SPACE": (
            "MENU_COMMAND_BOUNDARY_SPACE"
        ),
        "MENU_COMMAND_MULTILINE": (
            "MENU_COMMAND_MULTILINE"
        ),
        "MENU_COMMAND_CONTROL_CHARACTER": (
            "MENU_COMMAND_CONTROL_CHARACTER"
        ),
        "MENU_COMMAND_TOO_LONG": (
            "MENU_COMMAND_TOO_LONG"
        ),
    }


def test_menu_validation_result_is_immutable() -> None:
    result = MenuValidationResult(
        valid=True,
        failure_code=None,
        sequence_sha256="a" * 64,
    )

    with pytest.raises(FrozenInstanceError):
        result.valid = False  # type: ignore[misc]


def test_protocol_precondition_result_is_immutable() -> None:
    state = BudgetState()

    result = ProtocolPreconditionResult(
        menu_validation=MenuValidationResult(
            valid=True,
            failure_code=None,
            sequence_sha256="a" * 64,
        ),
        budget_before=state,
        budget_after=state,
        should_call_policy=True,
        termination_reason=None,
    )

    with pytest.raises(FrozenInstanceError):
        result.should_call_policy = False  # type: ignore[misc]


def test_identical_menus_are_valid_and_hash_exact_sequence(
) -> None:
    result = validate_menu_contract(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
    )

    assert result.valid is True
    assert result.failure_code is None
    assert result.sequence_sha256 == (
        sha256_string_sequence(
            VALID_COMMANDS
        )
    )


def test_duplicate_commands_are_not_deduplicated() -> None:
    commands = (
        "look",
        "go to desk 1",
        "look",
    )

    result = _validate_identical_menus(
        commands
    )

    assert result.valid is True
    assert result.sequence_sha256 == (
        sha256_string_sequence(commands)
    )


def test_policy_menu_count_mismatch_is_rejected() -> None:
    result = validate_menu_contract(
        policy_visible_commands=(
            "look",
            "go to desk 1",
        ),
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
    )

    assert result == MenuValidationResult(
        valid=False,
        failure_code=(
            MenuFailureCode
            .POLICY_MENU_COUNT_MISMATCH
        ),
        sequence_sha256=None,
    )


def test_policy_menu_order_mismatch_is_rejected() -> None:
    result = validate_menu_contract(
        policy_visible_commands=(
            "go to desk 1",
            "look",
            "take pencil 1 from desk 1",
        ),
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
    )

    assert result.valid is False
    assert result.failure_code is (
        MenuFailureCode
        .POLICY_MENU_SEQUENCE_MISMATCH
    )
    assert result.sequence_sha256 is None


def test_harness_menu_count_mismatch_is_rejected() -> None:
    result = validate_menu_contract(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=(
            "look",
            "go to desk 1",
        ),
        environment_commands=VALID_COMMANDS,
    )

    assert result.valid is False
    assert result.failure_code is (
        MenuFailureCode
        .HARNESS_MENU_COUNT_MISMATCH
    )
    assert result.sequence_sha256 is None


def test_harness_menu_order_mismatch_is_rejected() -> None:
    result = validate_menu_contract(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=(
            "look",
            "take pencil 1 from desk 1",
            "go to desk 1",
        ),
        environment_commands=VALID_COMMANDS,
    )

    assert result.valid is False
    assert result.failure_code is (
        MenuFailureCode
        .HARNESS_MENU_SEQUENCE_MISMATCH
    )
    assert result.sequence_sha256 is None


@pytest.mark.parametrize(
    (
        "commands",
        "expected_code",
    ),
    [
        (
            (123,),
            MenuFailureCode.MENU_COMMAND_NOT_STRING,
        ),
        (
            ("",),
            MenuFailureCode.MENU_COMMAND_EMPTY,
        ),
        (
            ("   ",),
            MenuFailureCode.MENU_COMMAND_BOUNDARY_SPACE,
        ),
        (
            (" look",),
            MenuFailureCode.MENU_COMMAND_BOUNDARY_SPACE,
        ),
        (
            ("look ",),
            MenuFailureCode.MENU_COMMAND_BOUNDARY_SPACE,
        ),
        (
            ("look\nnow",),
            MenuFailureCode.MENU_COMMAND_MULTILINE,
        ),
        (
            ("look\rnow",),
            MenuFailureCode.MENU_COMMAND_MULTILINE,
        ),
        (
            ("look\u0001",),
            (
                MenuFailureCode
                .MENU_COMMAND_CONTROL_CHARACTER
            ),
        ),
        (
            ("look\u007f",),
            (
                MenuFailureCode
                .MENU_COMMAND_CONTROL_CHARACTER
            ),
        ),
        (
            ("look\u0085",),
            (
                MenuFailureCode
                .MENU_COMMAND_CONTROL_CHARACTER
            ),
        ),
        (
            ("x" * 257,),
            MenuFailureCode.MENU_COMMAND_TOO_LONG,
        ),
    ],
)
def test_invalid_menu_command_shape_is_rejected(
    commands: tuple[object, ...],
    expected_code: MenuFailureCode,
) -> None:
    result = _validate_identical_menus(
        commands
    )

    assert result.valid is False
    assert result.failure_code is expected_code
    assert result.sequence_sha256 is None


def test_exactly_256_codepoint_command_is_valid() -> None:
    commands = (
        "x" * 256,
    )

    result = _validate_identical_menus(
        commands
    )

    assert result.valid is True
    assert result.failure_code is None


def test_custom_command_limit_is_enforced() -> None:
    result = _validate_identical_menus(
        ("look",),
        max_action_codepoints=3,
    )

    assert result.valid is False
    assert result.failure_code is (
        MenuFailureCode.MENU_COMMAND_TOO_LONG
    )


def test_invalid_menu_precondition_consumes_no_budget(
) -> None:
    state = BudgetState(
        policy_attempt_count=9,
        environment_step_count=4,
        protocol_failure_count=2,
        inadmissible_action_count=1,
        consecutive_nonexecuted_attempt_count=2,
    )

    result = validate_runtime_preconditions(
        policy_visible_commands=("look",),
        harness_visible_commands=("look",),
        environment_commands=(
            "look",
            "go to desk 1",
        ),
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert result.should_call_policy is False
    assert result.termination_reason is (
        EpisodeTerminationReason
        .PROTOCOL_CONFIGURATION_ERROR
    )
    assert result.budget_before is state
    assert result.budget_after is state
    assert result.budget_after == state

    assert result.menu_validation.valid is False
    assert result.menu_validation.failure_code is (
        MenuFailureCode
        .POLICY_MENU_COUNT_MISMATCH
    )


def test_valid_menu_with_exhausted_policy_budget_blocks_call(
) -> None:
    state = BudgetState(
        policy_attempt_count=60,
        environment_step_count=12,
    )

    result = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert result.menu_validation.valid is True
    assert result.should_call_policy is False
    assert result.termination_reason is (
        EpisodeTerminationReason
        .POLICY_ATTEMPT_BUDGET_EXHAUSTED
    )
    assert result.budget_before is state
    assert result.budget_after is state


def test_valid_menu_and_available_budget_allows_call(
) -> None:
    state = BudgetState(
        policy_attempt_count=59,
        environment_step_count=29,
    )

    result = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert result.menu_validation.valid is True
    assert result.menu_validation.failure_code is None
    assert result.menu_validation.sequence_sha256 == (
        sha256_string_sequence(
            VALID_COMMANDS
        )
    )

    assert result.should_call_policy is True
    assert result.termination_reason is None
    assert result.budget_before is state
    assert result.budget_after is state


def test_precondition_validation_never_mutates_state() -> None:
    state = BudgetState(
        policy_attempt_count=5,
        environment_step_count=3,
        protocol_failure_count=1,
        inadmissible_action_count=1,
        consecutive_nonexecuted_attempt_count=1,
    )

    before = state

    validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert state is before
    assert state == before


# ---------------------------------------------------------------------------
# Task 4B: completed generation processing and environment finalization
# ---------------------------------------------------------------------------

from pchsi.evaluation.raw_policy_parser import (
    ParserFailureCode,
    ParserStatus,
)
from pchsi.evaluation.raw_policy_prompt import (
    InterfaceFeedbackCode,
)
from pchsi.evaluation.runtime_core import (
    AdmissibilityStatus,
    AttemptFailureStage,
    AttemptOutcome,
    RuntimeDecision,
    RuntimeFailureCode,
    finalize_environment_result,
    process_completed_generation,
)


def _valid_precondition(
    state: BudgetState | None = None,
) -> ProtocolPreconditionResult:
    if state is None:
        state = BudgetState()

    result = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert result.should_call_policy is True
    assert result.termination_reason is None

    return result


def _exact_action_decision(
    *,
    state: BudgetState | None = None,
    action: str = "look",
) -> RuntimeDecision:
    return process_completed_generation(
        raw_response=(
            '{"action":"' + action + '"}'
        ),
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=_valid_precondition(
            state
        ),
        budget_limits=DEFAULT_LIMITS,
    )


def test_runtime_enums_are_exact() -> None:
    assert {
        item.name: item.value
        for item in AttemptOutcome
    } == {
        "ACTION_EXECUTED": "ACTION_EXECUTED",
        "FORMAT_PROTOCOL_FAILURE": (
            "FORMAT_PROTOCOL_FAILURE"
        ),
        "ACTION_NOT_ADMISSIBLE": (
            "ACTION_NOT_ADMISSIBLE"
        ),
        "INFRASTRUCTURE_ERROR": (
            "INFRASTRUCTURE_ERROR"
        ),
    }

    assert {
        item.name: item.value
        for item in AdmissibilityStatus
    } == {
        "NOT_CHECKED": "not_checked",
        "EXACT_MEMBER": "exact_member",
        "NOT_ADMISSIBLE": "not_admissible",
    }

    assert {
        item.name: item.value
        for item in AttemptFailureStage
    } == {
        "ENVELOPE": "envelope",
        "ACTION_NORMALIZATION": (
            "action_normalization"
        ),
        "ADMISSIBILITY": "admissibility",
        "INFRASTRUCTURE": "infrastructure",
    }

    assert {
        item.name: item.value
        for item in RuntimeFailureCode
    } == {
        "ACTION_NOT_ADMISSIBLE": (
            "ACTION_NOT_ADMISSIBLE"
        ),
        "ENVIRONMENT_STEP_FAILED": (
            "ENVIRONMENT_STEP_FAILED"
        ),
    }


def test_runtime_decision_is_immutable() -> None:
    decision = _exact_action_decision()

    with pytest.raises(FrozenInstanceError):
        decision.should_call_env = False  # type: ignore[misc]


def test_process_requires_approved_precondition() -> None:
    state = BudgetState()

    blocked = validate_runtime_preconditions(
        policy_visible_commands=("look",),
        harness_visible_commands=("look",),
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert blocked.should_call_policy is False

    with pytest.raises(
        ValueError,
        match="precondition",
    ):
        process_completed_generation(
            raw_response='{"action":"look"}',
            visible_admissible_commands=VALID_COMMANDS,
            precondition_result=blocked,
            budget_limits=DEFAULT_LIMITS,
        )

    assert blocked.budget_after is state


def test_process_rejects_menu_hash_drift() -> None:
    state = BudgetState()

    precondition = _valid_precondition(
        state
    )

    with pytest.raises(
        ValueError,
        match="menu",
    ):
        process_completed_generation(
            raw_response='{"action":"look"}',
            visible_admissible_commands=(
                "look",
                "go to desk 2",
            ),
            precondition_result=precondition,
            budget_limits=DEFAULT_LIMITS,
        )

    assert state == BudgetState()


def test_envelope_failure_is_attributed_exactly() -> None:
    state = BudgetState(
        policy_attempt_count=4,
        environment_step_count=2,
        consecutive_nonexecuted_attempt_count=1,
    )

    decision = process_completed_generation(
        raw_response="explanation only",
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=_valid_precondition(
            state
        ),
        budget_limits=DEFAULT_LIMITS,
    )

    assert decision.budget_before is state
    assert decision.budget_after == BudgetState(
        policy_attempt_count=5,
        environment_step_count=2,
        protocol_failure_count=1,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=2,
    )

    assert decision.parse_result.status is (
        ParserStatus.FAILED
    )
    assert decision.parse_result.failure_code is (
        ParserFailureCode.ENVELOPE_INVALID_JSON
    )

    assert decision.attempt_outcome is (
        AttemptOutcome.FORMAT_PROTOCOL_FAILURE
    )
    assert decision.failure_stage is (
        AttemptFailureStage.ENVELOPE
    )
    assert decision.failure_code is (
        ParserFailureCode.ENVELOPE_INVALID_JSON
    )
    assert decision.normalized_action is None
    assert decision.admissibility_status is (
        AdmissibilityStatus.NOT_CHECKED
    )
    assert decision.feedback_code is (
        InterfaceFeedbackCode.FORMAT_ERROR_V1
    )
    assert decision.should_call_env is False
    assert decision.candidate_environment_action is None
    assert decision.termination_reason is None


def test_action_normalization_failure_is_attributed_exactly(
) -> None:
    decision = process_completed_generation(
        raw_response='{"action":"   "}',
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=_valid_precondition(),
        budget_limits=DEFAULT_LIMITS,
    )

    assert decision.attempt_outcome is (
        AttemptOutcome.FORMAT_PROTOCOL_FAILURE
    )
    assert decision.failure_stage is (
        AttemptFailureStage.ACTION_NORMALIZATION
    )
    assert decision.failure_code is (
        ParserFailureCode.ACTION_EMPTY
    )
    assert decision.admissibility_status is (
        AdmissibilityStatus.NOT_CHECKED
    )
    assert decision.feedback_code is (
        InterfaceFeedbackCode.FORMAT_ERROR_V1
    )


def test_case_only_mismatch_remains_inadmissible() -> None:
    state = BudgetState(
        policy_attempt_count=8,
        environment_step_count=3,
        inadmissible_action_count=2,
        consecutive_nonexecuted_attempt_count=1,
    )

    decision = process_completed_generation(
        raw_response='{"action":"LOOK"}',
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=_valid_precondition(
            state
        ),
        budget_limits=DEFAULT_LIMITS,
    )

    assert decision.parse_result.status is (
        ParserStatus.SUCCESS
    )
    assert decision.parse_result.failure_code is None
    assert decision.normalized_action == "LOOK"

    assert decision.attempt_outcome is (
        AttemptOutcome.ACTION_NOT_ADMISSIBLE
    )
    assert decision.failure_stage is (
        AttemptFailureStage.ADMISSIBILITY
    )
    assert decision.failure_code is (
        RuntimeFailureCode.ACTION_NOT_ADMISSIBLE
    )
    assert decision.admissibility_status is (
        AdmissibilityStatus.NOT_ADMISSIBLE
    )
    assert decision.feedback_code is (
        InterfaceFeedbackCode.INVALID_ACTION_V1
    )
    assert decision.should_call_env is False
    assert decision.candidate_environment_action is None

    assert decision.budget_after == BudgetState(
        policy_attempt_count=9,
        environment_step_count=3,
        protocol_failure_count=0,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=2,
    )


def test_near_match_is_not_repaired() -> None:
    decision = process_completed_generation(
        raw_response='{"action":"go to desk"}',
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=_valid_precondition(),
        budget_limits=DEFAULT_LIMITS,
    )

    assert decision.normalized_action == (
        "go to desk"
    )
    assert decision.attempt_outcome is (
        AttemptOutcome.ACTION_NOT_ADMISSIBLE
    )
    assert decision.should_call_env is False


def test_exact_member_reserves_environment_step() -> None:
    state = BudgetState(
        policy_attempt_count=10,
        environment_step_count=4,
        protocol_failure_count=2,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=2,
    )

    decision = _exact_action_decision(
        state=state,
        action="go to desk 1",
    )

    assert decision.parse_result.status is (
        ParserStatus.SUCCESS
    )
    assert decision.attempt_outcome is (
        AttemptOutcome.ACTION_EXECUTED
    )
    assert decision.failure_stage is None
    assert decision.failure_code is None
    assert decision.normalized_action == (
        "go to desk 1"
    )
    assert decision.admissibility_status is (
        AdmissibilityStatus.EXACT_MEMBER
    )
    assert decision.feedback_code is None
    assert decision.should_call_env is True
    assert decision.candidate_environment_action == (
        "go to desk 1"
    )
    assert decision.termination_reason is None

    assert decision.budget_after == BudgetState(
        policy_attempt_count=11,
        environment_step_count=5,
        protocol_failure_count=2,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=0,
    )


def test_third_mixed_nonexecuted_attempt_terminates() -> None:
    state = BudgetState(
        policy_attempt_count=59,
        environment_step_count=12,
        protocol_failure_count=4,
        inadmissible_action_count=3,
        consecutive_nonexecuted_attempt_count=2,
    )

    decision = process_completed_generation(
        raw_response='{"action":"off list"}',
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=_valid_precondition(
            state
        ),
        budget_limits=DEFAULT_LIMITS,
    )

    assert decision.budget_after.policy_attempt_count == 60
    assert (
        decision.budget_after
        .consecutive_nonexecuted_attempt_count
        == 3
    )
    assert decision.termination_reason is (
        EpisodeTerminationReason
        .CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
    )


def test_parser_failure_at_attempt_sixty_resolves_policy_budget(
) -> None:
    state = BudgetState(
        policy_attempt_count=59,
        consecutive_nonexecuted_attempt_count=0,
    )

    decision = process_completed_generation(
        raw_response="bad response",
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=_valid_precondition(
            state
        ),
        budget_limits=DEFAULT_LIMITS,
    )

    assert decision.budget_after.policy_attempt_count == 60
    assert decision.termination_reason is (
        EpisodeTerminationReason
        .POLICY_ATTEMPT_BUDGET_EXHAUSTED
    )


def test_environment_success_without_termination_keeps_episode_open(
) -> None:
    decision = _exact_action_decision(
        state=BudgetState(
            policy_attempt_count=4,
            environment_step_count=2,
        ),
    )

    finalized = finalize_environment_result(
        decision,
        environment_terminated=False,
        infrastructure_error=False,
    )

    assert finalized.attempt_outcome is (
        AttemptOutcome.ACTION_EXECUTED
    )
    assert finalized.failure_stage is None
    assert finalized.failure_code is None
    assert finalized.termination_reason is None
    assert finalized.budget_after == (
        decision.budget_after
    )


def test_environment_termination_is_recorded() -> None:
    decision = _exact_action_decision()

    finalized = finalize_environment_result(
        decision,
        environment_terminated=True,
        infrastructure_error=False,
    )

    assert finalized.attempt_outcome is (
        AttemptOutcome.ACTION_EXECUTED
    )
    assert finalized.termination_reason is (
        EpisodeTerminationReason
        .ENVIRONMENT_TERMINATED
    )


def test_environment_step_thirty_terminates_by_environment_budget(
) -> None:
    decision = _exact_action_decision(
        state=BudgetState(
            policy_attempt_count=29,
            environment_step_count=29,
        ),
    )

    assert (
        decision.budget_after.environment_step_count
        == 30
    )

    finalized = finalize_environment_result(
        decision,
        environment_terminated=False,
        infrastructure_error=False,
    )

    assert finalized.termination_reason is (
        EpisodeTerminationReason
        .ENVIRONMENT_STEP_BUDGET_EXHAUSTED
    )


def test_policy_sixty_after_environment_uses_policy_budget(
) -> None:
    decision = _exact_action_decision(
        state=BudgetState(
            policy_attempt_count=59,
            environment_step_count=10,
        ),
    )

    finalized = finalize_environment_result(
        decision,
        environment_terminated=False,
        infrastructure_error=False,
    )

    assert finalized.termination_reason is (
        EpisodeTerminationReason
        .POLICY_ATTEMPT_BUDGET_EXHAUSTED
    )


def test_infrastructure_error_keeps_reserved_step_consumed(
) -> None:
    decision = _exact_action_decision(
        state=BudgetState(
            policy_attempt_count=7,
            environment_step_count=5,
        ),
        action="go to desk 1",
    )

    finalized = finalize_environment_result(
        decision,
        environment_terminated=True,
        infrastructure_error=True,
    )

    assert finalized.attempt_outcome is (
        AttemptOutcome.INFRASTRUCTURE_ERROR
    )
    assert finalized.failure_stage is (
        AttemptFailureStage.INFRASTRUCTURE
    )
    assert finalized.failure_code is (
        RuntimeFailureCode.ENVIRONMENT_STEP_FAILED
    )
    assert finalized.termination_reason is (
        EpisodeTerminationReason.INFRASTRUCTURE_ERROR
    )

    assert finalized.should_call_env is False
    assert finalized.candidate_environment_action == (
        "go to desk 1"
    )
    assert (
        finalized.budget_after.policy_attempt_count
        == 8
    )
    assert (
        finalized.budget_after.environment_step_count
        == 6
    )


def test_nonexecuted_decision_cannot_be_environment_finalized(
) -> None:
    decision = process_completed_generation(
        raw_response="bad response",
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=_valid_precondition(),
        budget_limits=DEFAULT_LIMITS,
    )

    assert decision.should_call_env is False

    with pytest.raises(
        ValueError,
        match="environment",
    ):
        finalize_environment_result(
            decision,
            environment_terminated=False,
            infrastructure_error=False,
        )


@pytest.mark.parametrize(
    (
        "environment_terminated",
        "infrastructure_error",
        "expected_name",
    ),
    [
        (
            1,
            False,
            "environment_terminated",
        ),
        (
            False,
            0,
            "infrastructure_error",
        ),
    ],
)
def test_environment_result_flags_require_bool(
    environment_terminated: object,
    infrastructure_error: object,
    expected_name: str,
) -> None:
    decision = _exact_action_decision()

    with pytest.raises(
        TypeError,
        match=expected_name,
    ):
        finalize_environment_result(
            decision,
            environment_terminated=(
                environment_terminated  # type: ignore[arg-type]
            ),
            infrastructure_error=(
                infrastructure_error  # type: ignore[arg-type]
            ),
        )


# ---------------------------------------------------------------------------
# Task 4 blocking correction: custom budget-limit lineage
# ---------------------------------------------------------------------------


def test_precondition_preserves_custom_budget_limits() -> None:
    limits = BudgetLimits(
        max_policy_attempts=2,
        max_environment_steps=1,
        max_consecutive_nonexecuted_attempts=2,
    )

    result = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=BudgetState(),
        budget_limits=limits,
    )

    assert result.should_call_policy is True
    assert result.budget_limits is limits


def test_process_rejects_budget_limit_drift_from_precondition(
) -> None:
    frozen_limits = BudgetLimits(
        max_policy_attempts=2,
        max_environment_steps=1,
        max_consecutive_nonexecuted_attempts=2,
    )

    precondition = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=BudgetState(),
        budget_limits=frozen_limits,
    )

    with pytest.raises(
        ValueError,
        match="budget_limits",
    ):
        process_completed_generation(
            raw_response='{"action":"look"}',
            visible_admissible_commands=VALID_COMMANDS,
            precondition_result=precondition,
            budget_limits=BudgetLimits(),
        )


def test_runtime_decision_preserves_custom_budget_limits(
) -> None:
    limits = BudgetLimits(
        max_policy_attempts=2,
        max_environment_steps=1,
        max_consecutive_nonexecuted_attempts=2,
    )

    precondition = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=BudgetState(),
        budget_limits=limits,
    )

    decision = process_completed_generation(
        raw_response='{"action":"look"}',
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=precondition,
        budget_limits=limits,
    )

    assert decision.budget_limits is limits


def test_finalize_uses_custom_environment_step_limit(
) -> None:
    limits = BudgetLimits(
        max_policy_attempts=5,
        max_environment_steps=1,
        max_consecutive_nonexecuted_attempts=2,
    )

    precondition = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=BudgetState(),
        budget_limits=limits,
    )

    decision = process_completed_generation(
        raw_response='{"action":"look"}',
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=precondition,
        budget_limits=limits,
    )

    assert decision.budget_after.environment_step_count == 1

    finalized = finalize_environment_result(
        decision,
        environment_terminated=False,
        infrastructure_error=False,
    )

    assert finalized.termination_reason is (
        EpisodeTerminationReason
        .ENVIRONMENT_STEP_BUDGET_EXHAUSTED
    )


def test_finalize_uses_custom_policy_attempt_limit(
) -> None:
    limits = BudgetLimits(
        max_policy_attempts=1,
        max_environment_steps=5,
        max_consecutive_nonexecuted_attempts=2,
    )

    precondition = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=BudgetState(),
        budget_limits=limits,
    )

    decision = process_completed_generation(
        raw_response='{"action":"look"}',
        visible_admissible_commands=VALID_COMMANDS,
        precondition_result=precondition,
        budget_limits=limits,
    )

    assert decision.budget_after.policy_attempt_count == 1

    finalized = finalize_environment_result(
        decision,
        environment_terminated=False,
        infrastructure_error=False,
    )

    assert finalized.termination_reason is (
        EpisodeTerminationReason
        .POLICY_ATTEMPT_BUDGET_EXHAUSTED
    )


# ---------------------------------------------------------------------------
# Task 4 finalization boundary: returned results remove environment authorization
# ---------------------------------------------------------------------------


def test_successful_finalized_result_removes_environment_authorization(
) -> None:
    decision = _exact_action_decision(
        action="go to desk 1",
    )

    assert decision.should_call_env is True

    finalized = finalize_environment_result(
        decision,
        environment_terminated=False,
        infrastructure_error=False,
    )

    assert finalized is not decision
    assert finalized.should_call_env is False

    # Preserve the selected action for later trace construction, but
    # do not retain permission to call the environment again.
    assert finalized.candidate_environment_action == (
        "go to desk 1"
    )

    # The original immutable pre-environment decision is unchanged.
    # The evaluator lifecycle must not reuse this authorization.
    assert decision.should_call_env is True


def test_infrastructure_finalized_result_removes_environment_authorization(
) -> None:
    decision = _exact_action_decision(
        action="go to desk 1",
    )

    finalized = finalize_environment_result(
        decision,
        environment_terminated=False,
        infrastructure_error=True,
    )

    assert finalized.attempt_outcome is (
        AttemptOutcome.INFRASTRUCTURE_ERROR
    )
    assert finalized.should_call_env is False
    assert finalized.candidate_environment_action == (
        "go to desk 1"
    )


def test_finalized_result_cannot_be_finalized_again(
) -> None:
    decision = _exact_action_decision()

    finalized = finalize_environment_result(
        decision,
        environment_terminated=False,
        infrastructure_error=False,
    )

    assert finalized.should_call_env is False

    with pytest.raises(
        ValueError,
        match="environment",
    ):
        finalize_environment_result(
            finalized,
            environment_terminated=False,
            infrastructure_error=False,
        )


# ---------------------------------------------------------------------------
# Post-review correction: terminal budget states must close the policy gate
# ---------------------------------------------------------------------------


def test_environment_step_exhaustion_blocks_next_policy_call(
) -> None:
    state = BudgetState(
        policy_attempt_count=30,
        environment_step_count=30,
    )

    result = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert result.menu_validation.valid is True
    assert result.should_call_policy is False
    assert result.termination_reason is (
        EpisodeTerminationReason
        .ENVIRONMENT_STEP_BUDGET_EXHAUSTED
    )
    assert result.budget_before is state
    assert result.budget_after is state


def test_consecutive_nonexecuted_exhaustion_blocks_next_policy_call(
) -> None:
    state = BudgetState(
        policy_attempt_count=3,
        consecutive_nonexecuted_attempt_count=3,
    )

    result = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert result.menu_validation.valid is True
    assert result.should_call_policy is False
    assert result.termination_reason is (
        EpisodeTerminationReason
        .CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
    )
    assert result.budget_before is state
    assert result.budget_after is state


def test_precondition_environment_budget_precedes_other_limits(
) -> None:
    state = BudgetState(
        policy_attempt_count=60,
        environment_step_count=30,
        consecutive_nonexecuted_attempt_count=3,
    )

    result = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert result.should_call_policy is False
    assert result.termination_reason is (
        EpisodeTerminationReason
        .ENVIRONMENT_STEP_BUDGET_EXHAUSTED
    )


def test_precondition_consecutive_limit_precedes_policy_limit(
) -> None:
    state = BudgetState(
        policy_attempt_count=60,
        environment_step_count=29,
        consecutive_nonexecuted_attempt_count=3,
    )

    result = validate_runtime_preconditions(
        policy_visible_commands=VALID_COMMANDS,
        harness_visible_commands=VALID_COMMANDS,
        environment_commands=VALID_COMMANDS,
        budget_state=state,
        budget_limits=DEFAULT_LIMITS,
    )

    assert result.should_call_policy is False
    assert result.termination_reason is (
        EpisodeTerminationReason
        .CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED
    )
