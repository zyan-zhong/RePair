from __future__ import annotations

from dataclasses import FrozenInstanceError
import json

import pytest

from pchsi.evaluation.action_trace import (
    ActionStage,
    ActionTrace,
    ExecutionStatus,
    PipelineVariant,
    StageName,
    StageStatus,
    TraceProvenance,
    freeze_json,
)


def _provenance() -> TraceProvenance:
    return TraceProvenance(
        run_id="run-001",
        task_id="task-001",
        episode_id="episode-001",
        replicate_id=0,
        arm_id="R2_PHASE_CRITICAL",
        code_commit="a" * 40,
        config_sha256="b" * 64,
        provider="openai",
        model_name="model-x",
        model_version="2026-07-01",
        provider_request_id="req-123",
        retry_count=1,
        timestamp_utc="2026-07-28T12:00:00Z",
    )


def _phase_stage() -> ActionStage:
    return ActionStage.build(
        name=StageName.PHASE_CRITICAL_HARNESS,
        status=StageStatus.EXECUTED,
        input_action="look",
        output_action="go to desk 1",
        metadata={
            "reason": "redirect_search",
            "evidence": {"scores": [0.2, 0.8], "trigger": "P4"},
        },
    )


def _trace() -> ActionTrace:
    return ActionTrace.build(
        provenance=_provenance(),
        pipeline_variant=PipelineVariant.PHASE_CRITICAL_V1,
        model_call_index=4,
        environment_step_index=3,
        execution_status=ExecutionStatus.EXECUTED,
        public_task_goal="put the pencil on the shelf",
        observation="You are near desk 1.",
        prompt_text="goal\nobservation\nactions",
        admissible_commands=("look", "go to desk 1"),
        raw_model_response='{"phase":"SEARCH_OBJECT","action":"look"}',
        literal_action="look",
        parsed_phase="SEARCH_OBJECT",
        model_reason="inspect",
        parser_status="json_action",
        parser_error=None,
        parser_metadata={"was_fenced": False},
        literal_action_exactly_admissible=True,
        literal_action_casefold_admissible=True,
        stages=(_phase_stage(),),
        final_executed_action="go to desk 1",
        final_action_admissible=True,
    )


def test_structured_metadata_is_deeply_immutable() -> None:
    stage = _phase_stage()
    assert stage.to_dict()["metadata"]["evidence"]["scores"] == [0.2, 0.8]
    with pytest.raises(FrozenInstanceError):
        stage.output_action = "look"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        stage.metadata.items.append(("x", 1))  # type: ignore[attr-defined]


def test_metadata_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match="NaN or infinity"):
        freeze_json({"score": float("nan")})


def test_trace_preserves_phase_and_reproducibility_provenance() -> None:
    payload = _trace().to_dict()
    assert payload["parsed_phase"] == "SEARCH_OBJECT"
    assert payload["provenance"]["provider_request_id"] == "req-123"
    assert payload["public_task_goal"] == "put the pencil on the shelf"
    assert payload["observation"] == "You are near desk 1."
    assert payload["admissible_commands"] == ["look", "go to desk 1"]


def test_pipeline_order_is_fixed_and_cannot_be_rearranged() -> None:
    wrong = ActionStage.build(
        name=StageName.HISTORICAL_ACTION_GUARD,
        status=StageStatus.EXECUTED,
        input_action="look",
        output_action="look",
    )
    with pytest.raises(ValueError, match="fixed pipeline order"):
        ActionTrace.build(
            provenance=_provenance(),
            pipeline_variant=PipelineVariant.HISTORICAL_V7B3C,
            model_call_index=0,
            environment_step_index=0,
            execution_status=ExecutionStatus.EXECUTED,
            public_task_goal="goal",
            observation="obs",
            prompt_text="prompt",
            admissible_commands=("look",),
            raw_model_response='{"action":"look"}',
            literal_action="look",
            parsed_phase=None,
            model_reason=None,
            parser_status="json_action",
            parser_error=None,
            parser_metadata=None,
            literal_action_exactly_admissible=True,
            literal_action_casefold_admissible=True,
            stages=(wrong,),
            final_executed_action="look",
            final_action_admissible=True,
        )


def test_historical_branch_can_record_skipped_action_guard_without_flattening() -> None:
    phase = ActionStage.build(
        name=StageName.HISTORICAL_PHASE_CONTROLLER,
        status=StageStatus.EXECUTED,
        input_action="done",
        output_action="take pencil 1 from desk 1",
        metadata={"phaseaware_reason": "visible_take"},
    )
    guard = ActionStage.build(
        name=StageName.HISTORICAL_ACTION_GUARD,
        status=StageStatus.SKIPPED,
        input_action="take pencil 1 from desk 1",
        output_action="take pencil 1 from desk 1",
        metadata={"skip_reason": "phaseaware_action_lock"},
    )
    trace = ActionTrace.build(
        provenance=_provenance(),
        pipeline_variant=PipelineVariant.HISTORICAL_V7B3C,
        model_call_index=1,
        environment_step_index=1,
        execution_status=ExecutionStatus.EXECUTED,
        public_task_goal="put pencil on shelf",
        observation="pencil is visible",
        prompt_text="prompt",
        admissible_commands=("take pencil 1 from desk 1",),
        raw_model_response='{"action":"done"}',
        literal_action="done",
        parsed_phase="DONE",
        model_reason=None,
        parser_status="json_action",
        parser_error=None,
        parser_metadata=None,
        literal_action_exactly_admissible=False,
        literal_action_casefold_admissible=False,
        stages=(phase, guard),
        final_executed_action="take pencil 1 from desk 1",
        final_action_admissible=True,
    )
    payload = trace.to_dict()
    assert payload["stages"][1]["status"] == "skipped"
    assert payload["stages"][1]["changed"] is False


def test_raw_pipeline_has_no_historical_controller_fields() -> None:
    trace = ActionTrace.build(
        provenance=_provenance(),
        pipeline_variant=PipelineVariant.RAW_V1,
        model_call_index=1,
        environment_step_index=1,
        execution_status=ExecutionStatus.EXECUTED,
        public_task_goal="goal",
        observation="obs",
        prompt_text="prompt",
        admissible_commands=("look",),
        raw_model_response='{"action":"look"}',
        literal_action="look",
        parsed_phase=None,
        model_reason=None,
        parser_status="json_action",
        parser_error=None,
        parser_metadata=None,
        literal_action_exactly_admissible=True,
        literal_action_casefold_admissible=True,
        stages=(),
        final_executed_action="look",
        final_action_admissible=True,
    )
    assert trace.to_dict()["stages"] == []


def test_non_executed_parse_failure_is_traceable_without_environment_step() -> None:
    trace = ActionTrace.build(
        provenance=_provenance(),
        pipeline_variant=PipelineVariant.RAW_V1,
        model_call_index=2,
        environment_step_index=None,
        execution_status=ExecutionStatus.NOT_EXECUTED,
        public_task_goal="goal",
        observation="obs",
        prompt_text="prompt",
        admissible_commands=("look",),
        raw_model_response="explanation only",
        literal_action="",
        parsed_phase=None,
        model_reason=None,
        parser_status="unparseable_response",
        parser_error="JSON parse failed",
        parser_metadata=None,
        literal_action_exactly_admissible=False,
        literal_action_casefold_admissible=False,
        stages=(),
        final_executed_action=None,
        final_action_admissible=None,
    )
    assert trace.environment_step_index is None
    assert trace.to_dict()["execution_status"] == "not_executed"


def test_json_serialisation_is_deterministic() -> None:
    trace = _trace()
    assert trace.to_json() == trace.to_json()
    assert json.loads(trace.to_json()) == trace.to_dict()


# ---------------------------------------------------------------------------
# Task 5A: v3.3 provenance and environment-error compatibility
# ---------------------------------------------------------------------------

from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    sha256_executed_transitions,
)


def test_execution_status_includes_environment_error() -> None:
    assert (
        ExecutionStatus.ENVIRONMENT_ERROR.value
        == "environment_error"
    )


def test_old_provenance_constructor_defaults_new_fields(
) -> None:
    provenance = _provenance()
    payload = provenance.to_dict()

    assert payload[
        "split_and_access_version"
    ] is None
    assert payload["split_name"] is None
    assert payload["access_mode"] is None
    assert payload["policy_version"] is None
    assert payload["seed"] is None
    assert payload["memory_version"] is None
    assert payload[
        "memory_state_sha256"
    ] is None


def test_e1_dev_provenance_round_trip() -> None:
    provenance = TraceProvenance(
        run_id="run-dev",
        task_id="task-dev",
        episode_id="episode-dev",
        replicate_id=0,
        arm_id="E1_DEV_RAW",
        code_commit="a" * 40,
        config_sha256="b" * 64,
        provider="local",
        model_name="Qwen2.5-3B-Instruct",
        model_version=(
            "aa8e72537993ba99e69dfaafa59ed015"
            "b17504d1"
        ),
        provider_request_id=None,
        retry_count=0,
        timestamp_utc="2026-08-03T05:00:00Z",
        split_and_access_version=(
            "SPLIT_AND_ACCESS_V1"
        ),
        split_name="E1-Dev",
        access_mode="development_visible",
        policy_version="pi0",
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256="c" * 64,
    )

    payload = provenance.to_dict()

    assert payload[
        "split_and_access_version"
    ] == "SPLIT_AND_ACCESS_V1"
    assert payload["split_name"] == "E1-Dev"
    assert payload[
        "access_mode"
    ] == "development_visible"
    assert payload["policy_version"] == "pi0"
    assert payload["seed"] == 17
    assert payload[
        "memory_version"
    ] == "MEMORY_M0_V1"
    assert payload[
        "memory_state_sha256"
    ] == "c" * 64


def test_e1_confirmatory_provenance_is_distinct(
) -> None:
    provenance = TraceProvenance(
        run_id="run-confirmatory",
        task_id="task-confirmatory",
        episode_id="episode-confirmatory",
        replicate_id=0,
        arm_id="E1_CONFIRMATORY_RAW",
        code_commit="a" * 40,
        config_sha256="b" * 64,
        provider="local",
        model_name="Qwen2.5-3B-Instruct",
        model_version=(
            "aa8e72537993ba99e69dfaafa59ed015"
            "b17504d1"
        ),
        provider_request_id=None,
        retry_count=0,
        timestamp_utc="2026-08-03T05:00:00Z",
        split_and_access_version=(
            "SPLIT_AND_ACCESS_V1"
        ),
        split_name="E1-Confirmatory",
        access_mode="sealed_confirmatory",
        policy_version="pi0",
        seed=31,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256="d" * 64,
    )

    payload = provenance.to_dict()

    assert (
        payload["split_name"]
        == "E1-Confirmatory"
    )
    assert (
        payload["access_mode"]
        == "sealed_confirmatory"
    )
    assert payload["seed"] == 31


@pytest.mark.parametrize(
    "invalid_hash",
    [
        "",
        "abc",
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "A" * 64,
    ],
)
def test_invalid_memory_state_sha256_is_rejected(
    invalid_hash: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="memory_state_sha256",
    ):
        TraceProvenance(
            run_id="run-invalid",
            task_id="task-invalid",
            episode_id="episode-invalid",
            replicate_id=0,
            arm_id="E1_DEV_RAW",
            code_commit="a" * 40,
            config_sha256="b" * 64,
            provider="local",
            model_name="model",
            model_version=None,
            provider_request_id=None,
            retry_count=0,
            timestamp_utc=(
                "2026-08-03T05:00:00Z"
            ),
            memory_state_sha256=invalid_hash,
        )


def test_memory_m0_golden_hash_remains_frozen(
) -> None:
    transitions = (
        ExecutedTransition(
            action="look",
            resulting_observation=(
                "You see a desk."
            ),
        ),
    )

    assert sha256_executed_transitions(
        transitions
    ) == (
        "af30775b5c2278a829632643ee4a6752c"
        "68b2d729d84d5dcb9871e2a097637aa"
    )


# ---------------------------------------------------------------------------
# Task 5B: Runtime Core attribution and environment-result fields
# ---------------------------------------------------------------------------

from dataclasses import replace

from pchsi.evaluation.action_trace import (
    EMPTY_METADATA,
    sha256_text,
)


def _runtime_trace_kwargs() -> dict[str, object]:
    """Return one complete successful RAW_V1 trace input."""

    return {
        "provenance": _e1_runtime_provenance(),
        "pipeline_variant": PipelineVariant.RAW_V1,
        "model_call_index": 0,
        "environment_step_index": 0,
        "execution_status": ExecutionStatus.EXECUTED,
        "public_task_goal": "put pencil on shelf",
        "observation": "You are near desk 1.",
        "prompt_text": "prompt",
        "admissible_commands": (
            "look",
            "go to desk 1",
        ),
        "raw_model_response": (
            '{"action":"look"}'
        ),
        "literal_action": "look",
        "parsed_phase": None,
        "model_reason": None,
        "parser_status": "success",
        "parser_error": None,
        "parser_metadata": None,
        "literal_action_exactly_admissible": True,
        "literal_action_casefold_admissible": True,
        "stages": (),
        "final_executed_action": "look",
        "final_action_admissible": True,
        "attempt_outcome": "ACTION_EXECUTED",
        "failure_stage": None,
        "failure_code": None,
        "normalized_action": "look",
        "admissibility_status": "exact_member",
        "feedback_code": None,
        "policy_attempt_count_before": 0,
        "policy_attempt_count_after": 1,
        "environment_step_count_before": 0,
        "environment_step_count_after": 1,
        "protocol_failure_count": 0,
        "inadmissible_action_count": 0,
        "consecutive_nonexecuted_attempt_count": 0,
        "episode_termination_reason": None,
        "submitted_environment_action": "look",
        "resulting_observation": (
            "You see a desk."
        ),
        "environment_event_flags": {
            "state_changed": True,
        },
        "protocol_failure_count_before": 0,
        "inadmissible_action_count_before": 0,
        "consecutive_nonexecuted_attempt_count_before": 0,
    }


def _build_runtime_trace(
    **overrides: object,
) -> ActionTrace:
    kwargs = _runtime_trace_kwargs()
    kwargs.update(overrides)

    return ActionTrace.build(
        **kwargs  # type: ignore[arg-type]
    )


def test_old_action_trace_defaults_new_runtime_fields(
) -> None:
    trace = _trace()
    payload = trace.to_dict()

    for name in (
        "attempt_outcome",
        "failure_stage",
        "failure_code",
        "normalized_action",
        "admissibility_status",
        "feedback_code",
        "policy_attempt_count_before",
        "policy_attempt_count_after",
        "environment_step_count_before",
        "environment_step_count_after",
        "protocol_failure_count",
        "inadmissible_action_count",
        "consecutive_nonexecuted_attempt_count",
        "episode_termination_reason",
        "submitted_environment_action",
        "resulting_observation",
        "resulting_observation_sha256",
        "protocol_failure_count_before",
        "inadmissible_action_count_before",
        "consecutive_nonexecuted_attempt_count_before",
    ):
        assert payload[name] is None

    assert payload[
        "environment_event_flags"
    ] == {}


def test_format_failure_runtime_trace_is_coherent(
) -> None:
    trace = _build_runtime_trace(
        environment_step_index=None,
        execution_status=(
            ExecutionStatus.NOT_EXECUTED
        ),
        raw_model_response="explanation only",
        literal_action="",
        parser_status="failed",
        parser_error="ENVELOPE_INVALID_JSON",
        literal_action_exactly_admissible=False,
        literal_action_casefold_admissible=False,
        final_executed_action=None,
        final_action_admissible=None,
        attempt_outcome=(
            "FORMAT_PROTOCOL_FAILURE"
        ),
        failure_stage="envelope",
        failure_code="ENVELOPE_INVALID_JSON",
        normalized_action=None,
        admissibility_status="not_checked",
        feedback_code="FORMAT_ERROR_V1",
        policy_attempt_count_before=0,
        policy_attempt_count_after=1,
        environment_step_count_before=0,
        environment_step_count_after=0,
        protocol_failure_count=1,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=1,
        episode_termination_reason=None,
        submitted_environment_action=None,
        resulting_observation=None,
        environment_event_flags=None,
    )

    payload = trace.to_dict()

    assert payload[
        "attempt_outcome"
    ] == "FORMAT_PROTOCOL_FAILURE"
    assert payload["failure_stage"] == "envelope"
    assert payload[
        "failure_code"
    ] == "ENVELOPE_INVALID_JSON"
    assert payload["normalized_action"] is None
    assert payload[
        "admissibility_status"
    ] == "not_checked"
    assert payload[
        "feedback_code"
    ] == "FORMAT_ERROR_V1"
    assert payload[
        "environment_step_index"
    ] is None
    assert payload[
        "submitted_environment_action"
    ] is None
    assert payload[
        "resulting_observation"
    ] is None
    assert payload[
        "resulting_observation_sha256"
    ] is None


def test_admissibility_failure_has_parser_success(
) -> None:
    trace = _build_runtime_trace(
        environment_step_index=None,
        execution_status=(
            ExecutionStatus.NOT_EXECUTED
        ),
        raw_model_response='{"action":"LOOK"}',
        literal_action="LOOK",
        parser_status="success",
        parser_error=None,
        literal_action_exactly_admissible=False,
        literal_action_casefold_admissible=True,
        final_executed_action=None,
        final_action_admissible=None,
        attempt_outcome=(
            "ACTION_NOT_ADMISSIBLE"
        ),
        failure_stage="admissibility",
        failure_code="ACTION_NOT_ADMISSIBLE",
        normalized_action="LOOK",
        admissibility_status="not_admissible",
        feedback_code="INVALID_ACTION_V1",
        model_call_index=2,
        policy_attempt_count_before=2,
        policy_attempt_count_after=3,
        environment_step_count_before=2,
        environment_step_count_after=2,
        protocol_failure_count=0,
        inadmissible_action_count=1,
        consecutive_nonexecuted_attempt_count=1,
        episode_termination_reason=None,
        submitted_environment_action=None,
        resulting_observation=None,
        environment_event_flags=None,
    )

    payload = trace.to_dict()

    assert payload["parser_status"] == "success"
    assert payload["parser_error"] is None
    assert payload[
        "attempt_outcome"
    ] == "ACTION_NOT_ADMISSIBLE"
    assert payload[
        "failure_stage"
    ] == "admissibility"
    assert payload[
        "normalized_action"
    ] == "LOOK"
    assert payload[
        "environment_step_count_before"
    ] == 2
    assert payload[
        "environment_step_count_after"
    ] == 2


def test_executed_runtime_trace_records_exact_counters_and_result(
) -> None:
    trace = _build_runtime_trace()

    assert trace.execution_status is (
        ExecutionStatus.EXECUTED
    )
    assert trace.environment_step_index == 0
    assert trace.policy_attempt_count_before == 0
    assert trace.policy_attempt_count_after == 1
    assert trace.environment_step_count_before == 0
    assert trace.environment_step_count_after == 1
    assert trace.submitted_environment_action == "look"
    assert trace.resulting_observation == (
        "You see a desk."
    )
    assert trace.resulting_observation_sha256 == (
        sha256_text("You see a desk.")
    )
    assert trace.environment_event_flags.to_python() == {
        "state_changed": True,
    }


def test_infrastructure_error_trace_is_coherent(
) -> None:
    trace = _build_runtime_trace(
        execution_status=(
            ExecutionStatus.ENVIRONMENT_ERROR
        ),
        final_executed_action=None,
        final_action_admissible=None,
        attempt_outcome="INFRASTRUCTURE_ERROR",
        failure_stage="infrastructure",
        failure_code="ENVIRONMENT_STEP_FAILED",
        normalized_action="look",
        admissibility_status="exact_member",
        feedback_code=None,
        policy_attempt_count_before=0,
        policy_attempt_count_after=1,
        environment_step_count_before=0,
        environment_step_count_after=1,
        protocol_failure_count=0,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=0,
        episode_termination_reason=(
            "INFRASTRUCTURE_ERROR"
        ),
        submitted_environment_action="look",
        resulting_observation=None,
        environment_event_flags={
            "exception_type": "RuntimeError",
        },
    )

    payload = trace.to_dict()

    assert payload[
        "execution_status"
    ] == "environment_error"
    assert payload[
        "attempt_outcome"
    ] == "INFRASTRUCTURE_ERROR"
    assert payload[
        "failure_stage"
    ] == "infrastructure"
    assert payload[
        "failure_code"
    ] == "ENVIRONMENT_STEP_FAILED"
    assert payload[
        "environment_step_index"
    ] == 0
    assert payload[
        "submitted_environment_action"
    ] == "look"
    assert payload[
        "final_executed_action"
    ] is None
    assert payload[
        "resulting_observation"
    ] is None
    assert payload[
        "resulting_observation_sha256"
    ] is None
    assert payload[
        "environment_step_count_after"
    ] == (
        payload[
            "environment_step_count_before"
        ]
        + 1
    )


@pytest.mark.parametrize(
    (
        "overrides",
        "expected_match",
    ),
    [
        (
            {
                "policy_attempt_count_before": 2,
                "policy_attempt_count_after": 2,
            },
            "policy_attempt_count",
        ),
        (
            {
                "environment_step_count_before": 2,
                "environment_step_count_after": 1,
            },
            "environment_step_count",
        ),
        (
            {
                "environment_step_count_before": 0,
                "environment_step_count_after": 2,
            },
            "environment_step_count",
        ),
    ],
)
def test_runtime_counters_reject_invalid_transitions(
    overrides: dict[str, object],
    expected_match: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_match,
    ):
        _build_runtime_trace(
            **overrides
        )


def test_nonexecuted_attempt_cannot_increment_environment_count(
) -> None:
    with pytest.raises(
        ValueError,
        match="environment_step_count",
    ):
        _build_runtime_trace(
            environment_step_index=None,
            execution_status=(
                ExecutionStatus.NOT_EXECUTED
            ),
            raw_model_response="bad response",
            literal_action="",
            parser_status="failed",
            parser_error="ENVELOPE_INVALID_JSON",
            literal_action_exactly_admissible=False,
            literal_action_casefold_admissible=False,
            final_executed_action=None,
            final_action_admissible=None,
            attempt_outcome=(
                "FORMAT_PROTOCOL_FAILURE"
            ),
            failure_stage="envelope",
            failure_code=(
                "ENVELOPE_INVALID_JSON"
            ),
            normalized_action=None,
            admissibility_status="not_checked",
            feedback_code="FORMAT_ERROR_V1",
            policy_attempt_count_before=0,
            policy_attempt_count_after=1,
            environment_step_count_before=0,
            environment_step_count_after=1,
            protocol_failure_count=1,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=1,
            episode_termination_reason=None,
            submitted_environment_action=None,
            resulting_observation=None,
            environment_event_flags=None,
        )


def test_infrastructure_error_rejects_fabricated_observation(
) -> None:
    with pytest.raises(
        ValueError,
        match="resulting_observation",
    ):
        _build_runtime_trace(
            execution_status=(
                ExecutionStatus.ENVIRONMENT_ERROR
            ),
            final_executed_action=None,
            final_action_admissible=None,
            attempt_outcome="INFRASTRUCTURE_ERROR",
            failure_stage="infrastructure",
            failure_code="ENVIRONMENT_STEP_FAILED",
            normalized_action="look",
            admissibility_status="exact_member",
            feedback_code=None,
            episode_termination_reason=(
                "INFRASTRUCTURE_ERROR"
            ),
            submitted_environment_action="look",
            resulting_observation=(
                "fabricated observation"
            ),
        )


def test_resulting_observation_hash_mismatch_is_rejected(
) -> None:
    trace = _build_runtime_trace()

    with pytest.raises(
        ValueError,
        match="resulting_observation_sha256",
    ):
        replace(
            trace,
            resulting_observation_sha256=(
                "0" * 64
            ),
        )


def test_runtime_trace_json_is_deterministic_and_complete(
) -> None:
    trace = _build_runtime_trace()

    first = trace.to_json()
    second = trace.to_json()

    assert first == second
    assert first.encode("utf-8") == second.encode(
        "utf-8"
    )

    payload = json.loads(first)

    assert payload["attempt_outcome"] == (
        "ACTION_EXECUTED"
    )
    assert payload[
        "submitted_environment_action"
    ] == "look"
    assert payload[
        "resulting_observation"
    ] == "You see a desk."
    assert payload[
        "resulting_observation_sha256"
    ] == sha256_text(
        "You see a desk."
    )
    assert payload[
        "environment_event_flags"
    ] == {
        "state_changed": True,
    }

    assert trace.environment_event_flags is not (
        EMPTY_METADATA
    )


# BEGIN E1_ACTION_TRACE_CONSISTENCY_RED_A
# These tests freeze provenance, RAW-scope, parser/outcome, action-fact,
# and environment-event consistency before production changes.


def _e1_runtime_provenance() -> TraceProvenance:
    return replace(
        _provenance(),
        arm_id="E1_DEV_RAW",
        provider="local",
        split_and_access_version=(
            "SPLIT_AND_ACCESS_V1"
        ),
        split_name="E1-Dev",
        access_mode="development_visible",
        policy_version="pi0",
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256="c" * 64,
    )


def _merged_runtime_case(
    base: dict[str, object],
    **changes: object,
) -> dict[str, object]:
    result = dict(base)
    result.update(changes)
    return result


def _format_runtime_overrides(
) -> dict[str, object]:
    return {
        "provenance": _e1_runtime_provenance(),
        "model_call_index": 0,
        "environment_step_index": None,
        "execution_status": (
            ExecutionStatus.NOT_EXECUTED
        ),
        "raw_model_response": "explanation only",
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
        "episode_termination_reason": None,
        "submitted_environment_action": None,
        "resulting_observation": None,
        "environment_event_flags": None,
    }


def _off_list_runtime_overrides(
) -> dict[str, object]:
    return {
        "provenance": _e1_runtime_provenance(),
        "model_call_index": 0,
        "environment_step_index": None,
        "execution_status": (
            ExecutionStatus.NOT_EXECUTED
        ),
        "raw_model_response": (
            '{"action":"LOOK"}'
        ),
        "literal_action": "LOOK",
        "parser_status": "success",
        "parser_error": None,
        "literal_action_exactly_admissible": False,
        "literal_action_casefold_admissible": True,
        "final_executed_action": None,
        "final_action_admissible": None,
        "attempt_outcome": (
            "ACTION_NOT_ADMISSIBLE"
        ),
        "failure_stage": "admissibility",
        "failure_code": "ACTION_NOT_ADMISSIBLE",
        "normalized_action": "LOOK",
        "admissibility_status": "not_admissible",
        "feedback_code": "INVALID_ACTION_V1",
        "policy_attempt_count_before": 0,
        "policy_attempt_count_after": 1,
        "environment_step_count_before": 0,
        "environment_step_count_after": 0,
        "protocol_failure_count": 0,
        "inadmissible_action_count": 1,
        "consecutive_nonexecuted_attempt_count": 1,
        "episode_termination_reason": None,
        "submitted_environment_action": None,
        "resulting_observation": None,
        "environment_event_flags": None,
    }


def _infrastructure_runtime_overrides(
) -> dict[str, object]:
    return {
        "provenance": _e1_runtime_provenance(),
        "model_call_index": 0,
        "environment_step_index": 0,
        "execution_status": (
            ExecutionStatus.ENVIRONMENT_ERROR
        ),
        "literal_action": "look",
        "parser_status": "success",
        "parser_error": None,
        "final_executed_action": None,
        "final_action_admissible": None,
        "attempt_outcome": "INFRASTRUCTURE_ERROR",
        "failure_stage": "infrastructure",
        "failure_code": "ENVIRONMENT_STEP_FAILED",
        "normalized_action": "look",
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
        "submitted_environment_action": "look",
        "resulting_observation": None,
        "environment_event_flags": {
            "exception_type": "RuntimeError",
        },
    }


@pytest.mark.parametrize(
    "field_name",
    [
        "split_and_access_version",
        "split_name",
        "access_mode",
        "policy_version",
        "memory_version",
    ],
)
def test_action_trace_consistency_red_a_optional_provenance_text_rejects_whitespace(
    field_name: str,
) -> None:
    with pytest.raises(ValueError):
        replace(
            _e1_runtime_provenance(),
            **{field_name: " \t "},
        )


@pytest.mark.parametrize(
    "changes",
    [
        {
            "split_and_access_version":
                "SPLIT_AND_ACCESS_V1",
            "split_name": None,
            "access_mode": None,
        },
        {
            "split_and_access_version":
                "SPLIT_AND_ACCESS_V1",
            "split_name": "E1-Dev",
            "access_mode": None,
        },
    ],
)
def test_action_trace_consistency_red_a_split_bundle_is_all_or_none(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        replace(
            _provenance(),
            **changes,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {
            "memory_version": "MEMORY_M0_V1",
            "memory_state_sha256": None,
        },
        {
            "memory_version": None,
            "memory_state_sha256": "c" * 64,
        },
    ],
)
def test_action_trace_consistency_red_a_memory_bundle_is_all_or_none(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        replace(
            _provenance(),
            **changes,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "split_and_access_version",
        "split_name",
        "access_mode",
        "policy_version",
        "seed",
        "memory_version",
        "memory_state_sha256",
    ],
)
def test_action_trace_consistency_red_a_runtime_trace_requires_complete_provenance(
    field_name: str,
) -> None:
    with pytest.raises(ValueError):
        incomplete = replace(
            _e1_runtime_provenance(),
            **{field_name: None},
        )

        _build_runtime_trace(
            provenance=incomplete,
        )


def test_action_trace_consistency_red_a_runtime_fields_reject_phase_critical_pipeline(
) -> None:
    stage = ActionStage.build(
        name=StageName.PHASE_CRITICAL_HARNESS,
        status=StageStatus.EXECUTED,
        input_action="look",
        output_action="look",
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            provenance=_e1_runtime_provenance(),
            pipeline_variant=(
                PipelineVariant.PHASE_CRITICAL_V1
            ),
            stages=(stage,),
        )


def test_action_trace_consistency_red_a_runtime_fields_reject_historical_pipeline(
) -> None:
    phase = ActionStage.build(
        name=StageName.HISTORICAL_PHASE_CONTROLLER,
        status=StageStatus.EXECUTED,
        input_action="look",
        output_action="look",
    )

    guard = ActionStage.build(
        name=StageName.HISTORICAL_ACTION_GUARD,
        status=StageStatus.EXECUTED,
        input_action="look",
        output_action="look",
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            provenance=_e1_runtime_provenance(),
            pipeline_variant=(
                PipelineVariant.HISTORICAL_V7B3C
            ),
            stages=(phase, guard),
        )


def test_action_trace_consistency_red_a_runtime_fields_reject_parsed_phase(
) -> None:
    with pytest.raises(ValueError):
        _build_runtime_trace(
            provenance=_e1_runtime_provenance(),
            parsed_phase="SEARCH_OBJECT",
        )


def test_action_trace_consistency_red_a_runtime_fields_reject_model_reason(
) -> None:
    with pytest.raises(ValueError):
        _build_runtime_trace(
            provenance=_e1_runtime_provenance(),
            model_reason="inspect",
        )


def test_action_trace_consistency_red_a_format_requires_failed_parser_status(
) -> None:
    kwargs = _merged_runtime_case(
        _format_runtime_overrides(),
        parser_status="success",
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )


def test_action_trace_consistency_red_a_off_list_requires_successful_parser_status(
) -> None:
    kwargs = _merged_runtime_case(
        _off_list_runtime_overrides(),
        parser_status="failed",
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )


def test_action_trace_consistency_red_a_executed_requires_successful_parser_status(
) -> None:
    with pytest.raises(ValueError):
        _build_runtime_trace(
            provenance=_e1_runtime_provenance(),
            parser_status="failed",
        )


def test_action_trace_consistency_red_a_infrastructure_requires_successful_parser_status(
) -> None:
    kwargs = _merged_runtime_case(
        _infrastructure_runtime_overrides(),
        parser_status="failed",
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )


def test_action_trace_consistency_red_a_format_requires_empty_literal_action(
) -> None:
    kwargs = _merged_runtime_case(
        _format_runtime_overrides(),
        literal_action="explanation only",
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )


def test_action_trace_consistency_red_a_off_list_literal_matches_normalized_action(
) -> None:
    kwargs = _merged_runtime_case(
        _off_list_runtime_overrides(),
        literal_action="look",
        normalized_action="LOOK",
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )


def test_action_trace_consistency_red_a_executed_requires_true_final_admissibility(
) -> None:
    with pytest.raises(ValueError):
        _build_runtime_trace(
            provenance=_e1_runtime_provenance(),
            final_action_admissible=False,
        )


def test_action_trace_consistency_red_a_executed_clears_consecutive_counter(
) -> None:
    with pytest.raises(ValueError):
        _build_runtime_trace(
            provenance=_e1_runtime_provenance(),
            consecutive_nonexecuted_attempt_count=1,
        )


def test_action_trace_consistency_red_a_infrastructure_clears_consecutive_counter(
) -> None:
    kwargs = _merged_runtime_case(
        _infrastructure_runtime_overrides(),
        consecutive_nonexecuted_attempt_count=1,
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )


@pytest.mark.parametrize(
    "case_factory",
    [
        _format_runtime_overrides,
        _off_list_runtime_overrides,
    ],
    ids=[
        "format",
        "off_list",
    ],
)
def test_action_trace_consistency_red_a_nonexecuted_outcomes_require_empty_flags(
    case_factory: object,
) -> None:
    kwargs = case_factory()  # type: ignore[operator]
    kwargs["environment_event_flags"] = {
        "unexpected": True,
    }

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )


@pytest.mark.parametrize(
    "invalid_flags",
    [
        {},
        {
            "unknown": "value",
        },
        {
            "exception_type": "   ",
        },
        {
            "result": {
                "success": True,
            },
        },
    ],
)
def test_action_trace_consistency_red_a_infrastructure_flags_use_exact_schema(
    invalid_flags: dict[str, object],
) -> None:
    kwargs = _merged_runtime_case(
        _infrastructure_runtime_overrides(),
        environment_event_flags=invalid_flags,
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )
# END E1_ACTION_TRACE_CONSISTENCY_RED_A


# BEGIN E1_ACTION_TRACE_CONSISTENCY_RED_B
# These tests freeze counter lineage, exact outcome transitions,
# cumulative conservation, index alignment, and serialization.


from dataclasses import fields as dataclass_fields


_LINEAGE_FIELD_NAMES = (
    "protocol_failure_count_before",
    "inadmissible_action_count_before",
    "consecutive_nonexecuted_attempt_count_before",
)


def _lineage_runtime_case(
    case_name: str,
) -> dict[str, object]:
    if case_name == "format":
        base = _format_runtime_overrides()

    elif case_name == "off_list":
        base = _off_list_runtime_overrides()

    elif case_name == "executed":
        base = {
            "provenance":
                _e1_runtime_provenance(),
        }

    elif case_name == "infrastructure":
        base = _infrastructure_runtime_overrides()

    else:
        raise AssertionError(
            f"unknown case: {case_name}"
        )

    return _merged_runtime_case(
        base,
        protocol_failure_count_before=0,
        inadmissible_action_count_before=0,
        consecutive_nonexecuted_attempt_count_before=0,
    )


def _build_lineage_runtime_case(
    case_name: str,
    **changes: object,
) -> ActionTrace:
    kwargs = _lineage_runtime_case(
        case_name
    )

    kwargs.update(changes)

    return _build_runtime_trace(
        **kwargs,
    )


def test_action_trace_consistency_red_b_lineage_fields_are_appended(
) -> None:
    names = tuple(
        item.name
        for item in dataclass_fields(
            ActionTrace
        )
    )

    assert names[-3:] == (
        _LINEAGE_FIELD_NAMES
    )


def test_action_trace_consistency_red_b_legacy_serialization_defaults_lineage_to_none(
) -> None:
    payload = _trace().to_dict()

    for field_name in (
        _LINEAGE_FIELD_NAMES
    ):
        assert field_name in payload
        assert payload[field_name] is None


@pytest.mark.parametrize(
    "case_name",
    [
        "format",
        "off_list",
        "executed",
        "infrastructure",
    ],
)
def test_action_trace_consistency_red_b_valid_transition_matrix_is_accepted(
    case_name: str,
) -> None:
    trace = _build_lineage_runtime_case(
        case_name
    )

    assert trace.attempt_outcome is not None


@pytest.mark.parametrize(
    (
        "field_name",
        "invalid_value",
        "expected_error",
    ),
    [
        (
            "protocol_failure_count_before",
            -1,
            ValueError,
        ),
        (
            "inadmissible_action_count_before",
            -1,
            ValueError,
        ),
        (
            "consecutive_nonexecuted_attempt_count_before",
            -1,
            ValueError,
        ),
        (
            "protocol_failure_count_before",
            True,
            TypeError,
        ),
        (
            "inadmissible_action_count_before",
            True,
            TypeError,
        ),
        (
            "consecutive_nonexecuted_attempt_count_before",
            True,
            TypeError,
        ),
    ],
)
def test_action_trace_consistency_red_b_before_counter_validation(
    field_name: str,
    invalid_value: object,
    expected_error: type[Exception],
) -> None:
    names = {
        item.name
        for item in dataclass_fields(
            ActionTrace
        )
    }

    assert field_name in names

    kwargs = _lineage_runtime_case(
        "executed"
    )

    kwargs[field_name] = invalid_value

    with pytest.raises(
        expected_error
    ):
        _build_runtime_trace(
            **kwargs,
        )


@pytest.mark.parametrize(
    "partial_lineage",
    [
        {
            "protocol_failure_count_before": 0,
        },
        {
            "protocol_failure_count_before": 0,
            "inadmissible_action_count_before": 0,
        },
    ],
)
def test_action_trace_consistency_red_b_partial_lineage_is_rejected(
    partial_lineage: dict[str, object],
) -> None:
    kwargs = _runtime_trace_kwargs()

    for field_name in (
        _LINEAGE_FIELD_NAMES
    ):
        kwargs.pop(
            field_name,
            None,
        )

    kwargs.update(
        partial_lineage
    )

    with pytest.raises(ValueError):
        ActionTrace.build(
            **kwargs,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    (
        "case_name",
        "field_name",
        "invalid_value",
    ),
    [
        (
            "format",
            "protocol_failure_count",
            0,
        ),
        (
            "format",
            "inadmissible_action_count",
            1,
        ),
        (
            "format",
            "consecutive_nonexecuted_attempt_count",
            0,
        ),
        (
            "off_list",
            "protocol_failure_count",
            1,
        ),
        (
            "off_list",
            "inadmissible_action_count",
            0,
        ),
        (
            "off_list",
            "consecutive_nonexecuted_attempt_count",
            0,
        ),
        (
            "executed",
            "protocol_failure_count",
            1,
        ),
        (
            "executed",
            "inadmissible_action_count",
            1,
        ),
        (
            "executed",
            "consecutive_nonexecuted_attempt_count",
            1,
        ),
        (
            "infrastructure",
            "protocol_failure_count",
            1,
        ),
        (
            "infrastructure",
            "inadmissible_action_count",
            1,
        ),
        (
            "infrastructure",
            "consecutive_nonexecuted_attempt_count",
            1,
        ),
    ],
)
def test_action_trace_consistency_red_b_exact_outcome_transition_is_required(
    case_name: str,
    field_name: str,
    invalid_value: int,
) -> None:
    kwargs = _lineage_runtime_case(
        case_name
    )

    kwargs[field_name] = (
        invalid_value
    )

    with pytest.raises(ValueError):
        _build_runtime_trace(
            **kwargs,
        )


def test_action_trace_consistency_red_b_before_counter_conservation_is_required(
) -> None:
    with pytest.raises(
        ValueError,
        match="conservation",
    ):
        _build_lineage_runtime_case(
            "executed",
            model_call_index=1,
            policy_attempt_count_before=1,
            policy_attempt_count_after=2,
        )


def test_action_trace_consistency_red_b_after_counter_conservation_is_required(
) -> None:
    with pytest.raises(
        ValueError,
        match="conservation",
    ):
        _build_lineage_runtime_case(
            "off_list",
            inadmissible_action_count=0,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "environment_step_count_before",
        "protocol_failure_count_before",
        "inadmissible_action_count_before",
    ],
)
def test_action_trace_consistency_red_b_before_components_cannot_exceed_policy(
    field_name: str,
) -> None:
    kwargs = _lineage_runtime_case(
        "executed"
    )

    kwargs.update({
        "model_call_index": 1,
        "policy_attempt_count_before": 1,
        "policy_attempt_count_after": 2,
        field_name: 2,
    })

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        _build_runtime_trace(
            **kwargs,
        )


def test_action_trace_consistency_red_b_model_call_index_matches_policy_before(
) -> None:
    with pytest.raises(
        ValueError,
        match="model_call_index",
    ):
        _build_lineage_runtime_case(
            "executed",
            model_call_index=7,
        )


def test_action_trace_consistency_red_b_executed_environment_index_matches_before_count(
) -> None:
    with pytest.raises(
        ValueError,
        match="environment_step_index",
    ):
        _build_lineage_runtime_case(
            "executed",
            environment_step_index=7,
        )


def test_action_trace_consistency_red_b_infrastructure_environment_index_matches_before_count(
) -> None:
    with pytest.raises(
        ValueError,
        match="environment_step_index",
    ):
        _build_lineage_runtime_case(
            "infrastructure",
            environment_step_index=7,
        )


def test_action_trace_consistency_red_b_serialization_contains_lineage_and_is_deterministic(
) -> None:
    trace = _build_lineage_runtime_case(
        "executed"
    )

    payload = trace.to_dict()

    assert payload[
        "protocol_failure_count_before"
    ] == 0

    assert payload[
        "inadmissible_action_count_before"
    ] == 0

    assert payload[
        "consecutive_nonexecuted_attempt_count_before"
    ] == 0

    assert trace.to_json() == (
        trace.to_json()
    )

    assert json.loads(
        trace.to_json()
    ) == payload


def test_action_trace_consistency_red_b_replace_revalidates_counter_lineage(
) -> None:
    trace = _build_lineage_runtime_case(
        "executed"
    )

    with pytest.raises(ValueError):
        replace(
            trace,
            protocol_failure_count=1,
        )
# END E1_ACTION_TRACE_CONSISTENCY_RED_B


# BEGIN E1_ACTION_TRACE_RED_B_COMPENSATED_MATRIX
# These cases preserve aggregate conservation while assigning the
# completed attempt to the wrong outcome-specific counter.


def test_action_trace_red_b_format_cannot_credit_inadmissible_counter(
) -> None:
    with pytest.raises(ValueError):
        _build_lineage_runtime_case(
            "format",
            protocol_failure_count=0,
            inadmissible_action_count=1,
        )


def test_action_trace_red_b_off_list_cannot_credit_protocol_counter(
) -> None:
    with pytest.raises(ValueError):
        _build_lineage_runtime_case(
            "off_list",
            protocol_failure_count=1,
            inadmissible_action_count=0,
        )


def test_action_trace_red_b_executed_cannot_swap_failure_counter_lineage(
) -> None:
    with pytest.raises(ValueError):
        _build_lineage_runtime_case(
            "executed",
            model_call_index=2,
            policy_attempt_count_before=2,
            policy_attempt_count_after=3,
            environment_step_count_before=0,
            environment_step_count_after=1,
            environment_step_index=0,
            protocol_failure_count_before=1,
            inadmissible_action_count_before=1,
            consecutive_nonexecuted_attempt_count_before=2,
            protocol_failure_count=2,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        )


def test_action_trace_red_b_infrastructure_cannot_swap_failure_counter_lineage(
) -> None:
    with pytest.raises(ValueError):
        _build_lineage_runtime_case(
            "infrastructure",
            model_call_index=2,
            policy_attempt_count_before=2,
            policy_attempt_count_after=3,
            environment_step_count_before=0,
            environment_step_count_after=1,
            environment_step_index=0,
            protocol_failure_count_before=1,
            inadmissible_action_count_before=1,
            consecutive_nonexecuted_attempt_count_before=2,
            protocol_failure_count=2,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        )
# END E1_ACTION_TRACE_RED_B_COMPENSATED_MATRIX

def test_p1_trace_provenance_binds_condition_identity() -> None:
    provenance = TraceProvenance(
        run_id="run-p1",
        task_id="task-1",
        episode_id="p4-P4-R0-PI0-t00001-s0000000017-a000",
        replicate_id=0,
        arm_id="R0_RAW_WITH_MENU_V1",
        code_commit="a" * 40,
        config_sha256="b" * 64,
        provider="vllm",
        model_name="Qwen2.5-3B-Instruct-E1",
        model_version="c" * 64,
        provider_request_id="req",
        retry_count=0,
        timestamp_utc="2026-08-08T00:00:00Z",
        split_and_access_version="P1_B_ACCESS_V1",
        split_name="valid_unseen",
        access_mode="TASK_ACCESS_MANIFEST_V1",
        policy_version="RAW_WITH_MENU_V1",
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256="d" * 64,
        task_access_manifest_sha256="1" * 64,
        policy_condition_manifest_sha256="2" * 64,
        condition_run_schedule_sha256="3" * 64,
        access_class="DEV_VISIBLE",
        policy_condition_id="P4-R0-PI0",
        condition_cell_id="p4-P4-R0-PI0-t00001-s0000000017",
    )
    payload = provenance.to_dict()
    assert payload["access_class"] == "DEV_VISIBLE"
    assert payload["condition_cell_id"].startswith("p4-P4-R0-PI0-")

    with pytest.raises(ValueError, match="supplied together"):
        TraceProvenance(
            run_id="run-p1",
            task_id="task-1",
            episode_id="e",
            replicate_id=0,
            arm_id="R0_RAW_WITH_MENU_V1",
            code_commit="a" * 40,
            config_sha256="b" * 64,
            provider="vllm",
            model_name="m",
            model_version=None,
            provider_request_id=None,
            retry_count=0,
            timestamp_utc="2026-08-08T00:00:00Z",
            task_access_manifest_sha256="1" * 64,
        )
