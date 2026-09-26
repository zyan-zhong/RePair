"""Schedule-driven P4 Harness-OFF SELECT result identity audit."""

from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from dataclasses import dataclass

from .action_trace import TraceProvenance
from .canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from .condition_run_schedule import (
    ConditionRunPurpose,
    ConditionRunScheduleV1,
)
from .distillation_access import (
    DistillationAccessClass,
)
from .distillation_governance import (
    canonical_model_sha256,
)
from .policy_call_evidence import (
    PolicyCallEvidenceV1,
)
from .policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
)
from .schema_models import (
    EpisodeArtifactV1,
)
from .select_execution_identity import (
    SelectExecutionIdentityV1,
    select_i1_request_contract_sha256,
    validate_select_i1_wire_v1,
    validate_select_model_identity_chain,
)
from .select_policy_runtime import (
    PI0_CONDITION_ID,
    PI1_LOGICAL_CONDITION_ID,
    SelectPolicyRuntimeManifestV1,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ExpectedSelectCellV1:
    schedule_name: str
    condition_cell_id: str
    manifest_index: int
    task_id: str
    evaluation_seed: int
    policy_condition_manifest_sha256: str
    condition_run_schedule_sha256: str


def validate_master_schedule_set(
    *,
    schedules: Mapping[
        str,
        ConditionRunScheduleV1,
    ],
    authorized_schedule_sha256: Mapping[
        str,
        str,
    ],
) -> None:
    """Validate exactly the schedules authorized by SELECT freeze."""

    if (
        set(schedules)
        != set(
            authorized_schedule_sha256
        )
    ):
        raise ValueError(
            "SELECT master schedule set identity mismatch"
        )

    if not schedules:
        raise ValueError(
            "SELECT master schedule set must not be empty"
        )

    reference_grid = None
    all_cell_ids: set[str] = set()

    for name in sorted(
        schedules
    ):
        schedule = schedules[
            name
        ]

        if (
            type(schedule)
            is not ConditionRunScheduleV1
        ):
            raise TypeError(
                "SELECT schedule has wrong type"
            )

        schedule_sha = (
            canonical_model_sha256(
                schedule
            )
        )

        if (
            schedule_sha
            != authorized_schedule_sha256[
                name
            ]
        ):
            raise ValueError(
                "SELECT authorized schedule hash mismatch"
            )

        if (
            schedule.run_purpose
            is not
            ConditionRunPurpose
            .P4_HARNESS_OFF_SELECT
        ):
            raise ValueError(
                "SELECT schedule has wrong purpose"
            )

        if (
            schedule.target_access_class
            is not
            DistillationAccessClass
            .SELECT_SUMMARY_ONLY
        ):
            raise ValueError(
                "SELECT schedule has wrong access class"
            )

        grid = tuple(
            (
                cell.manifest_index,
                cell.task_id,
                cell.seed,
            )
            for cell
            in schedule.cells
        )

        if (
            len(grid)
            != len(
                set(grid)
            )
        ):
            raise ValueError(
                "SELECT schedule contains duplicate task/seed cells"
            )

        if reference_grid is None:
            reference_grid = grid

        elif grid != reference_grid:
            raise ValueError(
                "SELECT schedules do not share "
                "the same task/seed grid"
            )

        for cell in schedule.cells:
            if (
                cell.condition_cell_id
                in all_cell_ids
            ):
                raise ValueError(
                    "duplicate SELECT scientific cell identity"
                )

            all_cell_ids.add(
                cell.condition_cell_id
            )


def derive_expected_select_cells_from_master_schedules(
    *,
    schedules: Mapping[
        str,
        ConditionRunScheduleV1,
    ],
    authorized_schedule_sha256: Mapping[
        str,
        str,
    ],
) -> tuple[
    ExpectedSelectCellV1,
    ...,
]:
    """Derive expected union exclusively from frozen schedules."""

    validate_master_schedule_set(
        schedules=schedules,
        authorized_schedule_sha256=(
            authorized_schedule_sha256
        ),
    )

    result: list[
        ExpectedSelectCellV1
    ] = []

    for name in sorted(
        schedules
    ):
        schedule = schedules[
            name
        ]

        schedule_sha = (
            canonical_model_sha256(
                schedule
            )
        )

        for cell in schedule.cells:
            result.append(
                ExpectedSelectCellV1(
                    schedule_name=name,
                    condition_cell_id=(
                        cell.condition_cell_id
                    ),
                    manifest_index=(
                        cell.manifest_index
                    ),
                    task_id=(
                        cell.task_id
                    ),
                    evaluation_seed=(
                        cell.seed
                    ),
                    policy_condition_manifest_sha256=(
                        schedule
                        .policy_condition_manifest_sha256
                    ),
                    condition_run_schedule_sha256=(
                        schedule_sha
                    ),
                )
            )

    return tuple(
        result
    )


def _exact_model_names_from_policy_call(
    evidence: PolicyCallEvidenceV1,
) -> tuple[str, str]:
    """Re-derive both model names from exact stored wire bytes."""

    if (
        type(evidence)
        is not PolicyCallEvidenceV1
    ):
        raise TypeError(
            "policy-call evidence has wrong type"
        )

    request = strict_json_loads(
        evidence.request_wire_bytes
    )

    response = strict_json_loads(
        evidence.raw_response_body
    )

    if not isinstance(
        request,
        dict,
    ):
        raise ValueError(
            "SELECT request evidence must be JSON object"
        )

    if not isinstance(
        response,
        dict,
    ):
        raise ValueError(
            "SELECT response evidence must be JSON object"
        )

    request_model = (
        request.get(
            "model"
        )
    )

    response_model = (
        response.get(
            "model"
        )
    )

    if (
        not isinstance(
            request_model,
            str,
        )
        or not request_model
    ):
        raise ValueError(
            "SELECT request model identity is missing"
        )

    if (
        not isinstance(
            response_model,
            str,
        )
        or not response_model
    ):
        raise ValueError(
            "SELECT response model identity is missing"
        )

    return (
        request_model,
        response_model,
    )


def audit_select_cell_identity_chain(
    *,
    expected_cell: ExpectedSelectCellV1,
    policy_condition:
        PolicyConditionManifestV1,
    policy_runtime:
        SelectPolicyRuntimeManifestV1,
    authorized_policy_runtime_sha256: str,
    policy_calls: Sequence[
        PolicyCallEvidenceV1,
    ],
    trace_provenances: Sequence[
        TraceProvenance,
    ],
    episode_artifact:
        EpisodeArtifactV1,
    expected_request_schema_sha256: str | None = None,
) -> None:
    """Audit one resolved SELECT scientific cell end-to-end."""

    if (
        type(expected_cell)
        is not ExpectedSelectCellV1
    ):
        raise TypeError(
            "expected_cell has wrong type"
        )

    if (
        type(policy_condition)
        is not PolicyConditionManifestV1
    ):
        raise TypeError(
            "policy_condition has wrong type"
        )

    if (
        type(policy_runtime)
        is not SelectPolicyRuntimeManifestV1
    ):
        raise TypeError(
            "policy_runtime has wrong type"
        )

    if (
        type(episode_artifact)
        is not EpisodeArtifactV1
    ):
        raise TypeError(
            "episode_artifact has wrong type"
        )


    # ========================================================
    # Frozen policy/runtime authority
    # ========================================================

    runtime_sha = sha256_bytes(
        canonical_json_bytes(
            policy_runtime.to_dict()
        )
    )

    if (
        runtime_sha
        != authorized_policy_runtime_sha256
    ):
        raise ValueError(
            "SELECT runtime authorization mismatch"
        )

    policy_sha = (
        canonical_model_sha256(
            policy_condition
        )
    )

    if (
        policy_sha
        != expected_cell
        .policy_condition_manifest_sha256
    ):
        raise ValueError(
            "SELECT schedule/policy manifest mismatch"
        )

    if (
        policy_condition
        .policy_runtime_manifest_sha256
        != runtime_sha
    ):
        raise ValueError(
            "SELECT policy/runtime manifest mismatch"
        )

    if (
        policy_runtime.policy_condition_id
        != policy_condition
        .policy_condition_id
    ):
        raise ValueError(
            "SELECT policy/runtime identity mismatch"
        )

    if (
        policy_runtime.served_model_name
        != policy_condition
        .served_model_name
    ):
        raise ValueError(
            "SELECT served-model identity mismatch"
        )

    if (
        policy_runtime.checkpoint_instance_id
        != policy_condition
        .policy_condition_id
    ):
        raise ValueError(
            "SELECT checkpoint identity mismatch"
        )


    # ========================================================
    # pi0 versus trained pi1 checkpoint semantics
    # ========================================================

    if (
        policy_condition.checkpoint_kind
        is CheckpointKind.BASE_MODEL
    ):
        if (
            policy_runtime.logical_condition_id
            != PI0_CONDITION_ID
        ):
            raise ValueError(
                "SELECT pi0 logical identity mismatch"
            )

        if (
            policy_runtime.adapter_bundle_sha256
            is not None
        ):
            raise ValueError(
                "SELECT pi0 unexpectedly binds LoRA"
            )

    elif (
        policy_condition.checkpoint_kind
        is CheckpointKind.LORA_ADAPTER
    ):
        if (
            policy_runtime.logical_condition_id
            == PI0_CONDITION_ID
        ):
            raise ValueError(
                "SELECT trained LoRA may not use pi0 logical identity"
            )

        if (
            policy_runtime.adapter_bundle_sha256
            != policy_condition
            .checkpoint_sha256
        ):
            raise ValueError(
                "SELECT adapter identity mismatch"
            )

    else:
        raise ValueError(
            "unsupported SELECT checkpoint kind"
        )


    # ========================================================
    # Final Episode must equal frozen scheduled cell
    # ========================================================

    if (
        episode_artifact.scheduled_cell_id
        != expected_cell.condition_cell_id
        or episode_artifact.condition_cell_id
        != expected_cell.condition_cell_id
    ):
        raise ValueError(
            "SELECT episode/schedule cell mismatch"
        )

    if (
        episode_artifact.task_index
        != expected_cell.manifest_index
        or episode_artifact.task_id
        != expected_cell.task_id
        or episode_artifact.seed
        != expected_cell.evaluation_seed
    ):
        raise ValueError(
            "SELECT episode task/seed mismatch"
        )

    if (
        episode_artifact
        .policy_condition_manifest_sha256
        != policy_sha
    ):
        raise ValueError(
            "SELECT episode policy manifest mismatch"
        )

    if (
        episode_artifact
        .condition_run_schedule_sha256
        != expected_cell
        .condition_run_schedule_sha256
    ):
        raise ValueError(
            "SELECT episode schedule mismatch"
        )

    if (
        episode_artifact
        .policy_runtime_manifest_sha256
        != runtime_sha
        or episode_artifact
        .select_policy_runtime_manifest_sha256
        != runtime_sha
    ):
        raise ValueError(
            "SELECT episode runtime identity mismatch"
        )

    if (
        episode_artifact.policy_condition_id
        != policy_condition
        .policy_condition_id
        or episode_artifact.logical_condition_id
        != policy_runtime
        .logical_condition_id
        or episode_artifact
        .checkpoint_instance_id
        != policy_runtime
        .checkpoint_instance_id
        or episode_artifact.training_seed
        != policy_runtime.training_seed
    ):
        raise ValueError(
            "SELECT episode policy identity mismatch"
        )

    if (
        episode_artifact.evaluation_context
        != "P4_HARNESS_OFF_SELECT"
        or episode_artifact.access_class
        != "SELECT_SUMMARY_ONLY"
    ):
        raise ValueError(
            "SELECT episode evaluation context mismatch"
        )


    if expected_request_schema_sha256 is not None:
        if episode_artifact.policy_request_schema_sha256 != expected_request_schema_sha256:
            raise ValueError("SELECT episode request contract mismatch")
        identity = SelectExecutionIdentityV1(
            evaluation_context=episode_artifact.evaluation_context,
            logical_condition_id=policy_runtime.logical_condition_id,
            checkpoint_instance_id=policy_runtime.checkpoint_instance_id,
            training_seed=policy_runtime.training_seed,
            served_model_name=policy_runtime.served_model_name,
            adapter_bundle_sha256=policy_runtime.adapter_bundle_sha256,
            access_class=episode_artifact.access_class,
            policy_condition_id=episode_artifact.policy_condition_id,
            condition_cell_id=expected_cell.condition_cell_id,
            task_access_manifest_sha256=episode_artifact.task_access_manifest_sha256,
            policy_condition_manifest_sha256=expected_cell.policy_condition_manifest_sha256,
            condition_run_schedule_sha256=expected_cell.condition_run_schedule_sha256,
            select_policy_runtime_manifest_sha256=runtime_sha,
        )
        audit_select_i1_policy_calls_v1(
            identity=identity, policy_calls=policy_calls,
            evaluation_seed=expected_cell.evaluation_seed,
            expected_request_schema_sha256=expected_request_schema_sha256,
        )
    elif episode_artifact.policy_request_schema_sha256 == select_i1_request_contract_sha256():
        raise ValueError("SELECT I1 result requires explicit request contract authority")

    # ========================================================
    # Exact model-call evidence ↔ trace alignment
    # ========================================================

    if not policy_calls:
        raise ValueError(
            "SELECT resolved cell has no policy-call evidence"
        )

    if (
        len(policy_calls)
        != len(
            trace_provenances
        )
    ):
        raise ValueError(
            "SELECT policy-call/trace count mismatch"
        )

    if (
        episode_artifact.trace_count
        != len(
            trace_provenances
        )
    ):
        raise ValueError(
            "SELECT episode/trace count mismatch"
        )

    for (
        policy_call,
        trace,
    ) in zip(
        policy_calls,
        trace_provenances,
        strict=True,
    ):
        if (
            type(trace)
            is not TraceProvenance
        ):
            raise TypeError(
                "trace provenance has wrong type"
            )

        (
            request_model,
            response_model,
        ) = (
            _exact_model_names_from_policy_call(
                policy_call
            )
        )

        if (
            trace.condition_cell_id
            != expected_cell.condition_cell_id
            or trace.task_id
            != expected_cell.task_id
            or trace.seed
            != expected_cell.evaluation_seed
        ):
            raise ValueError(
                "SELECT trace schedule identity mismatch"
            )

        if (
            trace.policy_condition_manifest_sha256
            != policy_sha
            or trace.condition_run_schedule_sha256
            != expected_cell
            .condition_run_schedule_sha256
            or trace
            .select_policy_runtime_manifest_sha256
            != runtime_sha
        ):
            raise ValueError(
                "SELECT trace manifest identity mismatch"
            )

        if (
            trace.logical_condition_id
            != policy_runtime.logical_condition_id
            or trace.checkpoint_instance_id
            != policy_runtime.checkpoint_instance_id
            or trace.training_seed
            != policy_runtime.training_seed
        ):
            raise ValueError(
                "SELECT trace policy identity mismatch"
            )

        validate_select_model_identity_chain(
            schedule_policy_condition_id=(
                policy_condition
                .policy_condition_id
            ),
            bound_policy_condition_id=(
                trace.policy_condition_id
            ),
            manifest_policy_condition_id=(
                policy_condition
                .policy_condition_id
            ),
            runtime_served_model_name=(
                policy_runtime
                .served_model_name
            ),
            profile_served_model_name=(
                policy_runtime
                .served_model_name
            ),
            request_model_name=(
                request_model
            ),
            response_model_name=(
                response_model
            ),
            trace_model_name=(
                trace.model_name
            ),
            artifact_policy_condition_id=(
                episode_artifact
                .policy_condition_id
            ),
        )


def audit_select_i1_policy_calls_v1(
    *, identity: SelectExecutionIdentityV1,
    policy_calls: Sequence[PolicyCallEvidenceV1], evaluation_seed: int,
    expected_request_schema_sha256: str,
) -> None:
    """Recheck actual stored I1 wire and RAW prompt using existing authorities."""
    from .raw_policy_prompt import (
        ExecutedTransition, InterfaceFeedbackCode, build_raw_policy_prompt,
    )
    if not policy_calls:
        raise ValueError("SELECT resolved cell has no policy-call evidence")
    for evidence in policy_calls:
        if type(evidence) is not PolicyCallEvidenceV1:
            raise TypeError("SELECT policy-call evidence has wrong type")
        prompt = build_raw_policy_prompt(
            public_task_goal=evidence.public_task_goal, observation=evidence.observation,
            executed_transitions=tuple(ExecutedTransition(*x) for x in evidence.executed_history),
            admissible_commands=evidence.admissible_commands,
            interface_feedback=(None if evidence.interface_feedback_before is None else
                                InterfaceFeedbackCode(evidence.interface_feedback_before)),
        )
        if evidence.prompt_text != prompt:
            raise ValueError("SELECT RAW prompt differs from original builder")
        validate_select_i1_wire_v1(
            identity=identity, raw=evidence.request_wire_bytes,
            expected_prompt=prompt, expected_seed=evaluation_seed,
            expected_request_id=evidence.client_request_id,
            expected_request_schema_sha256=expected_request_schema_sha256,
        )
