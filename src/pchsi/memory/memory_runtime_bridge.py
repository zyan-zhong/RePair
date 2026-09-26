"""Pure bridge from frozen Memory Policy views to existing Runtime Core."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib

from pchsi.evaluation.budget import (
    BudgetLimits,
    BudgetState,
)
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    InterfaceFeedbackCode,
)
from pchsi.evaluation.runtime_core import (
    ProtocolPreconditionResult,
    RuntimeDecision,
    process_completed_generation,
    validate_runtime_preconditions,
)
from pchsi.memory.memory_augmented_prompt import (
    build_memory_augmented_raw_policy_prompt_v1,
)
from pchsi.memory.policy_exposure import (
    EXPOSURE_SCHEMA_V1,
    INSERTION_ANCHOR_V1,
    MemoryPolicyExposureV1,
)


@dataclass(frozen=True, slots=True)
class PreparedMemoryPolicyAttemptV1:
    precondition: ProtocolPreconditionResult
    prompt: str | None
    exposure: MemoryPolicyExposureV1 | None


def prepare_memory_policy_attempt_v1(
    *,
    public_task_goal: str,
    observation: str,
    executed_transitions: Sequence[ExecutedTransition],
    memory_payloads: tuple[dict[str, object], ...],
    policy_visible_commands: Sequence[str],
    harness_visible_commands: Sequence[str],
    environment_commands: Sequence[str],
    interface_feedback: InterfaceFeedbackCode | None,
    budget_state: BudgetState,
    snapshot_sha256: str,
    token_budget_contract_sha256: str,
    retrieval_mode: str,
    branch_role: str,
    representation_class: str,
    memory_lineage_id: str | None,
    record_version: int | None,
    projection_artifact_sha256: str | None,
    packed_token_count: int,
    budget_limits: BudgetLimits = BudgetLimits(),
) -> PreparedMemoryPolicyAttemptV1:
    precondition = validate_runtime_preconditions(
        policy_visible_commands=policy_visible_commands,
        harness_visible_commands=harness_visible_commands,
        environment_commands=environment_commands,
        budget_state=budget_state,
        budget_limits=budget_limits,
    )

    if not precondition.should_call_policy:
        return PreparedMemoryPolicyAttemptV1(
            precondition=precondition,
            prompt=None,
            exposure=None,
        )

    prompt = build_memory_augmented_raw_policy_prompt_v1(
        public_task_goal=public_task_goal,
        observation=observation,
        executed_transitions=executed_transitions,
        retrieved_failure_experiences=memory_payloads,
        admissible_commands=policy_visible_commands,
        interface_feedback=interface_feedback,
    )

    if representation_class == "M0":
        if memory_payloads != ():
            raise ValueError("M0 requires empty Memory payload tuple")
    elif len(memory_payloads) != 1:
        raise ValueError(
            "direct B-DIRECT exposure requires exactly one Memory payload"
        )

    exposure = MemoryPolicyExposureV1(
        schema_id=EXPOSURE_SCHEMA_V1,
        schema_version=1,
        snapshot_sha256=snapshot_sha256,
        token_budget_contract_sha256=(
            token_budget_contract_sha256
        ),
        retrieval_mode=retrieval_mode,
        branch_role=branch_role,
        representation_class=representation_class,
        memory_lineage_id=memory_lineage_id,
        record_version=record_version,
        projection_artifact_sha256=(
            projection_artifact_sha256
        ),
        packed_token_count=packed_token_count,
        insertion_anchor=INSERTION_ANCHOR_V1,
        final_prompt_sha256=hashlib.sha256(
            prompt.encode("utf-8")
        ).hexdigest(),
        exposure_sha256=None,
    )

    return PreparedMemoryPolicyAttemptV1(
        precondition=precondition,
        prompt=prompt,
        exposure=exposure,
    )


def process_memory_policy_generation_v1(
    *,
    raw_response: str,
    visible_admissible_commands: Sequence[str],
    prepared: PreparedMemoryPolicyAttemptV1,
    budget_limits: BudgetLimits = BudgetLimits(),
) -> RuntimeDecision:
    if not isinstance(
        prepared,
        PreparedMemoryPolicyAttemptV1,
    ):
        raise TypeError("prepared attempt type mismatch")
    if (
        not prepared.precondition.should_call_policy
        or prepared.prompt is None
        or prepared.exposure is None
    ):
        raise ValueError(
            "prepared attempt does not authorize policy processing"
        )

    return process_completed_generation(
        raw_response=raw_response,
        visible_admissible_commands=(
            visible_admissible_commands
        ),
        precondition_result=prepared.precondition,
        budget_limits=budget_limits,
    )
