from __future__ import annotations

import copy

import pytest

from pchsi.evaluation.action_trace import (
    ActionTrace,
    TraceProvenance,
    sha256_string_sequence,
    sha256_text,
)
from pchsi.evaluation.alfworld_contracts import (
    MenuSnapshot,
    StepPublicState,
)
from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.episode_sequence import (
    EpisodeSequenceError,
    EpisodeSequenceInput,
    validate_episode_sequence,
)
from pchsi.evaluation.policy_response import (
    PolicyGeneration,
)
from pchsi.evaluation.public_transition import (
    build_public_transition,
)
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    InterfaceFeedbackCode,
    build_raw_policy_prompt,
    sha256_executed_transitions,
)
from pchsi.evaluation.runtime_core import (
    finalize_environment_result,
    process_completed_generation,
    validate_runtime_preconditions,
)
from pchsi.evaluation.trace_assembler import (
    TraceAssemblyInput,
    assemble_action_trace,
)


SCHEDULED_CELL_ID = "e1-t0000-s0000000017"
ATTEMPT_ID = "e1-t0000-s0000000017-a000"


def _menu(commands: tuple[str, ...]) -> MenuSnapshot:
    return MenuSnapshot(
        commands=commands,
        sequence_sha256=sha256_string_sequence(
            commands
        ),
    )


def _generation(
    *,
    raw_response: str,
    request_id: str,
) -> PolicyGeneration:
    return PolicyGeneration(
        raw_response_text=raw_response,
        raw_response_body=raw_response.encode("utf-8"),
        provider_request_id=request_id,
        client_request_id=f"client-{request_id}",
        finish_reason="stop",
        prompt_tokens=3,
        completion_tokens=2,
        prompt_token_ids=(1, 2, 3),
        token_ids=(4, 5),
        latency_ms=1,
    )


def _provenance(
    *,
    request_id: str,
    history: tuple[ExecutedTransition, ...],
) -> TraceProvenance:
    return TraceProvenance(
        run_id="run-e1",
        task_id="alfworld_valid_unseen_all134_0000",
        episode_id=ATTEMPT_ID,
        replicate_id=0,
        arm_id="R0_RAW_WITH_MENU_V1",
        code_commit="commit",
        config_sha256="a" * 64,
        provider="vllm",
        model_name="Qwen2.5-3B-Instruct-E1",
        model_version="revision",
        provider_request_id=request_id,
        retry_count=0,
        timestamp_utc="2026-08-07T00:00:00Z",
        split_and_access_version="SPLIT_AND_ACCESS_V1",
        split_name="valid_unseen",
        access_mode="TRUSTED_MANIFEST_DIRECT_V1",
        policy_version="RAW_WITH_MENU_V1",
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256=(
            sha256_executed_transitions(history)
        ),
    )


def _make_trace(
    *,
    state: BudgetState,
    history: tuple[ExecutedTransition, ...],
    feedback: InterfaceFeedbackCode | None,
    observation: str,
    menu: MenuSnapshot,
    raw_response: str,
    result: StepPublicState | None = None,
    infrastructure: bool = False,
) -> tuple[
    ActionTrace,
    BudgetState,
    ExecutedTransition | None,
    object | None,
]:
    model_call_index = state.policy_attempt_count
    request_id = f"provider-{model_call_index}"

    prompt = build_raw_policy_prompt(
        public_task_goal="put the object away",
        observation=observation,
        executed_transitions=history,
        admissible_commands=menu.commands,
        interface_feedback=feedback,
    )

    precondition = validate_runtime_preconditions(
        policy_visible_commands=menu.commands,
        harness_visible_commands=menu.commands,
        environment_commands=menu.commands,
        budget_state=state,
    )
    decision = process_completed_generation(
        raw_response=raw_response,
        visible_admissible_commands=menu.commands,
        precondition_result=precondition,
    )

    if decision.should_call_env:
        decision = finalize_environment_result(
            decision,
            environment_terminated=(
                False if result is None else result.done
            ),
            infrastructure_error=infrastructure,
        )

    trace = assemble_action_trace(
        TraceAssemblyInput(
            provenance=_provenance(
                request_id=request_id,
                history=history,
            ),
            model_call_index=model_call_index,
            public_task_goal="put the object away",
            observation=observation,
            prompt_text=prompt,
            menu=menu,
            generation=_generation(
                raw_response=raw_response,
                request_id=request_id,
            ),
            decision=decision,
            accepted_result=result,
            environment_exception_type=(
                "RuntimeError"
                if infrastructure
                else None
            ),
        )
    )

    transition = None
    executed = None
    if result is not None and not infrastructure:
        transition = build_public_transition(
            scheduled_cell_id=SCHEDULED_CELL_ID,
            execution_attempt_id=ATTEMPT_ID,
            model_call_index=model_call_index,
            environment_step_index=(
                state.environment_step_count
            ),
            submitted_action=(
                decision.candidate_environment_action
            ),
            pre_observation=observation,
            pre_menu=menu,
            result=result,
        )
        executed = ExecutedTransition(
            action=decision.candidate_environment_action,
            resulting_observation=result.observation,
        )

    return (
        trace,
        decision.budget_after,
        executed,
        transition,
    )


def _valid_sequence() -> EpisodeSequenceInput:
    state = BudgetState()
    history: tuple[ExecutedTransition, ...] = ()
    observation = "initial"
    menu = _menu(("look", "inventory", "look"))
    traces: list[ActionTrace] = []
    transitions = []

    trace, state, _, _ = _make_trace(
        state=state,
        history=history,
        feedback=None,
        observation=observation,
        menu=menu,
        raw_response="not-json",
    )
    traces.append(trace)

    trace, state, _, _ = _make_trace(
        state=state,
        history=history,
        feedback=InterfaceFeedbackCode.FORMAT_ERROR_V1,
        observation=observation,
        menu=menu,
        raw_response='{"action":"go north"}',
    )
    traces.append(trace)

    first_result = StepPublicState(
        observation="after-look",
        menu=_menu(("inventory", "look")),
        score=0,
        done=False,
        won=False,
    )
    trace, state, executed, transition = _make_trace(
        state=state,
        history=history,
        feedback=InterfaceFeedbackCode.INVALID_ACTION_V1,
        observation=observation,
        menu=menu,
        raw_response='{"action":"look"}',
        result=first_result,
    )
    traces.append(trace)
    transitions.append(transition)
    history = (*history, executed)
    observation = first_result.observation
    menu = first_result.menu

    final_result = StepPublicState(
        observation="done",
        menu=_menu(()),
        score=1,
        done=True,
        won=True,
    )
    trace, state, executed, transition = _make_trace(
        state=state,
        history=history,
        feedback=None,
        observation=observation,
        menu=menu,
        raw_response='{"action":"inventory"}',
        result=final_result,
    )
    traces.append(trace)
    transitions.append(transition)

    return EpisodeSequenceInput(
        traces=tuple(traces),
        public_transitions=tuple(transitions),
        final_budget=state,
        final_success=True,
        final_done=True,
        final_won=True,
        termination_reason="ENVIRONMENT_TERMINATED",
    )


def _mutate(value, **changes):
    clone = copy.copy(value)
    for name, replacement in changes.items():
        object.__setattr__(clone, name, replacement)
    return clone


def test_valid_multi_attempt_sequence_passes() -> None:
    report = validate_episode_sequence(
        _valid_sequence()
    )

    assert report.valid is True
    assert report.model_call_count == 4
    assert report.environment_call_trace_count == 2
    assert report.public_transition_count == 2
    assert report.final_environment_step_count == 2


@pytest.mark.parametrize(
    "mutation",
    ["missing", "reordered", "duplicate"],
)
def test_missing_reordered_or_duplicate_trace_fails(
    mutation: str,
) -> None:
    value = _valid_sequence()
    traces = list(value.traces)

    if mutation == "missing":
        traces.pop(1)
    elif mutation == "reordered":
        traces[0], traces[1] = traces[1], traces[0]
    elif mutation == "duplicate":
        traces.insert(1, traces[0])
    else:
        raise AssertionError(mutation)

    with pytest.raises(EpisodeSequenceError):
        validate_episode_sequence(
            EpisodeSequenceInput(
                traces=tuple(traces),
                public_transitions=(
                    value.public_transitions
                ),
                final_budget=value.final_budget,
                final_success=value.final_success,
                final_done=value.final_done,
                final_won=value.final_won,
                termination_reason=(
                    value.termination_reason
                ),
            )
        )


@pytest.mark.parametrize(
    "mutation",
    ["budget", "observation", "menu", "feedback", "m0"],
)
def test_budget_observation_menu_feedback_and_m0_discontinuity_fail(
    mutation: str,
) -> None:
    value = _valid_sequence()
    traces = list(value.traces)
    target = traces[1]

    if mutation == "budget":
        target = _mutate(
            target,
            policy_attempt_count_before=9,
        )
    elif mutation == "observation":
        target = _mutate(
            target,
            observation="wrong",
            observation_sha256=sha256_text("wrong"),
        )
    elif mutation == "menu":
        target = _mutate(
            target,
            admissible_commands=("wrong",),
            admissible_commands_sha256=(
                sha256_string_sequence(("wrong",))
            ),
        )
    elif mutation == "feedback":
        target = _mutate(
            target,
            prompt_text=target.prompt_text.replace(
                "FORMAT_ERROR_V1",
                "INVALID_ACTION_V1",
            ),
            prompt_sha256=sha256_text(
                target.prompt_text.replace(
                    "FORMAT_ERROR_V1",
                    "INVALID_ACTION_V1",
                )
            ),
        )
    elif mutation == "m0":
        provenance = _mutate(
            target.provenance,
            memory_state_sha256="f" * 64,
        )
        target = _mutate(
            target,
            provenance=provenance,
        )
    else:
        raise AssertionError(mutation)

    traces[1] = target

    with pytest.raises(EpisodeSequenceError):
        validate_episode_sequence(
            EpisodeSequenceInput(
                traces=tuple(traces),
                public_transitions=(
                    value.public_transitions
                ),
                final_budget=value.final_budget,
                final_success=value.final_success,
                final_done=value.final_done,
                final_won=value.final_won,
                termination_reason=(
                    value.termination_reason
                ),
            )
        )


def test_environment_step_indices_cover_executed_and_error_calls() -> None:
    state = BudgetState()
    history: tuple[ExecutedTransition, ...] = ()
    menu = _menu(("look",))

    trace, state, _, _ = _make_trace(
        state=state,
        history=history,
        feedback=None,
        observation="initial",
        menu=menu,
        raw_response='{"action":"look"}',
        infrastructure=True,
    )

    value = EpisodeSequenceInput(
        traces=(trace,),
        public_transitions=(),
        final_budget=state,
        final_success=None,
        final_done=None,
        final_won=None,
        termination_reason="INFRASTRUCTURE_ERROR",
    )
    report = validate_episode_sequence(value)
    assert report.environment_call_trace_count == 1
    assert report.public_transition_count == 0
    assert report.final_environment_step_count == 1

    corrupted = _mutate(
        trace,
        environment_step_index=3,
    )
    with pytest.raises(EpisodeSequenceError):
        validate_episode_sequence(
            EpisodeSequenceInput(
                traces=(corrupted,),
                public_transitions=(),
                final_budget=state,
                final_success=None,
                final_done=None,
                final_won=None,
                termination_reason=(
                    "INFRASTRUCTURE_ERROR"
                ),
            )
        )


def test_public_transition_count_excludes_infrastructure_error() -> None:
    state = BudgetState()
    trace, state, _, _ = _make_trace(
        state=state,
        history=(),
        feedback=None,
        observation="initial",
        menu=_menu(("look",)),
        raw_response='{"action":"look"}',
        infrastructure=True,
    )

    report = validate_episode_sequence(
        EpisodeSequenceInput(
            traces=(trace,),
            public_transitions=(),
            final_budget=state,
            final_success=None,
            final_done=None,
            final_won=None,
            termination_reason="INFRASTRUCTURE_ERROR",
        )
    )
    assert report.environment_call_trace_count == 1
    assert report.public_transition_count == 0


def test_infrastructure_trace_with_transition_fails() -> None:
    state = BudgetState()
    menu = _menu(("look",))
    trace, state, _, _ = _make_trace(
        state=state,
        history=(),
        feedback=None,
        observation="initial",
        menu=menu,
        raw_response='{"action":"look"}',
        infrastructure=True,
    )
    fabricated = build_public_transition(
        scheduled_cell_id=SCHEDULED_CELL_ID,
        execution_attempt_id=ATTEMPT_ID,
        model_call_index=0,
        environment_step_index=0,
        submitted_action="look",
        pre_observation="initial",
        pre_menu=menu,
        result=StepPublicState(
            observation="fabricated",
            menu=_menu(("look",)),
            score=0,
            done=False,
            won=False,
        ),
    )

    with pytest.raises(EpisodeSequenceError):
        validate_episode_sequence(
            EpisodeSequenceInput(
                traces=(trace,),
                public_transitions=(fabricated,),
                final_budget=state,
                final_success=None,
                final_done=None,
                final_won=None,
                termination_reason=(
                    "INFRASTRUCTURE_ERROR"
                ),
            )
        )


def test_final_budget_and_termination_must_match() -> None:
    value = _valid_sequence()

    with pytest.raises(EpisodeSequenceError):
        validate_episode_sequence(
            EpisodeSequenceInput(
                traces=value.traces,
                public_transitions=(
                    value.public_transitions
                ),
                final_budget=BudgetState(),
                final_success=True,
                final_done=True,
                final_won=True,
                termination_reason=(
                    value.termination_reason
                ),
            )
        )

    with pytest.raises(EpisodeSequenceError):
        validate_episode_sequence(
            EpisodeSequenceInput(
                traces=value.traces,
                public_transitions=(
                    value.public_transitions
                ),
                final_budget=value.final_budget,
                final_success=True,
                final_done=True,
                final_won=True,
                termination_reason=(
                    "ENVIRONMENT_STEP_BUDGET_EXHAUSTED"
                ),
            )
        )


def test_success_requires_done_true_won_true() -> None:
    value = _valid_sequence()

    for done, won in (
        (False, True),
        (True, False),
        (None, None),
    ):
        with pytest.raises(EpisodeSequenceError):
            validate_episode_sequence(
                EpisodeSequenceInput(
                    traces=value.traces,
                    public_transitions=(
                        value.public_transitions
                    ),
                    final_budget=value.final_budget,
                    final_success=True,
                    final_done=done,
                    final_won=won,
                    termination_reason=(
                        "ENVIRONMENT_TERMINATED"
                    ),
                )
            )
