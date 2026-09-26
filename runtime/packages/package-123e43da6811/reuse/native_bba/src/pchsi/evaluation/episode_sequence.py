"""Deterministic cross-trace validation for one E1 episode attempt."""

from __future__ import annotations

from dataclasses import dataclass
import json

from .action_trace import (
    ActionTrace,
    ExecutionStatus,
)
from .budget import BudgetState
from .raw_policy_prompt import (
    ExecutedTransition,
    FORMAT_ERROR_V1,
    INVALID_ACTION_V1,
    InterfaceFeedbackCode,
    build_raw_policy_prompt,
    canonical_executed_transitions_json,
    sha256_executed_transitions,
)
from .schema_models import PublicTransitionRecordV1


class EpisodeSequenceError(ValueError):
    """The first deterministic cross-record invariant failure."""

    def __init__(self, code: str) -> None:
        if not isinstance(code, str) or not code:
            raise ValueError(
                "EpisodeSequenceError code must be non-empty"
            )
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EpisodeSequenceInput:
    traces: tuple[ActionTrace, ...]
    public_transitions: tuple[
        PublicTransitionRecordV1,
        ...
    ]
    final_budget: BudgetState
    final_success: bool | None
    final_done: bool | None
    final_won: bool | None
    termination_reason: str

    def __post_init__(self) -> None:
        if any(
            not isinstance(trace, ActionTrace)
            for trace in self.traces
        ):
            raise TypeError(
                "traces must contain ActionTrace"
            )
        if any(
            not isinstance(
                transition,
                PublicTransitionRecordV1,
            )
            for transition in self.public_transitions
        ):
            raise TypeError(
                "public_transitions must contain "
                "PublicTransitionRecordV1"
            )
        if not isinstance(
            self.final_budget,
            BudgetState,
        ):
            raise TypeError(
                "final_budget must be BudgetState"
            )
        for name in (
            "final_success",
            "final_done",
            "final_won",
        ):
            value = getattr(self, name)
            if value is not None and type(value) is not bool:
                raise TypeError(
                    f"{name} must be bool or None"
                )
        if (
            not isinstance(
                self.termination_reason,
                str,
            )
            or not self.termination_reason
        ):
            raise ValueError(
                "termination_reason must be non-empty"
            )


@dataclass(frozen=True, slots=True)
class EpisodeSequenceReport:
    model_call_count: int
    environment_call_trace_count: int
    public_transition_count: int
    final_environment_step_count: int
    valid: bool


def _fail(code: str) -> None:
    raise EpisodeSequenceError(code)


def _trace_budget_before(
    trace: ActionTrace,
) -> BudgetState:
    values = (
        trace.policy_attempt_count_before,
        trace.environment_step_count_before,
        trace.protocol_failure_count_before,
        trace.inadmissible_action_count_before,
        (
            trace
            .consecutive_nonexecuted_attempt_count_before
        ),
    )
    if any(value is None for value in values):
        _fail("TRACE_BUDGET_BEFORE_INCOMPLETE")
    return BudgetState(
        policy_attempt_count=values[0],
        environment_step_count=values[1],
        protocol_failure_count=values[2],
        inadmissible_action_count=values[3],
        consecutive_nonexecuted_attempt_count=(
            values[4]
        ),
    )


def _trace_budget_after(
    trace: ActionTrace,
) -> BudgetState:
    values = (
        trace.policy_attempt_count_after,
        trace.environment_step_count_after,
        trace.protocol_failure_count,
        trace.inadmissible_action_count,
        trace.consecutive_nonexecuted_attempt_count,
    )
    if any(value is None for value in values):
        _fail("TRACE_BUDGET_AFTER_INCOMPLETE")
    return BudgetState(
        policy_attempt_count=values[0],
        environment_step_count=values[1],
        protocol_failure_count=values[2],
        inadmissible_action_count=values[3],
        consecutive_nonexecuted_attempt_count=(
            values[4]
        ),
    )


def _constant_provenance(
    trace: ActionTrace,
) -> tuple[object, ...]:
    value = trace.provenance
    return (
        value.run_id,
        value.task_id,
        value.episode_id,
        value.replicate_id,
        value.arm_id,
        value.code_commit,
        value.config_sha256,
        value.provider,
        value.model_name,
        value.model_version,
        value.retry_count,
        value.split_and_access_version,
        value.split_name,
        value.access_mode,
        value.policy_version,
        value.seed,
        value.memory_version,
    )


def _feedback(
    value: str | None,
) -> InterfaceFeedbackCode | None:
    if value is None:
        return None
    try:
        return InterfaceFeedbackCode(value)
    except ValueError:
        _fail("FEEDBACK_CODE_INVALID")



_MEMORY_M0_VERSION = "MEMORY_M0_V1"
_PERSISTENT_MEMORY_VERSION = "PERSISTENT_FAILURE_EXPERIENCE_V1"
_MEMORY_PROMPT_ID = "MEMORY_AUGMENTED_RAW_POLICY_PROMPT_V1"
_MEMORY_LINE_PREFIX = "RETRIEVED_FAILURE_EXPERIENCES_JSON="
_OUTPUT_REQUIREMENT = '{"action":"<command>"}'


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _feedback_text(
    value: InterfaceFeedbackCode | None,
) -> str | None:
    if value is None:
        return None
    if value is InterfaceFeedbackCode.FORMAT_ERROR_V1:
        return FORMAT_ERROR_V1
    if value is InterfaceFeedbackCode.INVALID_ACTION_V1:
        return INVALID_ACTION_V1
    _fail("FEEDBACK_CODE_INVALID")


def _validate_memory_augmented_prompt(
    *,
    prompt_text: str,
    public_task_goal: str,
    observation: str,
    executed_history: tuple[ExecutedTransition, ...],
    admissible_commands: tuple[str, ...],
    interface_feedback: InterfaceFeedbackCode | None,
) -> None:
    lines = prompt_text.splitlines()
    if len(lines) != 8:
        _fail("MEMORY_AUGMENTED_PROMPT_LINE_COUNT")

    expected = (
        _MEMORY_PROMPT_ID,
        "TASK_GOAL_JSON=" + _canonical_json(public_task_goal),
        "CURRENT_OBSERVATION_JSON=" + _canonical_json(observation),
        (
            "EXECUTED_TRANSITIONS_JSON="
            + canonical_executed_transitions_json(executed_history)
        ),
        None,
        (
            "VISIBLE_ADMISSIBLE_COMMANDS_JSON="
            + _canonical_json(admissible_commands)
        ),
        (
            "INTERFACE_FEEDBACK_JSON="
            + _canonical_json(_feedback_text(interface_feedback))
        ),
        "OUTPUT_REQUIREMENT=" + _OUTPUT_REQUIREMENT,
    )

    for index, expected_line in enumerate(expected):
        if index == 4:
            continue
        if lines[index] != expected_line:
            _fail("PROMPT_OR_FEEDBACK_CONTINUITY_FAILURE")

    memory_line = lines[4]
    if not memory_line.startswith(_MEMORY_LINE_PREFIX):
        _fail("MEMORY_AUGMENTED_PROMPT_MEMORY_FIELD")
    raw_payload = memory_line[len(_MEMORY_LINE_PREFIX):]
    try:
        payload = json.loads(raw_payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        _fail("MEMORY_AUGMENTED_PROMPT_MEMORY_JSON")

    if (
        not isinstance(payload, list)
        or len(payload) > 1
        or any(not isinstance(item, dict) for item in payload)
    ):
        _fail("MEMORY_AUGMENTED_PROMPT_MEMORY_SHAPE")
    try:
        canonical_payload = _canonical_json(payload)
    except (TypeError, ValueError):
        _fail("MEMORY_AUGMENTED_PROMPT_MEMORY_JSON")
    if raw_payload != canonical_payload:
        _fail("MEMORY_AUGMENTED_PROMPT_MEMORY_CANONICALIZATION")


def _validate_transition(
    *,
    trace: ActionTrace,
    transition: PublicTransitionRecordV1,
) -> None:
    if (
        transition.execution_attempt_id
        != trace.provenance.episode_id
    ):
        _fail("TRANSITION_ATTEMPT_ID_MISMATCH")
    if (
        transition.model_call_index
        != trace.model_call_index
    ):
        _fail("TRANSITION_MODEL_INDEX_MISMATCH")
    if (
        transition.environment_step_index
        != trace.environment_step_index
    ):
        _fail("TRANSITION_ENVIRONMENT_INDEX_MISMATCH")
    if (
        transition.submitted_action
        != trace.submitted_environment_action
    ):
        _fail("TRANSITION_ACTION_MISMATCH")
    if (
        transition.pre_action_observation
        != trace.observation
        or transition.pre_action_observation_sha256
        != trace.observation_sha256
    ):
        _fail("TRANSITION_PRE_OBSERVATION_MISMATCH")
    if (
        transition.pre_action_admissible_commands
        != trace.admissible_commands
        or (
            transition
            .pre_action_admissible_commands_sha256
            != trace.admissible_commands_sha256
        )
    ):
        _fail("TRANSITION_PRE_MENU_MISMATCH")
    if (
        transition.resulting_observation
        != trace.resulting_observation
        or (
            transition.resulting_observation_sha256
            != trace.resulting_observation_sha256
        )
    ):
        _fail("TRANSITION_RESULT_OBSERVATION_MISMATCH")


def _validate_final_state(
    value: EpisodeSequenceInput,
) -> None:
    reason = value.termination_reason

    if reason == "ENVIRONMENT_TERMINATED":
        if value.final_done is not True:
            _fail("FINAL_ENVIRONMENT_DONE_REQUIRED")
        if type(value.final_won) is not bool:
            _fail("FINAL_ENVIRONMENT_WON_REQUIRED")
        if value.final_success is not value.final_won:
            _fail("FINAL_SUCCESS_WON_MISMATCH")
        return

    if reason == "INFRASTRUCTURE_ERROR":
        if (
            value.final_success is not None
            or value.final_done is not None
            or value.final_won is not None
        ):
            _fail("FINAL_INFRASTRUCTURE_PUBLIC_RESULT_PRESENT")
        return

    if (
        value.final_success is not False
        or value.final_done is not False
        or value.final_won is not False
    ):
        _fail("FINAL_NONENVIRONMENT_STATUS_MISMATCH")


def validate_episode_sequence(
    value: EpisodeSequenceInput,
) -> EpisodeSequenceReport:
    if not isinstance(
        value,
        EpisodeSequenceInput,
    ):
        raise TypeError(
            "value must be EpisodeSequenceInput"
        )

    traces = value.traces
    transitions = value.public_transitions

    if not traces:
        if transitions:
            _fail("TRANSITION_WITHOUT_TRACE")
        if value.final_budget != BudgetState():
            _fail("EMPTY_SEQUENCE_FINAL_BUDGET")
        _validate_final_state(value)
        return EpisodeSequenceReport(
            model_call_count=0,
            environment_call_trace_count=0,
            public_transition_count=0,
            final_environment_step_count=0,
            valid=True,
        )

    constant = _constant_provenance(
        traces[0]
    )
    task_goal = traces[0].public_task_goal
    current_observation = traces[0].observation
    current_menu = traces[0].admissible_commands
    expected_budget = BudgetState()
    pending_feedback: (
        InterfaceFeedbackCode | None
    ) = None
    executed_history: list[
        ExecutedTransition
    ] = []
    transition_cursor = 0
    environment_call_count = 0

    scheduled_cell_id: str | None = None

    for index, trace in enumerate(traces):
        if trace.model_call_index != index:
            _fail("MODEL_CALL_INDEX_DISCONTINUITY")
        if _constant_provenance(trace) != constant:
            _fail("PROVENANCE_DISCONTINUITY")
        if trace.public_task_goal != task_goal:
            _fail("TASK_GOAL_DISCONTINUITY")

        before = _trace_budget_before(trace)
        after = _trace_budget_after(trace)
        if before != expected_budget:
            _fail("BUDGET_CONTINUITY_FAILURE")

        if trace.observation != current_observation:
            _fail("OBSERVATION_CONTINUITY_FAILURE")
        if trace.admissible_commands != current_menu:
            _fail("MENU_CONTINUITY_FAILURE")

        memory_version = trace.provenance.memory_version

        if memory_version == _MEMORY_M0_VERSION:
            expected_memory_sha256 = (
                sha256_executed_transitions(
                    tuple(executed_history)
                )
            )
            if (
                trace.provenance.memory_state_sha256
                != expected_memory_sha256
            ):
                _fail("MEMORY_M0_CONTINUITY_FAILURE")

            expected_prompt = build_raw_policy_prompt(
                public_task_goal=task_goal,
                observation=current_observation,
                executed_transitions=tuple(
                    executed_history
                ),
                admissible_commands=current_menu,
                interface_feedback=pending_feedback,
            )
            if trace.prompt_text != expected_prompt:
                _fail("PROMPT_OR_FEEDBACK_CONTINUITY_FAILURE")

        elif memory_version == _PERSISTENT_MEMORY_VERSION:
            snapshot_sha256 = (
                traces[0].provenance.memory_state_sha256
            )
            if snapshot_sha256 is None:
                _fail("MEMORY_SNAPSHOT_MISSING")
            if (
                trace.provenance.memory_state_sha256
                != snapshot_sha256
            ):
                _fail("MEMORY_SNAPSHOT_CONTINUITY_FAILURE")
            _validate_memory_augmented_prompt(
                prompt_text=trace.prompt_text,
                public_task_goal=task_goal,
                observation=current_observation,
                executed_history=tuple(executed_history),
                admissible_commands=current_menu,
                interface_feedback=pending_feedback,
            )

        else:
            _fail("MEMORY_VERSION_UNSUPPORTED")

        if (
            index < len(traces) - 1
            and trace.episode_termination_reason
            is not None
        ):
            _fail("EARLY_TERMINATION_REASON")

        if trace.execution_status in {
            ExecutionStatus.EXECUTED,
            ExecutionStatus.ENVIRONMENT_ERROR,
        }:
            if (
                trace.environment_step_index
                != environment_call_count
            ):
                _fail("ENVIRONMENT_STEP_INDEX_DISCONTINUITY")
            environment_call_count += 1
        elif trace.environment_step_index is not None:
            _fail("NONEXECUTED_ENVIRONMENT_STEP_INDEX")

        if (
            trace.execution_status
            is ExecutionStatus.EXECUTED
        ):
            if transition_cursor >= len(transitions):
                _fail("MISSING_PUBLIC_TRANSITION")
            transition = transitions[
                transition_cursor
            ]
            _validate_transition(
                trace=trace,
                transition=transition,
            )
            if scheduled_cell_id is None:
                scheduled_cell_id = (
                    transition.scheduled_cell_id
                )
            elif (
                transition.scheduled_cell_id
                != scheduled_cell_id
            ):
                _fail("TRANSITION_CELL_ID_DISCONTINUITY")

            if (
                trace.submitted_environment_action
                is None
                or trace.resulting_observation
                is None
            ):
                _fail("EXECUTED_TRACE_PUBLIC_RESULT_MISSING")

            executed_history.append(
                ExecutedTransition(
                    action=(
                        trace
                        .submitted_environment_action
                    ),
                    resulting_observation=(
                        trace.resulting_observation
                    ),
                )
            )
            current_observation = (
                transition.resulting_observation
            )
            current_menu = (
                transition
                .resulting_admissible_commands
            )
            transition_cursor += 1
            pending_feedback = None

        elif (
            trace.execution_status
            is ExecutionStatus.ENVIRONMENT_ERROR
        ):
            pending_feedback = None

        else:
            pending_feedback = _feedback(
                trace.feedback_code
            )

        expected_budget = after

    if transition_cursor != len(transitions):
        _fail("EXTRA_PUBLIC_TRANSITION")

    if expected_budget != value.final_budget:
        _fail("FINAL_BUDGET_MISMATCH")
    if (
        value.final_budget.environment_step_count
        != environment_call_count
    ):
        _fail("FINAL_ENVIRONMENT_COUNT_MISMATCH")

    last_reason = (
        traces[-1].episode_termination_reason
    )
    if last_reason != value.termination_reason:
        _fail("TERMINATION_REASON_MISMATCH")

    _validate_final_state(value)

    return EpisodeSequenceReport(
        model_call_count=len(traces),
        environment_call_trace_count=(
            environment_call_count
        ),
        public_transition_count=len(
            transitions
        ),
        final_environment_step_count=(
            value.final_budget
            .environment_step_count
        ),
        valid=True,
    )
