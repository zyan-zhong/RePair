"""Correct construction of existing ActionTrace records from frozen decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .action_trace import (
    ActionTrace,
    ExecutionStatus,
    PipelineVariant,
    TraceProvenance,
    sha256_string_sequence,
)
from .alfworld_contracts import (
    MenuSnapshot,
    StepPublicState,
)
from .policy_response import PolicyGeneration
from .policy_call_evidence import PolicyCallEvidenceV1
from .runtime_core import (
    AdmissibilityStatus,
    AttemptOutcome,
    RuntimeDecision,
)


@dataclass(frozen=True, slots=True)
class TraceAssemblyInput:
    provenance: TraceProvenance
    model_call_index: int
    public_task_goal: str
    observation: str
    prompt_text: str
    menu: MenuSnapshot
    generation: PolicyGeneration
    decision: RuntimeDecision
    accepted_result: StepPublicState | None = None
    environment_exception_type: str | None = None


def _enum_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        enum_value = value.value
        if not isinstance(enum_value, str):
            raise TypeError(
                "enum value must be str"
            )
        return enum_value
    if isinstance(value, str):
        return value
    raise TypeError(
        "runtime enum-like value must be str, Enum, or None"
    )


def _validate_input(
    value: TraceAssemblyInput,
) -> None:
    if not isinstance(value, TraceAssemblyInput):
        raise TypeError(
            "value must be TraceAssemblyInput"
        )
    if not isinstance(
        value.provenance,
        TraceProvenance,
    ):
        raise TypeError(
            "provenance must be TraceProvenance"
        )
    if not isinstance(value.menu, MenuSnapshot):
        raise TypeError("menu must be MenuSnapshot")
    if (
        value.menu.sequence_sha256
        != sha256_string_sequence(
            value.menu.commands
        )
    ):
        raise ValueError(
            "menu sequence SHA-256 does not match commands"
        )
    if not isinstance(
        value.generation,
        PolicyGeneration,
    ):
        raise TypeError(
            "generation must be PolicyGeneration"
        )
    if not isinstance(
        value.decision,
        RuntimeDecision,
    ):
        raise TypeError(
            "decision must be RuntimeDecision"
        )
    if (
        value.provenance.provider_request_id
        != value.generation.provider_request_id
    ):
        raise ValueError(
            "provider request ID does not match trace provenance"
        )
    if (
        value.model_call_index
        != value.decision.budget_before
        .policy_attempt_count
    ):
        raise ValueError(
            "model_call_index must equal decision budget_before"
        )
    if value.decision.should_call_env:
        raise ValueError(
            "environment-authorized decisions must be finalized "
            "before trace assembly"
        )



def validate_policy_call_trace_alignment(
    *,
    evidence: PolicyCallEvidenceV1,
    trace: ActionTrace,
) -> None:
    # Keep PolicyCall evidence validation outside TraceAssemblyInput so the
    # frozen trace-construction input surface stays closed.
    if not isinstance(evidence, PolicyCallEvidenceV1):
        raise TypeError("evidence must be PolicyCallEvidenceV1")
    if not isinstance(trace, ActionTrace):
        raise TypeError("trace must be ActionTrace")

    if evidence.model_call_index != trace.model_call_index:
        raise ValueError(
            "policy-call model index differs from ActionTrace"
        )
    if evidence.public_task_goal != trace.public_task_goal:
        raise ValueError(
            "policy-call public task goal differs from ActionTrace"
        )
    if evidence.prompt_text != trace.prompt_text:
        raise ValueError("policy-call prompt differs from ActionTrace")
    if evidence.observation != trace.observation:
        raise ValueError(
            "policy-call observation differs from ActionTrace"
        )
    if tuple(evidence.admissible_commands) != tuple(
        trace.admissible_commands
    ):
        raise ValueError("policy-call menu differs from ActionTrace")
    if evidence.raw_response_text != trace.raw_model_response:
        raise ValueError(
            "policy-call raw response differs from ActionTrace"
        )
    if (
        evidence.provider_request_id
        != trace.provenance.provider_request_id
    ):
        raise ValueError(
            "policy-call provider request ID differs from TraceProvenance"
        )

    budget = dict(evidence.budget_before)
    expected_budget = {
        "policy_attempt_count": trace.policy_attempt_count_before,
        "environment_step_count": trace.environment_step_count_before,
        "protocol_failure_count": trace.protocol_failure_count_before,
        "inadmissible_action_count": (
            trace.inadmissible_action_count_before
        ),
        "consecutive_nonexecuted_attempt_count": (
            trace.consecutive_nonexecuted_attempt_count_before
        ),
    }
    if budget != expected_budget:
        raise ValueError(
            "policy-call budget_before differs from ActionTrace counters"
        )

def assemble_action_trace(
    value: TraceAssemblyInput,
) -> ActionTrace:
    _validate_input(value)

    decision = value.decision
    outcome = decision.attempt_outcome
    exact_member = (
        decision.admissibility_status
        is AdmissibilityStatus.EXACT_MEMBER
    )
    literal_action = (
        ""
        if decision.parse_result.normalized_action
        is None
        else decision.parse_result.normalized_action
    )

    environment_step_index: int | None = None
    submitted_action: str | None = None
    resulting_observation: str | None = None
    final_executed_action: str | None = None
    final_action_admissible: bool | None = None
    environment_event_flags: dict[str, object] = {}

    if outcome is AttemptOutcome.ACTION_EXECUTED:
        if not isinstance(
            value.accepted_result,
            StepPublicState,
        ):
            raise TypeError(
                "ACTION_EXECUTED requires accepted_result"
            )
        if value.environment_exception_type is not None:
            raise ValueError(
                "ACTION_EXECUTED cannot have environment_exception_type"
            )
        if decision.candidate_environment_action is None:
            raise ValueError(
                "ACTION_EXECUTED requires candidate environment action"
            )

        execution_status = ExecutionStatus.EXECUTED
        environment_step_index = (
            decision.budget_before
            .environment_step_count
        )
        submitted_action = (
            decision.candidate_environment_action
        )
        resulting_observation = (
            value.accepted_result.observation
        )
        final_executed_action = submitted_action
        final_action_admissible = True

    elif outcome is AttemptOutcome.INFRASTRUCTURE_ERROR:
        if value.accepted_result is not None:
            raise ValueError(
                "INFRASTRUCTURE_ERROR cannot have accepted_result"
            )
        if (
            not isinstance(
                value.environment_exception_type,
                str,
            )
            or not value.environment_exception_type.strip()
        ):
            raise ValueError(
                "INFRASTRUCTURE_ERROR requires a nonblank "
                "environment_exception_type"
            )
        if decision.candidate_environment_action is None:
            raise ValueError(
                "INFRASTRUCTURE_ERROR requires candidate action"
            )

        execution_status = (
            ExecutionStatus.ENVIRONMENT_ERROR
        )
        environment_step_index = (
            decision.budget_before
            .environment_step_count
        )
        submitted_action = (
            decision.candidate_environment_action
        )
        environment_event_flags = {
            "exception_type": (
                value.environment_exception_type
            )
        }

    else:
        if value.accepted_result is not None:
            raise ValueError(
                "nonexecuted outcome cannot have accepted_result"
            )
        if value.environment_exception_type is not None:
            raise ValueError(
                "nonexecuted outcome cannot have "
                "environment_exception_type"
            )
        execution_status = (
            ExecutionStatus.NOT_EXECUTED
        )

    parser_failure_code = (
        _enum_text(
            decision.parse_result.failure_code
        )
    )
    parser_status = _enum_text(
        decision.parse_result.status
    )
    if parser_status is None:
        raise AssertionError(
            "parser status must not be None"
        )

    parser_metadata = {
        "failure_code": parser_failure_code,
        "failure_stage": _enum_text(
            decision.parse_result.failure_stage
        ),
        "status": parser_status,
    }

    return ActionTrace.build(
        provenance=value.provenance,
        pipeline_variant=PipelineVariant.RAW_V1,
        model_call_index=value.model_call_index,
        environment_step_index=(
            environment_step_index
        ),
        execution_status=execution_status,
        public_task_goal=value.public_task_goal,
        observation=value.observation,
        prompt_text=value.prompt_text,
        admissible_commands=value.menu.commands,
        raw_model_response=(
            value.generation.raw_response_text
        ),
        literal_action=literal_action,
        parsed_phase=None,
        model_reason=None,
        parser_status=parser_status,
        parser_error=parser_failure_code,
        parser_metadata=parser_metadata,
        literal_action_exactly_admissible=(
            exact_member
        ),
        literal_action_casefold_admissible=(
            exact_member
        ),
        stages=(),
        final_executed_action=(
            final_executed_action
        ),
        final_action_admissible=(
            final_action_admissible
        ),
        attempt_outcome=outcome.value,
        failure_stage=_enum_text(
            decision.failure_stage
        ),
        failure_code=_enum_text(
            decision.failure_code
        ),
        normalized_action=(
            decision.normalized_action
        ),
        admissibility_status=(
            decision.admissibility_status.value
        ),
        feedback_code=_enum_text(
            decision.feedback_code
        ),
        policy_attempt_count_before=(
            decision.budget_before
            .policy_attempt_count
        ),
        policy_attempt_count_after=(
            decision.budget_after
            .policy_attempt_count
        ),
        environment_step_count_before=(
            decision.budget_before
            .environment_step_count
        ),
        environment_step_count_after=(
            decision.budget_after
            .environment_step_count
        ),
        protocol_failure_count=(
            decision.budget_after
            .protocol_failure_count
        ),
        inadmissible_action_count=(
            decision.budget_after
            .inadmissible_action_count
        ),
        consecutive_nonexecuted_attempt_count=(
            decision.budget_after
            .consecutive_nonexecuted_attempt_count
        ),
        episode_termination_reason=_enum_text(
            decision.termination_reason
        ),
        submitted_environment_action=(
            submitted_action
        ),
        resulting_observation=(
            resulting_observation
        ),
        environment_event_flags=(
            environment_event_flags
        ),
        protocol_failure_count_before=(
            decision.budget_before
            .protocol_failure_count
        ),
        inadmissible_action_count_before=(
            decision.budget_before
            .inadmissible_action_count
        ),
        consecutive_nonexecuted_attempt_count_before=(
            decision.budget_before
            .consecutive_nonexecuted_attempt_count
        ),
    )
