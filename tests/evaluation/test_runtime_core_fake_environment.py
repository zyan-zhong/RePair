from __future__ import annotations

from dataclasses import dataclass
import json

import pytest

from pchsi.evaluation.action_trace import (
    ActionTrace,
    ExecutionStatus,
    PipelineVariant,
    TraceProvenance,
    sha256_string_sequence,
    sha256_text,
)
from pchsi.evaluation.budget import (
    BudgetLimits,
    BudgetState,
    EpisodeTerminationReason,
)
from pchsi.evaluation.raw_policy_parser import (
    ParserFailureCode,
    ParserStatus,
)
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    FORMAT_ERROR_V1,
    INVALID_ACTION_V1,
    InterfaceFeedbackCode,
    build_raw_policy_prompt,
    canonical_executed_transitions_json,
    sha256_executed_transitions,
)
from pchsi.evaluation.runtime_core import (
    AdmissibilityStatus,
    AttemptFailureStage,
    AttemptOutcome,
    ProtocolPreconditionResult,
    RuntimeDecision,
    RuntimeFailureCode,
    finalize_environment_result,
    process_completed_generation,
    validate_runtime_preconditions,
)


PUBLIC_TASK_GOAL = "put the pencil on the shelf"

INITIAL_OBSERVATION = (
    "You are in a study. "
    "A desk and shelf are visible."
)

SUCCESS_OBSERVATION = "Executed: go to desk 1"

MENU = (
    "go to desk 1",
    "look",
    "go to desk 1",
    "take pencil 1 from desk 1",
)

RAW_RESPONSES = (
    "not-json",
    '{"action":"go to nowhere"}',
    '{"action":"go to desk 1"}',
)

DEFAULT_LIMITS = BudgetLimits()

BUDGET_0 = BudgetState()

BUDGET_1 = BudgetState(
    policy_attempt_count=1,
    environment_step_count=0,
    protocol_failure_count=1,
    inadmissible_action_count=0,
    consecutive_nonexecuted_attempt_count=1,
)

BUDGET_2 = BudgetState(
    policy_attempt_count=2,
    environment_step_count=0,
    protocol_failure_count=1,
    inadmissible_action_count=1,
    consecutive_nonexecuted_attempt_count=2,
)

BUDGET_3 = BudgetState(
    policy_attempt_count=3,
    environment_step_count=1,
    protocol_failure_count=1,
    inadmissible_action_count=1,
    consecutive_nonexecuted_attempt_count=0,
)

INFRASTRUCTURE_BUDGET = BudgetState(
    policy_attempt_count=1,
    environment_step_count=1,
    protocol_failure_count=0,
    inadmissible_action_count=0,
    consecutive_nonexecuted_attempt_count=0,
)


@dataclass
class FakeEnvironment:
    """Test-only environment with a frozen visible command menu."""

    observation: str
    admissible_commands: tuple[str, ...]
    fail_next_step: bool = False
    attempted_actions: tuple[str, ...] = ()

    def step(
        self,
        action: str,
    ) -> tuple[str, dict[str, bool]]:
        """Execute one exact menu member or raise a synthetic failure."""

        self.attempted_actions = (
            *self.attempted_actions,
            action,
        )

        if action not in self.admissible_commands:
            raise AssertionError(
                "fake environment received "
                "a non-exact menu member"
            )

        if self.fail_next_step:
            raise RuntimeError(
                "synthetic environment failure"
            )

        next_observation = f"Executed: {action}"
        self.observation = next_observation

        return (
            next_observation,
            {"state_changed": True},
        )


@dataclass(frozen=True, slots=True)
class SuccessfulSequenceResult:
    """Complete record for the three-attempt success sequence."""

    public_task_goal: str
    initial_observation: str
    final_observation: str
    menu: tuple[str, ...]
    raw_responses: tuple[str, str, str]
    prompts: tuple[str, str, str, str]
    prompt_histories: tuple[
        tuple[ExecutedTransition, ...],
        tuple[ExecutedTransition, ...],
        tuple[ExecutedTransition, ...],
        tuple[ExecutedTransition, ...],
    ]
    preconditions: tuple[
        ProtocolPreconditionResult,
        ProtocolPreconditionResult,
        ProtocolPreconditionResult,
    ]
    decisions: tuple[
        RuntimeDecision,
        RuntimeDecision,
        RuntimeDecision,
    ]
    finalized_success_decision: RuntimeDecision
    traces: tuple[
        ActionTrace,
        ActionTrace,
        ActionTrace,
    ]
    initial_history: tuple[ExecutedTransition, ...]
    post_success_history: tuple[ExecutedTransition, ...]
    initial_memory_state_sha256: str
    post_success_memory_state_sha256: str
    final_feedback: InterfaceFeedbackCode | None
    fake_environment_attempted_actions: tuple[str, ...]
    fake_environment_menu_after: tuple[str, ...]
    precondition_call_count: int
    process_completed_generation_call_count: int
    environment_step_call_count: int
    environment_finalization_count: int
    orchestration_events: tuple[str, ...]
    prompt4_budget_before: BudgetState
    prompt4_budget_after: BudgetState


@dataclass(frozen=True, slots=True)
class InfrastructureSequenceResult:
    """Complete record for one infrastructure failure."""

    public_task_goal: str
    initial_observation: str
    final_observation: str
    menu: tuple[str, ...]
    raw_response: str
    prompt: str
    precondition: ProtocolPreconditionResult
    authorized_decision: RuntimeDecision
    finalized_decision: RuntimeDecision
    trace: ActionTrace
    initial_history: tuple[ExecutedTransition, ...]
    final_history: tuple[ExecutedTransition, ...]
    initial_memory_state_sha256: str
    final_memory_state_sha256: str
    fake_environment_attempted_actions: tuple[str, ...]
    fake_environment_menu_after: tuple[str, ...]
    precondition_call_count: int
    process_completed_generation_call_count: int
    environment_step_call_count: int
    environment_finalization_count: int
    orchestration_events: tuple[str, ...]
    membership_probe_exception_name: str
    membership_probe_exception_message: str
    membership_probe_attempted_actions: tuple[str, ...]
    membership_probe_observation_after: str
    membership_probe_menu_after: tuple[str, ...]
    membership_probe_history_after: tuple[
        ExecutedTransition,
        ...,
    ]


def _prompt_json_value(
    prompt: str,
    field: str,
) -> object:
    """Decode one frozen JSON-valued prompt line."""

    prefix = f"{field}="
    matching_lines = [
        line
        for line in prompt.splitlines()
        if line.startswith(prefix)
    ]

    assert len(matching_lines) == 1

    return json.loads(
        matching_lines[0][len(prefix):]
    )


def _expected_history_payload(
    history: tuple[ExecutedTransition, ...],
) -> object:
    """Return the canonical MEMORY_M0_V1 payload."""

    return json.loads(
        canonical_executed_transitions_json(
            history
        )
    )


def _assert_attributes(
    value: object,
    expected: dict[str, object],
) -> None:
    """Assert an explicit attribute contract."""

    for name, expected_value in expected.items():
        assert getattr(value, name) == expected_value


def _assert_precondition(
    result: ProtocolPreconditionResult,
    *,
    expected_budget: BudgetState,
    expected_menu_hash: str,
) -> None:
    """Check one pre-policy Stage-0 result."""

    assert result.menu_validation.valid is True
    assert result.menu_validation.failure_code is None
    assert (
        result.menu_validation.sequence_sha256
        == expected_menu_hash
    )
    assert result.should_call_policy is True
    assert result.termination_reason is None
    assert result.budget_before == expected_budget
    assert result.budget_after == expected_budget
    assert result.budget_before is result.budget_after
    assert result.budget_limits == DEFAULT_LIMITS


def _assert_trace_provenance(
    trace: ActionTrace,
    *,
    expected_memory_sha256: str,
) -> None:
    """Check the frozen E1-Dev provenance boundary."""

    _assert_attributes(
        trace.provenance,
        {
            "split_and_access_version": (
                "SPLIT_AND_ACCESS_V1"
            ),
            "split_name": "E1-Dev",
            "access_mode": "development_visible",
            "policy_version": "pi0",
            "seed": 17,
            "memory_version": "MEMORY_M0_V1",
            "memory_state_sha256": (
                expected_memory_sha256
            ),
        },
    )


def _assert_trace_payload(
    trace: ActionTrace,
    expected: dict[str, object],
) -> None:
    """Assert trace fields and deterministic JSON serialization."""

    payload = trace.to_dict()

    for name, expected_value in expected.items():
        assert payload[name] == expected_value

    assert json.loads(trace.to_json()) == payload


# BEGIN TASK6_GREEN_SUCCESS_DRIVER
def _run_successful_fake_environment_sequence(
) -> SuccessfulSequenceResult:
    """Run the complete test-only three-attempt success sequence."""

    initial_history: tuple[
        ExecutedTransition,
        ...,
    ] = ()

    initial_memory_state_sha256 = (
        sha256_executed_transitions(
            initial_history
        )
    )

    fake_environment = FakeEnvironment(
        observation=INITIAL_OBSERVATION,
        admissible_commands=MENU,
    )

    prompts: list[str] = []
    prompt_histories: list[
        tuple[ExecutedTransition, ...]
    ] = []
    preconditions: list[
        ProtocolPreconditionResult
    ] = []
    decisions: list[RuntimeDecision] = []
    traces: list[ActionTrace] = []
    orchestration_events: list[str] = []

    current_budget = BUDGET_0
    current_history = initial_history
    current_feedback: (
        InterfaceFeedbackCode
        | None
    ) = None

    precondition_call_count = 0
    process_completed_generation_call_count = 0
    environment_step_call_count = 0
    environment_finalization_count = 0

    finalized_success_decision: (
        RuntimeDecision
        | None
    ) = None

    def build_provenance(
        *,
        model_call_index: int,
    ) -> TraceProvenance:
        return TraceProvenance(
            run_id="task6-success",
            task_id="synthetic-task",
            episode_id="synthetic-episode",
            replicate_id=0,
            arm_id="E1_DEV_RAW",
            code_commit=(
                "f5bac95abf6faa0fd4d7d48169756c73"
                "edad75ee"
            ),
            config_sha256="b" * 64,
            provider="test-only",
            model_name="synthetic-policy",
            model_version="task6-v1.1",
            provider_request_id=(
                f"synthetic-request-{model_call_index}"
            ),
            retry_count=0,
            timestamp_utc=(
                "2026-08-03T10:00:00Z"
            ),
            split_and_access_version=(
                "SPLIT_AND_ACCESS_V1"
            ),
            split_name="E1-Dev",
            access_mode="development_visible",
            policy_version="pi0",
            seed=17,
            memory_version="MEMORY_M0_V1",
            memory_state_sha256=(
                initial_memory_state_sha256
            ),
        )

    def build_nonexecuted_trace(
        *,
        model_call_index: int,
        prompt: str,
        raw_response: str,
        decision: RuntimeDecision,
    ) -> ActionTrace:
        normalized_action = (
            decision.parse_result.normalized_action
        )

        literal_action = (
            ""
            if normalized_action is None
            else normalized_action
        )

        exactly_admissible = (
            normalized_action in MENU
            if normalized_action is not None
            else False
        )

        return ActionTrace.build(
            provenance=build_provenance(
                model_call_index=(
                    model_call_index
                ),
            ),
            pipeline_variant=PipelineVariant.RAW_V1,
            model_call_index=model_call_index,
            environment_step_index=None,
            execution_status=(
                ExecutionStatus.NOT_EXECUTED
            ),
            public_task_goal=PUBLIC_TASK_GOAL,
            observation=INITIAL_OBSERVATION,
            prompt_text=prompt,
            admissible_commands=MENU,
            raw_model_response=raw_response,
            literal_action=literal_action,
            parsed_phase=None,
            model_reason=None,
            parser_status=(
                decision.parse_result.status.value
            ),
            parser_error=(
                None
                if (
                    decision
                    .parse_result
                    .failure_code
                    is None
                )
                else (
                    decision
                    .parse_result
                    .failure_code
                    .value
                )
            ),
            parser_metadata=None,
            literal_action_exactly_admissible=(
                exactly_admissible
            ),
            literal_action_casefold_admissible=(
                exactly_admissible
            ),
            stages=(),
            final_executed_action=None,
            final_action_admissible=None,
            attempt_outcome=(
                decision.attempt_outcome.value
            ),
            failure_stage=(
                None
                if decision.failure_stage is None
                else decision.failure_stage.value
            ),
            failure_code=(
                None
                if decision.failure_code is None
                else decision.failure_code.value
            ),
            normalized_action=(
                decision.normalized_action
            ),
            admissibility_status=(
                decision.admissibility_status.value
            ),
            feedback_code=(
                None
                if decision.feedback_code is None
                else decision.feedback_code.value
            ),
            policy_attempt_count_before=(
                decision
                .budget_before
                .policy_attempt_count
            ),
            policy_attempt_count_after=(
                decision
                .budget_after
                .policy_attempt_count
            ),
            environment_step_count_before=(
                decision
                .budget_before
                .environment_step_count
            ),
            environment_step_count_after=(
                decision
                .budget_after
                .environment_step_count
            ),
            protocol_failure_count_before=(
                decision
                .budget_before
                .protocol_failure_count
            ),
            inadmissible_action_count_before=(
                decision
                .budget_before
                .inadmissible_action_count
            ),
            consecutive_nonexecuted_attempt_count_before=(
                decision
                .budget_before
                .consecutive_nonexecuted_attempt_count
            ),
            protocol_failure_count=(
                decision
                .budget_after
                .protocol_failure_count
            ),
            inadmissible_action_count=(
                decision
                .budget_after
                .inadmissible_action_count
            ),
            consecutive_nonexecuted_attempt_count=(
                decision
                .budget_after
                .consecutive_nonexecuted_attempt_count
            ),
            episode_termination_reason=(
                None
                if (
                    decision.termination_reason
                    is None
                )
                else (
                    decision
                    .termination_reason
                    .value
                )
            ),
            submitted_environment_action=None,
            resulting_observation=None,
            environment_event_flags=None,
        )

    for attempt_number, raw_response in enumerate(
        RAW_RESPONSES,
        start=1,
    ):
        orchestration_events.append(
            f"build_prompt_{attempt_number}"
        )

        prompt_history = tuple(
            current_history
        )

        prompt = build_raw_policy_prompt(
            public_task_goal=PUBLIC_TASK_GOAL,
            observation=fake_environment.observation,
            executed_transitions=prompt_history,
            admissible_commands=MENU,
            interface_feedback=current_feedback,
        )

        prompts.append(prompt)
        prompt_histories.append(
            prompt_history
        )

        orchestration_events.append(
            "validate_preconditions_"
            f"{attempt_number}"
        )

        precondition = (
            validate_runtime_preconditions(
                policy_visible_commands=MENU,
                harness_visible_commands=MENU,
                environment_commands=(
                    fake_environment
                    .admissible_commands
                ),
                budget_state=current_budget,
                budget_limits=DEFAULT_LIMITS,
            )
        )

        precondition_call_count += 1
        preconditions.append(
            precondition
        )

        orchestration_events.append(
            "process_generation_"
            f"{attempt_number}"
        )

        decision = process_completed_generation(
            raw_response=raw_response,
            visible_admissible_commands=MENU,
            precondition_result=precondition,
            budget_limits=DEFAULT_LIMITS,
        )

        process_completed_generation_call_count += 1
        decisions.append(decision)
        current_budget = decision.budget_after

        model_call_index = (
            attempt_number - 1
        )

        if decision.should_call_env is False:
            traces.append(
                build_nonexecuted_trace(
                    model_call_index=(
                        model_call_index
                    ),
                    prompt=prompt,
                    raw_response=raw_response,
                    decision=decision,
                )
            )

            current_feedback = (
                decision.feedback_code
            )

            continue

        if decision.should_call_env is not True:
            raise AssertionError(
                "runtime decision did not authorize "
                "the fake environment call"
            )

        if (
            decision
            .candidate_environment_action
            is None
        ):
            raise AssertionError(
                "authorized runtime decision has "
                "no environment action"
            )

        orchestration_events.append(
            "environment_step_1"
        )

        environment_step_call_count += 1

        next_observation, event_flags = (
            fake_environment.step(
                decision
                .candidate_environment_action
            )
        )

        orchestration_events.append(
            "finalize_environment_1"
        )

        finalized_success_decision = (
            finalize_environment_result(
                decision,
                environment_terminated=False,
                infrastructure_error=False,
            )
        )

        environment_finalization_count += 1

        successful_transition = (
            ExecutedTransition(
                action=(
                    decision
                    .candidate_environment_action
                ),
                resulting_observation=(
                    next_observation
                ),
            )
        )

        current_history = (
            *current_history,
            successful_transition,
        )

        current_feedback = None

        traces.append(
            ActionTrace.build(
                provenance=build_provenance(
                    model_call_index=(
                        model_call_index
                    ),
                ),
                pipeline_variant=(
                    PipelineVariant.RAW_V1
                ),
                model_call_index=(
                    model_call_index
                ),
                environment_step_index=0,
                execution_status=(
                    ExecutionStatus.EXECUTED
                ),
                public_task_goal=(
                    PUBLIC_TASK_GOAL
                ),
                observation=(
                    INITIAL_OBSERVATION
                ),
                prompt_text=prompt,
                admissible_commands=MENU,
                raw_model_response=(
                    raw_response
                ),
                literal_action=(
                    decision.normalized_action
                    or ""
                ),
                parsed_phase=None,
                model_reason=None,
                parser_status=(
                    decision
                    .parse_result
                    .status
                    .value
                ),
                parser_error=None,
                parser_metadata=None,
                literal_action_exactly_admissible=True,
                literal_action_casefold_admissible=True,
                stages=(),
                final_executed_action=(
                    decision
                    .candidate_environment_action
                ),
                final_action_admissible=True,
                attempt_outcome=(
                    finalized_success_decision
                    .attempt_outcome
                    .value
                ),
                failure_stage=None,
                failure_code=None,
                normalized_action=(
                    finalized_success_decision
                    .normalized_action
                ),
                admissibility_status=(
                    finalized_success_decision
                    .admissibility_status
                    .value
                ),
                feedback_code=None,
                policy_attempt_count_before=(
                    finalized_success_decision
                    .budget_before
                    .policy_attempt_count
                ),
                policy_attempt_count_after=(
                    finalized_success_decision
                    .budget_after
                    .policy_attempt_count
                ),
                environment_step_count_before=(
                    finalized_success_decision
                    .budget_before
                    .environment_step_count
                ),
                environment_step_count_after=(
                    finalized_success_decision
                    .budget_after
                    .environment_step_count
                ),
                protocol_failure_count_before=(
                    finalized_success_decision
                    .budget_before
                    .protocol_failure_count
                ),
                inadmissible_action_count_before=(
                    finalized_success_decision
                    .budget_before
                    .inadmissible_action_count
                ),
                consecutive_nonexecuted_attempt_count_before=(
                    finalized_success_decision
                    .budget_before
                    .consecutive_nonexecuted_attempt_count
                ),
                protocol_failure_count=(
                    finalized_success_decision
                    .budget_after
                    .protocol_failure_count
                ),
                inadmissible_action_count=(
                    finalized_success_decision
                    .budget_after
                    .inadmissible_action_count
                ),
                consecutive_nonexecuted_attempt_count=(
                    finalized_success_decision
                    .budget_after
                    .consecutive_nonexecuted_attempt_count
                ),
                episode_termination_reason=None,
                submitted_environment_action=(
                    decision
                    .candidate_environment_action
                ),
                resulting_observation=(
                    next_observation
                ),
                environment_event_flags=(
                    event_flags
                ),
            )
        )

    if finalized_success_decision is None:
        raise AssertionError(
            "success sequence did not finalize "
            "an environment result"
        )

    post_success_history = tuple(
        current_history
    )

    post_success_memory_state_sha256 = (
        sha256_executed_transitions(
            post_success_history
        )
    )

    prompt4_budget_before = (
        current_budget
    )

    orchestration_events.append(
        "build_prompt_4"
    )

    prompt_4_history = tuple(
        current_history
    )

    prompt_4 = build_raw_policy_prompt(
        public_task_goal=PUBLIC_TASK_GOAL,
        observation=fake_environment.observation,
        executed_transitions=(
            prompt_4_history
        ),
        admissible_commands=MENU,
        interface_feedback=current_feedback,
    )

    prompts.append(prompt_4)
    prompt_histories.append(
        prompt_4_history
    )

    prompt4_budget_after = (
        current_budget
    )

    return SuccessfulSequenceResult(
        public_task_goal=PUBLIC_TASK_GOAL,
        initial_observation=(
            INITIAL_OBSERVATION
        ),
        final_observation=(
            fake_environment.observation
        ),
        menu=MENU,
        raw_responses=RAW_RESPONSES,
        prompts=(
            prompts[0],
            prompts[1],
            prompts[2],
            prompts[3],
        ),
        prompt_histories=(
            prompt_histories[0],
            prompt_histories[1],
            prompt_histories[2],
            prompt_histories[3],
        ),
        preconditions=(
            preconditions[0],
            preconditions[1],
            preconditions[2],
        ),
        decisions=(
            decisions[0],
            decisions[1],
            decisions[2],
        ),
        finalized_success_decision=(
            finalized_success_decision
        ),
        traces=(
            traces[0],
            traces[1],
            traces[2],
        ),
        initial_history=initial_history,
        post_success_history=(
            post_success_history
        ),
        initial_memory_state_sha256=(
            initial_memory_state_sha256
        ),
        post_success_memory_state_sha256=(
            post_success_memory_state_sha256
        ),
        final_feedback=current_feedback,
        fake_environment_attempted_actions=(
            fake_environment
            .attempted_actions
        ),
        fake_environment_menu_after=(
            fake_environment
            .admissible_commands
        ),
        precondition_call_count=(
            precondition_call_count
        ),
        process_completed_generation_call_count=(
            process_completed_generation_call_count
        ),
        environment_step_call_count=(
            environment_step_call_count
        ),
        environment_finalization_count=(
            environment_finalization_count
        ),
        orchestration_events=tuple(
            orchestration_events
        ),
        prompt4_budget_before=(
            prompt4_budget_before
        ),
        prompt4_budget_after=(
            prompt4_budget_after
        ),
    )
# END TASK6_GREEN_SUCCESS_DRIVER


# BEGIN TASK6_GREEN_INFRASTRUCTURE_DRIVER
def _run_infrastructure_error_sequence(
) -> InfrastructureSequenceResult:
    """Run one exact-member environment infrastructure failure."""

    initial_history: tuple[
        ExecutedTransition,
        ...,
    ] = ()

    initial_memory_state_sha256 = (
        sha256_executed_transitions(
            initial_history
        )
    )

    orchestration_events: list[str] = []

    membership_probe = FakeEnvironment(
        observation=INITIAL_OBSERVATION,
        admissible_commands=MENU,
        fail_next_step=True,
    )

    membership_probe_history: tuple[
        ExecutedTransition,
        ...,
    ] = ()

    orchestration_events.append(
        "membership_probe_step"
    )

    try:
        membership_probe.step(
            "go to nowhere"
        )
    except AssertionError as error:
        membership_probe_exception_name = (
            type(error).__name__
        )
        membership_probe_exception_message = (
            str(error)
        )
    else:
        raise AssertionError(
            "membership probe did not reject "
            "the off-list action"
        )

    fake_environment = FakeEnvironment(
        observation=INITIAL_OBSERVATION,
        admissible_commands=MENU,
        fail_next_step=True,
    )

    raw_response = (
        '{"action":"go to desk 1"}'
    )

    orchestration_events.append(
        "build_prompt_1"
    )

    prompt = build_raw_policy_prompt(
        public_task_goal=PUBLIC_TASK_GOAL,
        observation=(
            fake_environment.observation
        ),
        executed_transitions=(
            initial_history
        ),
        admissible_commands=MENU,
        interface_feedback=None,
    )

    orchestration_events.append(
        "validate_preconditions_1"
    )

    precondition = validate_runtime_preconditions(
        policy_visible_commands=MENU,
        harness_visible_commands=MENU,
        environment_commands=(
            fake_environment
            .admissible_commands
        ),
        budget_state=BUDGET_0,
        budget_limits=DEFAULT_LIMITS,
    )

    precondition_call_count = 1

    orchestration_events.append(
        "process_generation_1"
    )

    authorized_decision = (
        process_completed_generation(
            raw_response=raw_response,
            visible_admissible_commands=MENU,
            precondition_result=(
                precondition
            ),
            budget_limits=DEFAULT_LIMITS,
        )
    )

    process_completed_generation_call_count = 1

    if (
        authorized_decision.should_call_env
        is not True
    ):
        raise AssertionError(
            "runtime decision did not authorize "
            "the fake environment call"
        )

    if (
        authorized_decision
        .candidate_environment_action
        is None
    ):
        raise AssertionError(
            "authorized runtime decision has "
            "no environment action"
        )

    orchestration_events.append(
        "environment_step_1"
    )

    environment_step_call_count = 1

    try:
        fake_environment.step(
            authorized_decision
            .candidate_environment_action
        )
    except RuntimeError as error:
        exception_type = (
            type(error).__name__
        )
    else:
        raise AssertionError(
            "synthetic infrastructure "
            "failure was not raised"
        )

    orchestration_events.append(
        "finalize_environment_1"
    )

    finalized_decision = (
        finalize_environment_result(
            authorized_decision,
            environment_terminated=False,
            infrastructure_error=True,
        )
    )

    environment_finalization_count = 1

    final_history = initial_history

    final_memory_state_sha256 = (
        sha256_executed_transitions(
            final_history
        )
    )

    provenance = TraceProvenance(
        run_id="task6-infrastructure",
        task_id="synthetic-task",
        episode_id=(
            "synthetic-infrastructure-episode"
        ),
        replicate_id=0,
        arm_id="E1_DEV_RAW",
        code_commit=(
            "f5bac95abf6faa0fd4d7d48169756c73"
            "edad75ee"
        ),
        config_sha256="b" * 64,
        provider="test-only",
        model_name="synthetic-policy",
        model_version="task6-v1.1",
        provider_request_id=(
            "synthetic-infrastructure-request"
        ),
        retry_count=0,
        timestamp_utc=(
            "2026-08-03T10:00:00Z"
        ),
        split_and_access_version=(
            "SPLIT_AND_ACCESS_V1"
        ),
        split_name="E1-Dev",
        access_mode="development_visible",
        policy_version="pi0",
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256=(
            initial_memory_state_sha256
        ),
    )

    trace = ActionTrace.build(
        provenance=provenance,
        pipeline_variant=(
            PipelineVariant.RAW_V1
        ),
        model_call_index=0,
        environment_step_index=0,
        execution_status=(
            ExecutionStatus.ENVIRONMENT_ERROR
        ),
        public_task_goal=(
            PUBLIC_TASK_GOAL
        ),
        observation=INITIAL_OBSERVATION,
        prompt_text=prompt,
        admissible_commands=MENU,
        raw_model_response=(
            raw_response
        ),
        literal_action="go to desk 1",
        parsed_phase=None,
        model_reason=None,
        parser_status="success",
        parser_error=None,
        parser_metadata=None,
        literal_action_exactly_admissible=True,
        literal_action_casefold_admissible=True,
        stages=(),
        final_executed_action=None,
        final_action_admissible=None,
        attempt_outcome=(
            finalized_decision
            .attempt_outcome
            .value
        ),
        failure_stage=(
            finalized_decision
            .failure_stage
            .value
            if (
                finalized_decision
                .failure_stage
                is not None
            )
            else None
        ),
        failure_code=(
            finalized_decision
            .failure_code
            .value
            if (
                finalized_decision
                .failure_code
                is not None
            )
            else None
        ),
        normalized_action=(
            finalized_decision
            .normalized_action
        ),
        admissibility_status=(
            finalized_decision
            .admissibility_status
            .value
        ),
        feedback_code=None,
        policy_attempt_count_before=(
            finalized_decision
            .budget_before
            .policy_attempt_count
        ),
        policy_attempt_count_after=(
            finalized_decision
            .budget_after
            .policy_attempt_count
        ),
        environment_step_count_before=(
            finalized_decision
            .budget_before
            .environment_step_count
        ),
        environment_step_count_after=(
            finalized_decision
            .budget_after
            .environment_step_count
        ),
        protocol_failure_count_before=(
            finalized_decision
            .budget_before
            .protocol_failure_count
        ),
        inadmissible_action_count_before=(
            finalized_decision
            .budget_before
            .inadmissible_action_count
        ),
        consecutive_nonexecuted_attempt_count_before=(
            finalized_decision
            .budget_before
            .consecutive_nonexecuted_attempt_count
        ),
        protocol_failure_count=(
            finalized_decision
            .budget_after
            .protocol_failure_count
        ),
        inadmissible_action_count=(
            finalized_decision
            .budget_after
            .inadmissible_action_count
        ),
        consecutive_nonexecuted_attempt_count=(
            finalized_decision
            .budget_after
            .consecutive_nonexecuted_attempt_count
        ),
        episode_termination_reason=(
            finalized_decision
            .termination_reason
            .value
            if (
                finalized_decision
                .termination_reason
                is not None
            )
            else None
        ),
        submitted_environment_action=(
            authorized_decision
            .candidate_environment_action
        ),
        resulting_observation=None,
        environment_event_flags={
            "exception_type": (
                exception_type
            ),
        },
    )

    return InfrastructureSequenceResult(
        public_task_goal=PUBLIC_TASK_GOAL,
        initial_observation=(
            INITIAL_OBSERVATION
        ),
        final_observation=(
            fake_environment.observation
        ),
        menu=MENU,
        raw_response=raw_response,
        prompt=prompt,
        precondition=precondition,
        authorized_decision=(
            authorized_decision
        ),
        finalized_decision=(
            finalized_decision
        ),
        trace=trace,
        initial_history=initial_history,
        final_history=final_history,
        initial_memory_state_sha256=(
            initial_memory_state_sha256
        ),
        final_memory_state_sha256=(
            final_memory_state_sha256
        ),
        fake_environment_attempted_actions=(
            fake_environment
            .attempted_actions
        ),
        fake_environment_menu_after=(
            fake_environment
            .admissible_commands
        ),
        precondition_call_count=(
            precondition_call_count
        ),
        process_completed_generation_call_count=(
            process_completed_generation_call_count
        ),
        environment_step_call_count=(
            environment_step_call_count
        ),
        environment_finalization_count=(
            environment_finalization_count
        ),
        orchestration_events=tuple(
            orchestration_events
        ),
        membership_probe_exception_name=(
            membership_probe_exception_name
        ),
        membership_probe_exception_message=(
            membership_probe_exception_message
        ),
        membership_probe_attempted_actions=(
            membership_probe
            .attempted_actions
        ),
        membership_probe_observation_after=(
            membership_probe.observation
        ),
        membership_probe_menu_after=(
            membership_probe
            .admissible_commands
        ),
        membership_probe_history_after=(
            membership_probe_history
        ),
    )
# END TASK6_GREEN_INFRASTRUCTURE_DRIVER


def test_fake_environment_end_to_end_sequence(
) -> None:
    run = (
        _run_successful_fake_environment_sequence()
    )

    _assert_attributes(
        run,
        {
            "public_task_goal": PUBLIC_TASK_GOAL,
            "initial_observation": INITIAL_OBSERVATION,
            "final_observation": SUCCESS_OBSERVATION,
            "menu": MENU,
            "raw_responses": RAW_RESPONSES,
            "precondition_call_count": 3,
            "process_completed_generation_call_count": 3,
            "environment_step_call_count": 1,
            "environment_finalization_count": 1,
            "orchestration_events": (
                "build_prompt_1",
                "validate_preconditions_1",
                "process_generation_1",
                "build_prompt_2",
                "validate_preconditions_2",
                "process_generation_2",
                "build_prompt_3",
                "validate_preconditions_3",
                "process_generation_3",
                "environment_step_1",
                "finalize_environment_1",
                "build_prompt_4",
            ),
            "prompt4_budget_before": BUDGET_3,
            "prompt4_budget_after": BUDGET_3,
            "final_feedback": None,
            "fake_environment_attempted_actions": (
                "go to desk 1",
            ),
            "fake_environment_menu_after": MENU,
        },
    )

    assert len(run.prompts) == 4
    assert len(run.preconditions) == 3
    assert len(run.decisions) == 3
    assert len(run.traces) == 3

    expected_histories = (
        (),
        (),
        (),
        (
            ExecutedTransition(
                action="go to desk 1",
                resulting_observation=(
                    SUCCESS_OBSERVATION
                ),
            ),
        ),
    )

    assert run.prompt_histories == (
        expected_histories
    )

    expected_observations = (
        INITIAL_OBSERVATION,
        INITIAL_OBSERVATION,
        INITIAL_OBSERVATION,
        SUCCESS_OBSERVATION,
    )

    expected_feedback = (
        None,
        FORMAT_ERROR_V1,
        INVALID_ACTION_V1,
        None,
    )

    for index, prompt in enumerate(
        run.prompts
    ):
        assert _prompt_json_value(
            prompt,
            "TASK_GOAL_JSON",
        ) == PUBLIC_TASK_GOAL
        assert _prompt_json_value(
            prompt,
            "CURRENT_OBSERVATION_JSON",
        ) == expected_observations[index]
        assert _prompt_json_value(
            prompt,
            "VISIBLE_ADMISSIBLE_COMMANDS_JSON",
        ) == list(MENU)
        assert _prompt_json_value(
            prompt,
            "EXECUTED_TRANSITIONS_JSON",
        ) == _expected_history_payload(
            expected_histories[index]
        )
        assert _prompt_json_value(
            prompt,
            "INTERFACE_FEEDBACK_JSON",
        ) == expected_feedback[index]

    expected_menu_hash = (
        sha256_string_sequence(MENU)
    )

    for precondition, budget in zip(
        run.preconditions,
        (BUDGET_0, BUDGET_1, BUDGET_2),
        strict=True,
    ):
        _assert_precondition(
            precondition,
            expected_budget=budget,
            expected_menu_hash=expected_menu_hash,
        )

    assert {
        item.menu_validation.sequence_sha256
        for item in run.preconditions
    } == {
        expected_menu_hash
    }

    (
        format_decision,
        off_list_decision,
        exact_member_decision,
    ) = run.decisions

    _assert_attributes(
        format_decision,
        {
            "budget_before": BUDGET_0,
            "budget_after": BUDGET_1,
            "attempt_outcome": (
                AttemptOutcome
                .FORMAT_PROTOCOL_FAILURE
            ),
            "failure_stage": (
                AttemptFailureStage.ENVELOPE
            ),
            "failure_code": (
                ParserFailureCode
                .ENVELOPE_INVALID_JSON
            ),
            "normalized_action": None,
            "admissibility_status": (
                AdmissibilityStatus.NOT_CHECKED
            ),
            "feedback_code": (
                InterfaceFeedbackCode
                .FORMAT_ERROR_V1
            ),
            "should_call_env": False,
            "candidate_environment_action": None,
        },
    )
    assert format_decision.parse_result.status is (
        ParserStatus.FAILED
    )
    assert format_decision.parse_result.failure_code is (
        ParserFailureCode.ENVELOPE_INVALID_JSON
    )

    _assert_attributes(
        off_list_decision,
        {
            "budget_before": BUDGET_1,
            "budget_after": BUDGET_2,
            "attempt_outcome": (
                AttemptOutcome
                .ACTION_NOT_ADMISSIBLE
            ),
            "failure_stage": (
                AttemptFailureStage.ADMISSIBILITY
            ),
            "failure_code": (
                RuntimeFailureCode
                .ACTION_NOT_ADMISSIBLE
            ),
            "normalized_action": "go to nowhere",
            "admissibility_status": (
                AdmissibilityStatus.NOT_ADMISSIBLE
            ),
            "feedback_code": (
                InterfaceFeedbackCode
                .INVALID_ACTION_V1
            ),
            "should_call_env": False,
            "candidate_environment_action": None,
        },
    )
    assert off_list_decision.parse_result.status is (
        ParserStatus.SUCCESS
    )
    assert (
        off_list_decision
        .parse_result
        .normalized_action
        == "go to nowhere"
    )
    assert (
        off_list_decision.parse_result.failure_code
        is None
    )

    _assert_attributes(
        exact_member_decision,
        {
            "budget_before": BUDGET_2,
            "budget_after": BUDGET_3,
            "attempt_outcome": (
                AttemptOutcome.ACTION_EXECUTED
            ),
            "failure_stage": None,
            "failure_code": None,
            "normalized_action": "go to desk 1",
            "admissibility_status": (
                AdmissibilityStatus.EXACT_MEMBER
            ),
            "feedback_code": None,
            "should_call_env": True,
            "candidate_environment_action": (
                "go to desk 1"
            ),
        },
    )
    assert exact_member_decision.parse_result.status is (
        ParserStatus.SUCCESS
    )
    assert (
        exact_member_decision
        .parse_result
        .normalized_action
        == "go to desk 1"
    )

    finalized = run.finalized_success_decision

    _assert_attributes(
        finalized,
        {
            "budget_before": BUDGET_2,
            "budget_after": BUDGET_3,
            "attempt_outcome": (
                AttemptOutcome.ACTION_EXECUTED
            ),
            "failure_stage": None,
            "failure_code": None,
            "should_call_env": False,
            "termination_reason": None,
        },
    )

    for unauthorized in (
        format_decision,
        off_list_decision,
        finalized,
    ):
        with pytest.raises(
            ValueError,
            match="authorize",
        ):
            finalize_environment_result(
                unauthorized,
                environment_terminated=False,
                infrastructure_error=False,
            )

    assert run.initial_history == ()
    assert run.post_success_history == (
        expected_histories[3]
    )
    assert run.initial_memory_state_sha256 == (
        sha256_executed_transitions(())
    )
    assert run.post_success_memory_state_sha256 == (
        sha256_executed_transitions(
            run.post_success_history
        )
    )
    assert (
        run.post_success_memory_state_sha256
        != run.initial_memory_state_sha256
    )

    common_trace = {
        "pipeline_variant": "raw_v1",
        "public_task_goal": PUBLIC_TASK_GOAL,
        "public_task_goal_sha256": (
            sha256_text(PUBLIC_TASK_GOAL)
        ),
        "admissible_commands": list(MENU),
        "admissible_commands_sha256": (
            expected_menu_hash
        ),
        "observation": INITIAL_OBSERVATION,
        "observation_sha256": (
            sha256_text(INITIAL_OBSERVATION)
        ),
        "stages": [],
        "parsed_phase": None,
        "parser_metadata": {},
        "model_reason": None,
        "episode_termination_reason": None,
    }

    trace_expectations = (
        common_trace
        | {
            "model_call_index": 0,
            "environment_step_index": None,
            "execution_status": "not_executed",
            "prompt_text": run.prompts[0],
            "prompt_sha256": (
                sha256_text(run.prompts[0])
            ),
            "raw_model_response": RAW_RESPONSES[0],
            "raw_response_sha256": (
                sha256_text(RAW_RESPONSES[0])
            ),
            "literal_action": "",
            "parser_status": "failed",
            "parser_error": "ENVELOPE_INVALID_JSON",
            "literal_action_exactly_admissible": False,
            "literal_action_casefold_admissible": False,
            "final_executed_action": None,
            "final_action_admissible": None,
            "attempt_outcome": (
                "FORMAT_PROTOCOL_FAILURE"
            ),
            "failure_stage": "envelope",
            "failure_code": "ENVELOPE_INVALID_JSON",
            "normalized_action": None,
            "admissibility_status": "not_checked",
            "feedback_code": "FORMAT_ERROR_V1",
            "policy_attempt_count_before": 0,
            "policy_attempt_count_after": 1,
            "environment_step_count_before": 0,
            "environment_step_count_after": 0,
            "protocol_failure_count": 1,
            "inadmissible_action_count": 0,
            "consecutive_nonexecuted_attempt_count": 1,
            "submitted_environment_action": None,
            "resulting_observation": None,
            "resulting_observation_sha256": None,
            "environment_event_flags": {},
        },
        common_trace
        | {
            "model_call_index": 1,
            "environment_step_index": None,
            "execution_status": "not_executed",
            "prompt_text": run.prompts[1],
            "prompt_sha256": (
                sha256_text(run.prompts[1])
            ),
            "raw_model_response": RAW_RESPONSES[1],
            "raw_response_sha256": (
                sha256_text(RAW_RESPONSES[1])
            ),
            "literal_action": "go to nowhere",
            "parser_status": "success",
            "parser_error": None,
            "parser_metadata": {},
            "literal_action_exactly_admissible": False,
            "literal_action_casefold_admissible": False,
            "final_executed_action": None,
            "final_action_admissible": None,
            "attempt_outcome": (
                "ACTION_NOT_ADMISSIBLE"
            ),
            "failure_stage": "admissibility",
            "failure_code": "ACTION_NOT_ADMISSIBLE",
            "normalized_action": "go to nowhere",
            "admissibility_status": "not_admissible",
            "feedback_code": "INVALID_ACTION_V1",
            "policy_attempt_count_before": 1,
            "policy_attempt_count_after": 2,
            "environment_step_count_before": 0,
            "environment_step_count_after": 0,
            "protocol_failure_count": 1,
            "inadmissible_action_count": 1,
            "consecutive_nonexecuted_attempt_count": 2,
            "submitted_environment_action": None,
            "resulting_observation": None,
            "resulting_observation_sha256": None,
            "environment_event_flags": {},
        },
        common_trace
        | {
            "model_call_index": 2,
            "environment_step_index": 0,
            "execution_status": "executed",
            "prompt_text": run.prompts[2],
            "prompt_sha256": (
                sha256_text(run.prompts[2])
            ),
            "raw_model_response": RAW_RESPONSES[2],
            "raw_response_sha256": (
                sha256_text(RAW_RESPONSES[2])
            ),
            "literal_action": "go to desk 1",
            "parser_status": "success",
            "parser_error": None,
            "literal_action_exactly_admissible": True,
            "literal_action_casefold_admissible": True,
            "final_executed_action": "go to desk 1",
            "final_action_admissible": True,
            "attempt_outcome": "ACTION_EXECUTED",
            "failure_stage": None,
            "failure_code": None,
            "normalized_action": "go to desk 1",
            "admissibility_status": "exact_member",
            "feedback_code": None,
            "policy_attempt_count_before": 2,
            "policy_attempt_count_after": 3,
            "environment_step_count_before": 0,
            "environment_step_count_after": 1,
            "protocol_failure_count": 1,
            "inadmissible_action_count": 1,
            "consecutive_nonexecuted_attempt_count": 0,
            "submitted_environment_action": (
                "go to desk 1"
            ),
            "resulting_observation": (
                SUCCESS_OBSERVATION
            ),
            "resulting_observation_sha256": (
                sha256_text(SUCCESS_OBSERVATION)
            ),
            "environment_event_flags": {
                "state_changed": True,
            },
        },
    )

    for trace, expected in zip(
        run.traces,
        trace_expectations,
        strict=True,
    ):
        _assert_trace_provenance(
            trace,
            expected_memory_sha256=(
                run.initial_memory_state_sha256
            ),
        )
        _assert_trace_payload(
            trace,
            expected,
        )


def test_fake_environment_infrastructure_error(
) -> None:
    run = _run_infrastructure_error_sequence()

    _assert_attributes(
        run,
        {
            "public_task_goal": PUBLIC_TASK_GOAL,
            "initial_observation": INITIAL_OBSERVATION,
            "final_observation": INITIAL_OBSERVATION,
            "menu": MENU,
            "raw_response": (
                '{"action":"go to desk 1"}'
            ),
            "precondition_call_count": 1,
            "process_completed_generation_call_count": 1,
            "environment_step_call_count": 1,
            "environment_finalization_count": 1,
            "orchestration_events": (
                "membership_probe_step",
                "build_prompt_1",
                "validate_preconditions_1",
                "process_generation_1",
                "environment_step_1",
                "finalize_environment_1",
            ),
            "fake_environment_attempted_actions": (
                "go to desk 1",
            ),
            "fake_environment_menu_after": MENU,
            "membership_probe_exception_name": (
                "AssertionError"
            ),
            "membership_probe_exception_message": (
                "fake environment received "
                "a non-exact menu member"
            ),
            "membership_probe_attempted_actions": (
                "go to nowhere",
            ),
            "membership_probe_observation_after": (
                INITIAL_OBSERVATION
            ),
            "membership_probe_menu_after": MENU,
            "membership_probe_history_after": (),
        },
    )

    assert _prompt_json_value(
        run.prompt,
        "TASK_GOAL_JSON",
    ) == PUBLIC_TASK_GOAL
    assert _prompt_json_value(
        run.prompt,
        "CURRENT_OBSERVATION_JSON",
    ) == INITIAL_OBSERVATION
    assert _prompt_json_value(
        run.prompt,
        "VISIBLE_ADMISSIBLE_COMMANDS_JSON",
    ) == list(MENU)
    assert _prompt_json_value(
        run.prompt,
        "EXECUTED_TRANSITIONS_JSON",
    ) == []
    assert _prompt_json_value(
        run.prompt,
        "INTERFACE_FEEDBACK_JSON",
    ) is None

    expected_menu_hash = (
        sha256_string_sequence(MENU)
    )

    _assert_precondition(
        run.precondition,
        expected_budget=BUDGET_0,
        expected_menu_hash=expected_menu_hash,
    )

    _assert_attributes(
        run.authorized_decision,
        {
            "budget_before": BUDGET_0,
            "budget_after": INFRASTRUCTURE_BUDGET,
            "attempt_outcome": (
                AttemptOutcome.ACTION_EXECUTED
            ),
            "failure_stage": None,
            "failure_code": None,
            "normalized_action": "go to desk 1",
            "admissibility_status": (
                AdmissibilityStatus.EXACT_MEMBER
            ),
            "feedback_code": None,
            "should_call_env": True,
            "candidate_environment_action": (
                "go to desk 1"
            ),
        },
    )
    assert (
        run.authorized_decision
        .parse_result
        .status
        is ParserStatus.SUCCESS
    )

    _assert_attributes(
        run.finalized_decision,
        {
            "budget_before": BUDGET_0,
            "budget_after": INFRASTRUCTURE_BUDGET,
            "attempt_outcome": (
                AttemptOutcome.INFRASTRUCTURE_ERROR
            ),
            "failure_stage": (
                AttemptFailureStage.INFRASTRUCTURE
            ),
            "failure_code": (
                RuntimeFailureCode
                .ENVIRONMENT_STEP_FAILED
            ),
            "normalized_action": "go to desk 1",
            "admissibility_status": (
                AdmissibilityStatus.EXACT_MEMBER
            ),
            "feedback_code": None,
            "should_call_env": False,
            "termination_reason": (
                EpisodeTerminationReason
                .INFRASTRUCTURE_ERROR
            ),
        },
    )

    with pytest.raises(
        ValueError,
        match="authorize",
    ):
        finalize_environment_result(
            run.finalized_decision,
            environment_terminated=False,
            infrastructure_error=True,
        )

    assert run.initial_history == ()
    assert run.final_history == ()
    assert run.initial_memory_state_sha256 == (
        sha256_executed_transitions(())
    )
    assert run.final_memory_state_sha256 == (
        run.initial_memory_state_sha256
    )

    _assert_trace_provenance(
        run.trace,
        expected_memory_sha256=(
            run.initial_memory_state_sha256
        ),
    )

    _assert_trace_payload(
        run.trace,
        {
            "pipeline_variant": "raw_v1",
            "model_call_index": 0,
            "environment_step_index": 0,
            "execution_status": "environment_error",
            "public_task_goal": PUBLIC_TASK_GOAL,
            "public_task_goal_sha256": (
                sha256_text(PUBLIC_TASK_GOAL)
            ),
            "observation": INITIAL_OBSERVATION,
            "observation_sha256": (
                sha256_text(INITIAL_OBSERVATION)
            ),
            "prompt_text": run.prompt,
            "prompt_sha256": (
                sha256_text(run.prompt)
            ),
            "admissible_commands": list(MENU),
            "admissible_commands_sha256": (
                expected_menu_hash
            ),
            "raw_model_response": run.raw_response,
            "raw_response_sha256": (
                sha256_text(run.raw_response)
            ),
            "literal_action": "go to desk 1",
            "parsed_phase": None,
            "model_reason": None,
            "parser_status": "success",
            "parser_error": None,
            "parser_metadata": {},
            "literal_action_exactly_admissible": True,
            "literal_action_casefold_admissible": True,
            "stages": [],
            "final_executed_action": None,
            "final_action_admissible": None,
            "attempt_outcome": "INFRASTRUCTURE_ERROR",
            "failure_stage": "infrastructure",
            "failure_code": "ENVIRONMENT_STEP_FAILED",
            "normalized_action": "go to desk 1",
            "admissibility_status": "exact_member",
            "feedback_code": None,
            "policy_attempt_count_before": 0,
            "policy_attempt_count_after": 1,
            "environment_step_count_before": 0,
            "environment_step_count_after": 1,
            "protocol_failure_count": 0,
            "inadmissible_action_count": 0,
            "consecutive_nonexecuted_attempt_count": 0,
            "episode_termination_reason": (
                "INFRASTRUCTURE_ERROR"
            ),
            "submitted_environment_action": (
                "go to desk 1"
            ),
            "resulting_observation": None,
            "resulting_observation_sha256": None,
            "environment_event_flags": {
                "exception_type": "RuntimeError",
            },
        },
    )
