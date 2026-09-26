"""Fail-closed identity binding for P4 Harness-OFF SELECT."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
)
from .condition_run_schedule import (
    ConditionRunScheduleCellV1,
    condition_cell_id,
)
from .distillation_access import (
    DistillationAccessClass,
    TaskAccessRecordV1,
)
from .distillation_governance import (
    canonical_model_sha256,
)
from .policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
)
from .policy_execution_profile import (
    PolicyExecutionProfileV1,
)
from .select_policy_runtime import (
    PI0_CONDITION_ID,
    PI1_LOGICAL_CONDITION_ID,
    SelectPolicyRuntimeManifestV1,
)


P4_SELECT_EVALUATION_CONTEXT = (
    "P4_HARNESS_OFF_SELECT"
)


def _runtime_sha256(
    runtime:
        SelectPolicyRuntimeManifestV1,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            runtime.to_dict()
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SelectExecutionIdentityV1:
    """One complete policy identity for one SELECT scientific cell."""

    evaluation_context: str

    logical_condition_id: str
    checkpoint_instance_id: str
    training_seed: int | None

    served_model_name: str
    adapter_bundle_sha256: str | None

    access_class: str

    policy_condition_id: str
    condition_cell_id: str

    task_access_manifest_sha256: str
    policy_condition_manifest_sha256: str
    condition_run_schedule_sha256: str
    select_policy_runtime_manifest_sha256: str

    def __post_init__(
        self,
    ) -> None:
        if (
            self.evaluation_context
            != P4_SELECT_EVALUATION_CONTEXT
        ):
            raise ValueError(
                "SELECT evaluation_context mismatch"
            )

        if (
            self.access_class
            != DistillationAccessClass
            .SELECT_SUMMARY_ONLY.value
        ):
            raise ValueError(
                "SELECT access_class mismatch"
            )

        for name in (
            "logical_condition_id",
            "checkpoint_instance_id",
            "served_model_name",
            "policy_condition_id",
            "condition_cell_id",
        ):
            value = getattr(
                self,
                name,
            )
            if (
                not isinstance(value, str)
                or not value
            ):
                raise ValueError(
                    f"{name} must be non-empty str"
                )

        for name in (
            "task_access_manifest_sha256",
            "policy_condition_manifest_sha256",
            "condition_run_schedule_sha256",
            "select_policy_runtime_manifest_sha256",
        ):
            require_lower_sha256(
                name,
                getattr(self, name),
            )

        if (
            self.policy_condition_id
            != self.checkpoint_instance_id
        ):
            raise ValueError(
                "SELECT policy/checkpoint identity mismatch"
            )

        if (
            self.logical_condition_id
            == PI0_CONDITION_ID
        ):
            if (
                self.policy_condition_id
                != PI0_CONDITION_ID
            ):
                raise ValueError(
                    "pi0 SELECT identity mismatch"
                )

            if self.training_seed is not None:
                raise ValueError(
                    "pi0 SELECT identity forbids training_seed"
                )

            if (
                self.adapter_bundle_sha256
                is not None
            ):
                raise ValueError(
                    "pi0 SELECT identity forbids LoRA hash"
                )

        else:
            if (
                type(self.training_seed)
                is not int
                or self.training_seed < 0
            ):
                raise ValueError(
                    "pi1 SELECT identity requires training_seed"
                )

            require_lower_sha256(
                "adapter_bundle_sha256",
                self.adapter_bundle_sha256,
            )



@dataclass(
    frozen=True,
    slots=True,
)
class SelectBoundEpisodeCellV1:
    """Schedule cell bound to one exact SELECT policy identity."""

    scheduled_cell_id: str
    task_index: int
    task_id: str
    seed: int

    policy_condition_id: str
    access_class: DistillationAccessClass

    execution_identity: SelectExecutionIdentityV1

    def __post_init__(
        self,
    ) -> None:
        if (
            self.access_class
            is not DistillationAccessClass
            .SELECT_SUMMARY_ONLY
        ):
            raise ValueError(
                "SELECT cell requires SELECT_SUMMARY_ONLY"
            )

        if (
            self.execution_identity
            .policy_condition_id
            != self.policy_condition_id
        ):
            raise ValueError(
                "SELECT cell policy identity mismatch"
            )

        if (
            self.execution_identity
            .condition_cell_id
            != self.scheduled_cell_id
        ):
            raise ValueError(
                "SELECT condition cell identity mismatch"
            )

        expected = (
            condition_cell_id(
                policy_condition_id=(
                    self.policy_condition_id
                ),
                manifest_index=(
                    self.task_index
                ),
                seed=(
                    self.seed
                ),
            )
        )

        if (
            self.scheduled_cell_id
            != expected
        ):
            raise ValueError(
                "SELECT scheduled cell is not canonical"
            )


def bind_select_condition_cell(
    *,
    schedule_cell:
        ConditionRunScheduleCellV1,
    task_access:
        TaskAccessRecordV1,
    policy_condition:
        PolicyConditionManifestV1,
    policy_runtime:
        SelectPolicyRuntimeManifestV1,

    task_access_manifest_sha256: str,
    policy_condition_manifest_sha256: str,
    condition_run_schedule_sha256: str,
    select_policy_runtime_manifest_sha256: str,
) -> SelectBoundEpisodeCellV1:
    """Bind schedule/access/policy/runtime into one exact SELECT identity."""

    if (
        type(schedule_cell)
        is not ConditionRunScheduleCellV1
    ):
        raise TypeError(
            "schedule_cell has wrong type"
        )

    if (
        type(task_access)
        is not TaskAccessRecordV1
    ):
        raise TypeError(
            "task_access has wrong type"
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

    for name, value in (
        (
            "task_access_manifest_sha256",
            task_access_manifest_sha256,
        ),
        (
            "policy_condition_manifest_sha256",
            policy_condition_manifest_sha256,
        ),
        (
            "condition_run_schedule_sha256",
            condition_run_schedule_sha256,
        ),
        (
            "select_policy_runtime_manifest_sha256",
            select_policy_runtime_manifest_sha256,
        ),
    ):
        require_lower_sha256(
            name,
            value,
        )

    if (
        schedule_cell.manifest_index
        != task_access.manifest_index
        or schedule_cell.task_id
        != task_access.task_id
    ):
        raise ValueError(
            "SELECT schedule/access identity mismatch"
        )

    if (
        task_access.access_class
        is not DistillationAccessClass
        .SELECT_SUMMARY_ONLY
    ):
        raise ValueError(
            "SELECT task must be SELECT_SUMMARY_ONLY"
        )

    if (
        task_access.teacher_call_permitted
        or task_access.training_permitted
        or not task_access.select_evaluation_permitted
        or task_access.confirmatory_permitted
    ):
        raise ValueError(
            "SELECT task permission contract mismatch"
        )

    if (
        canonical_model_sha256(
            policy_condition
        )
        != policy_condition_manifest_sha256
    ):
        raise ValueError(
            "SELECT policy manifest hash mismatch"
        )

    if (
        _runtime_sha256(
            policy_runtime
        )
        != select_policy_runtime_manifest_sha256
    ):
        raise ValueError(
            "SELECT runtime manifest hash mismatch"
        )

    if (
        policy_runtime.policy_condition_id
        != policy_condition.policy_condition_id
    ):
        raise ValueError(
            "SELECT runtime/policy identity mismatch"
        )

    if (
        policy_runtime.served_model_name
        != policy_condition.served_model_name
    ):
        raise ValueError(
            "SELECT served-model identity mismatch"
        )

    if (
        policy_runtime.checkpoint_instance_id
        != policy_condition.policy_condition_id
    ):
        raise ValueError(
            "SELECT checkpoint identity mismatch"
        )

    if (
        policy_condition.checkpoint_kind
        is CheckpointKind.BASE_MODEL
    ):
        if (
            policy_runtime.logical_condition_id
            != PI0_CONDITION_ID
        ):
            raise ValueError(
                "pi0 logical identity mismatch"
            )

        if (
            policy_runtime.adapter_bundle_sha256
            is not None
        ):
            raise ValueError(
                "pi0 runtime unexpectedly binds LoRA"
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
                "trained SELECT logical identity may not be pi0"
            )

        if (
            policy_runtime.adapter_bundle_sha256
            != policy_condition.checkpoint_sha256
        ):
            raise ValueError(
                "pi1 adapter identity mismatch"
            )

    else:
        raise ValueError(
            "unsupported SELECT checkpoint kind"
        )

    expected_cell = (
        condition_cell_id(
            policy_condition_id=(
                policy_condition
                .policy_condition_id
            ),
            manifest_index=(
                schedule_cell
                .manifest_index
            ),
            seed=(
                schedule_cell.seed
            ),
        )
    )

    if (
        schedule_cell.condition_cell_id
        != expected_cell
    ):
        raise ValueError(
            "SELECT schedule condition identity mismatch"
        )

    identity = (
        SelectExecutionIdentityV1(
            evaluation_context=(
                P4_SELECT_EVALUATION_CONTEXT
            ),
            logical_condition_id=(
                policy_runtime
                .logical_condition_id
            ),
            checkpoint_instance_id=(
                policy_runtime
                .checkpoint_instance_id
            ),
            training_seed=(
                policy_runtime
                .training_seed
            ),
            served_model_name=(
                policy_runtime
                .served_model_name
            ),
            adapter_bundle_sha256=(
                policy_runtime
                .adapter_bundle_sha256
            ),
            access_class=(
                task_access
                .access_class
                .value
            ),
            policy_condition_id=(
                policy_condition
                .policy_condition_id
            ),
            condition_cell_id=(
                schedule_cell
                .condition_cell_id
            ),
            task_access_manifest_sha256=(
                task_access_manifest_sha256
            ),
            policy_condition_manifest_sha256=(
                policy_condition_manifest_sha256
            ),
            condition_run_schedule_sha256=(
                condition_run_schedule_sha256
            ),
            select_policy_runtime_manifest_sha256=(
                select_policy_runtime_manifest_sha256
            ),
        )
    )

    return SelectBoundEpisodeCellV1(
        scheduled_cell_id=(
            schedule_cell
            .condition_cell_id
        ),
        task_index=(
            schedule_cell
            .manifest_index
        ),
        task_id=(
            schedule_cell
            .task_id
        ),
        seed=(
            schedule_cell.seed
        ),
        policy_condition_id=(
            policy_condition
            .policy_condition_id
        ),
        access_class=(
            task_access
            .access_class
        ),
        execution_identity=(
            identity
        ),
    )


def validate_select_execution_profile_binding(
    *,
    identity:
        SelectExecutionIdentityV1,
    profile:
        PolicyExecutionProfileV1 | SelectI1ExecutionProfileV1,
    expected_request_schema_sha256: str | None = None,
) -> None:
    """Fail before a model call if profile points to another model."""

    if type(profile) is SelectI1ExecutionProfileV1:
        if profile.identity != identity:
            raise ValueError("SELECT I1 profile identity mismatch")
        if expected_request_schema_sha256 != profile.request_contract_sha256:
            raise ValueError("SELECT I1 request contract is not bound by episode config")
        return
    if expected_request_schema_sha256 == select_i1_request_contract_sha256():
        raise ValueError("SELECT I1 request contract cannot use a legacy RAW profile")

    if (
        profile.request_kind
        != "R0"
    ):
        raise ValueError(
            "SELECT identity requires RAW request semantics"
        )

    if (
        profile.arm_id
        != identity.logical_condition_id
    ):
        raise ValueError(
            "SELECT logical identity/profile mismatch"
        )

    if (
        profile.served_model_name
        != identity.served_model_name
    ):
        raise ValueError(
            "SELECT served-model identity/profile mismatch"
        )


def build_select_execution_profile(
    identity:
        SelectExecutionIdentityV1,
) -> PolicyExecutionProfileV1:
    """Build a raw-policy execution profile from frozen SELECT identity."""

    policy_version = (
        "pi0"
        if identity.logical_condition_id
        == PI0_CONDITION_ID
        else (
            "PI1_BAD"
            if identity.logical_condition_id
            == PI1_LOGICAL_CONDITION_ID
            else identity.logical_condition_id
        )
    )

    return PolicyExecutionProfileV1(
        profile_id=(
            "P4_SELECT_EXECUTION_PROFILE_V1:"
            + identity.checkpoint_instance_id
        ),
        arm_id=(
            identity.logical_condition_id
        ),
        policy_version=(
            policy_version
        ),
        request_kind="R0",
        requires_diagnostic_policy_call_evidence=True,
        requires_current_admissible_commands=False,
        served_model_name=(
            identity.served_model_name
        ),
    )


def validate_select_model_identity_chain(
    *,
    schedule_policy_condition_id: str,
    bound_policy_condition_id: str,
    manifest_policy_condition_id: str,

    runtime_served_model_name: str,
    profile_served_model_name: str,
    request_model_name: str,
    response_model_name: str,
    trace_model_name: str,

    artifact_policy_condition_id: str,
) -> None:
    """Validate schedule → runtime → request → response → trace identity."""

    policy_ids = (
        schedule_policy_condition_id,
        bound_policy_condition_id,
        manifest_policy_condition_id,
        artifact_policy_condition_id,
    )

    if (
        len(set(policy_ids))
        != 1
    ):
        raise ValueError(
            "SELECT policy identity chain mismatch"
        )

    model_ids = (
        runtime_served_model_name,
        profile_served_model_name,
        request_model_name,
        response_model_name,
        trace_model_name,
    )

    if (
        len(set(model_ids))
        != 1
    ):
        raise ValueError(
            "SELECT model identity chain mismatch"
        )


# Explicit opt-in: legacy SELECT callers keep build_select_execution_profile().
# The source prompt, menu, parser, budgets and episode loop are not changed here.
def select_i1_request_contract_sha256() -> str:
    from pchsi.research_intelligence.human_f0f1_runtime import (
        continuation_request_contract_v1,
    )
    return sha256_bytes(canonical_json_bytes(
        continuation_request_contract_v1("I1_EXECUTION_PROFILE_V1")
    ))


@dataclass(frozen=True, slots=True)
class SelectI1ExecutionProfileV1:
    identity: SelectExecutionIdentityV1
    request_contract_sha256: str

    def __post_init__(self) -> None:
        if type(self.identity) is not SelectExecutionIdentityV1:
            raise TypeError("SELECT I1 requires exact SELECT identity")
        if self.request_contract_sha256 != select_i1_request_contract_sha256():
            raise ValueError("SELECT I1 request contract differs from original factory")

    @property
    def profile_id(self) -> str:
        return "SELECT_I1_EXECUTION_PROFILE_V1:" + self.identity.checkpoint_instance_id

    @property
    def arm_id(self) -> str:
        return self.identity.logical_condition_id

    @property
    def policy_version(self) -> str:
        return build_select_execution_profile(self.identity).policy_version

    @property
    def request_kind(self) -> str:
        return "I1"

    @property
    def requires_diagnostic_policy_call_evidence(self) -> bool:
        return True

    @property
    def requires_current_admissible_commands(self) -> bool:
        return False

    @property
    def served_model_name(self) -> str:
        return self.identity.served_model_name

    def build_request(self, *, prompt_text: str, seed: int, request_id: str,
                      admissible_commands=None):
        from pchsi.research_intelligence.human_f0f1_runtime import (
            build_bound_continuation_request_v1,
            continuation_request_contract_v1,
        )
        if admissible_commands is not None:
            raise ValueError("SELECT I1 does not accept dynamic action enum")
        return build_bound_continuation_request_v1(
            runtime={
                "served_model_name": self.served_model_name,
                "continuation_request_contract": continuation_request_contract_v1(
                    "I1_EXECUTION_PROFILE_V1"
                ),
            },
            prompt_text=prompt_text, seed=seed, request_id=request_id,
        )


def build_select_i1_execution_profile(
    identity: SelectExecutionIdentityV1, *, request_contract_sha256: str,
) -> SelectI1ExecutionProfileV1:
    return SelectI1ExecutionProfileV1(identity, request_contract_sha256)


def validate_select_i1_wire_v1(
    *, identity: SelectExecutionIdentityV1, raw: bytes,
    expected_prompt: str, expected_seed: int, expected_request_id: str,
    expected_request_schema_sha256: str,
) -> None:
    from pchsi.research_intelligence.human_f0f1_runtime import (
        continuation_request_contract_v1, validate_continuation_wire_v1,
    )
    build_select_i1_execution_profile(
        identity, request_contract_sha256=expected_request_schema_sha256,
    )
    validate_continuation_wire_v1(
        runtime={
            "served_model_name": identity.served_model_name,
            "continuation_request_contract": continuation_request_contract_v1(
                "I1_EXECUTION_PROFILE_V1"
            ),
        },
        raw=raw, expected_prompt=expected_prompt, expected_seed=expected_seed,
        expected_request_id=expected_request_id,
    )
