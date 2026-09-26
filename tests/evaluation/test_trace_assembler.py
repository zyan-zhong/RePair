from __future__ import annotations

from pchsi.evaluation.action_trace import (
    ExecutionStatus,
    PipelineVariant,
    TraceProvenance,
    sha256_string_sequence,
)
from pchsi.evaluation.alfworld_contracts import (
    MenuSnapshot,
    StepPublicState,
)
from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.policy_response import PolicyGeneration
from pchsi.evaluation.raw_policy_prompt import (
    sha256_executed_transitions,
)
from pchsi.evaluation.runtime_core import (
    AttemptOutcome,
    finalize_environment_result,
    process_completed_generation,
    validate_runtime_preconditions,
)
from pchsi.evaluation.trace_assembler import (
    TraceAssemblyInput,
    assemble_action_trace,
)


def _menu(commands: tuple[str, ...]) -> MenuSnapshot:
    return MenuSnapshot(
        commands=commands,
        sequence_sha256=sha256_string_sequence(
            commands
        ),
    )


def _provenance(
    *,
    provider_request_id: str,
) -> TraceProvenance:
    return TraceProvenance(
        run_id="run-e1",
        task_id="alfworld_valid_unseen_all134_0000",
        episode_id="e1-t0000-s0000000017-a000",
        replicate_id=0,
        arm_id="R0_RAW_WITH_MENU_V1",
        code_commit="commit",
        config_sha256="a" * 64,
        provider="vllm",
        model_name="Qwen2.5-3B-Instruct-E1",
        model_version="revision",
        provider_request_id=provider_request_id,
        retry_count=0,
        timestamp_utc="2026-08-07T00:00:00Z",
        split_and_access_version="SPLIT_AND_ACCESS_V1",
        split_name="valid_unseen",
        access_mode="TRUSTED_MANIFEST_DIRECT_V1",
        policy_version="RAW_WITH_MENU_V1",
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256=(
            sha256_executed_transitions(())
        ),
    )


def _generation(
    raw_response: str,
) -> PolicyGeneration:
    return PolicyGeneration(
        raw_response_text=raw_response,
        raw_response_body=raw_response.encode("utf-8"),
        provider_request_id="provider-request",
        client_request_id="client-request",
        finish_reason="stop",
        prompt_tokens=3,
        completion_tokens=2,
        prompt_token_ids=(1, 2, 3),
        token_ids=(4, 5),
        latency_ms=1,
    )


def _decision(
    *,
    raw_response: str,
    commands: tuple[str, ...],
):
    precondition = validate_runtime_preconditions(
        policy_visible_commands=commands,
        harness_visible_commands=commands,
        environment_commands=commands,
        budget_state=BudgetState(),
    )
    return process_completed_generation(
        raw_response=raw_response,
        visible_admissible_commands=commands,
        precondition_result=precondition,
    )


def _input(
    *,
    raw_response: str,
    commands: tuple[str, ...] = (
        "look",
        "inventory",
        "look",
    ),
    accepted_result: StepPublicState | None = None,
    infrastructure: bool = False,
) -> TraceAssemblyInput:
    decision = _decision(
        raw_response=raw_response,
        commands=commands,
    )

    if decision.should_call_env:
        decision = finalize_environment_result(
            decision,
            environment_terminated=(
                False
                if accepted_result is None
                else accepted_result.done
            ),
            infrastructure_error=infrastructure,
        )

    return TraceAssemblyInput(
        provenance=_provenance(
            provider_request_id="provider-request"
        ),
        model_call_index=0,
        public_task_goal="put the object away",
        observation="before",
        prompt_text="RAW_POLICY_PROMPT_V1\n...",
        menu=_menu(commands),
        generation=_generation(raw_response),
        decision=decision,
        accepted_result=accepted_result,
        environment_exception_type=(
            "RuntimeError"
            if infrastructure
            else None
        ),
    )


def test_trace_assembler_builds_nonexecuted_executed_and_environment_error_traces() -> None:
    format_trace = assemble_action_trace(
        _input(raw_response="not-json")
    )
    assert format_trace.execution_status is (
        ExecutionStatus.NOT_EXECUTED
    )
    assert format_trace.attempt_outcome == (
        "FORMAT_PROTOCOL_FAILURE"
    )
    assert format_trace.environment_step_index is None
    assert format_trace.resulting_observation is None

    off_list_trace = assemble_action_trace(
        _input(
            raw_response='{"action":"go north"}'
        )
    )
    assert off_list_trace.execution_status is (
        ExecutionStatus.NOT_EXECUTED
    )
    assert off_list_trace.attempt_outcome == (
        "ACTION_NOT_ADMISSIBLE"
    )

    executed_result = StepPublicState(
        observation="after",
        menu=_menu(("inventory",)),
        score=0,
        done=False,
        won=False,
    )
    executed_trace = assemble_action_trace(
        _input(
            raw_response='{"action":"look"}',
            accepted_result=executed_result,
        )
    )
    assert executed_trace.execution_status is (
        ExecutionStatus.EXECUTED
    )
    assert executed_trace.attempt_outcome == (
        "ACTION_EXECUTED"
    )
    assert executed_trace.environment_step_index == 0
    assert executed_trace.final_executed_action == "look"
    assert executed_trace.resulting_observation == "after"

    error_trace = assemble_action_trace(
        _input(
            raw_response='{"action":"look"}',
            infrastructure=True,
        )
    )
    assert error_trace.execution_status is (
        ExecutionStatus.ENVIRONMENT_ERROR
    )
    assert error_trace.attempt_outcome == (
        "INFRASTRUCTURE_ERROR"
    )
    assert error_trace.environment_step_index == 0
    assert error_trace.final_executed_action is None
    assert error_trace.resulting_observation is None
    assert error_trace.environment_event_flags.to_python() == {
        "exception_type": "RuntimeError"
    }


def test_trace_assembler_preserves_duplicate_menu_and_exact_action() -> None:
    commands = (
        "look",
        "inventory",
        "look",
    )
    result = StepPublicState(
        observation="after",
        menu=_menu(("inventory",)),
        score=0,
        done=False,
        won=False,
    )

    trace = assemble_action_trace(
        _input(
            raw_response='{"action":"look"}',
            commands=commands,
            accepted_result=result,
        )
    )

    assert trace.admissible_commands == commands
    assert trace.admissible_commands_sha256 == (
        sha256_string_sequence(commands)
    )
    assert trace.literal_action == "look"
    assert trace.normalized_action == "look"
    assert trace.submitted_environment_action == "look"


def test_trace_assembler_does_not_change_action_trace_semantics() -> None:
    result = StepPublicState(
        observation="after",
        menu=_menu(("inventory",)),
        score=0,
        done=False,
        won=False,
    )
    value = _input(
        raw_response='{"action":"look"}',
        accepted_result=result,
    )

    trace = assemble_action_trace(value)

    assert trace.pipeline_variant is PipelineVariant.RAW_V1
    assert trace.stages == ()
    assert trace.parsed_phase is None
    assert trace.model_reason is None
    assert trace.policy_attempt_count_before == (
        value.decision.budget_before.policy_attempt_count
    )
    assert trace.policy_attempt_count_after == (
        value.decision.budget_after.policy_attempt_count
    )
    assert trace.environment_step_count_before == (
        value.decision.budget_before.environment_step_count
    )
    assert trace.environment_step_count_after == (
        value.decision.budget_after.environment_step_count
    )


def test_raw_infos_expert_plan_and_facts_cannot_enter_artifact() -> None:
    assert set(TraceAssemblyInput.__dataclass_fields__) == {
        "provenance",
        "model_call_index",
        "public_task_goal",
        "observation",
        "prompt_text",
        "menu",
        "generation",
        "decision",
        "accepted_result",
        "environment_exception_type",
    }

    forbidden = {
        "infos",
        "raw_infos",
        "expert_plan",
        "policy_commands",
        "facts",
    }
    assert forbidden.isdisjoint(
        TraceAssemblyInput.__dataclass_fields__
    )
