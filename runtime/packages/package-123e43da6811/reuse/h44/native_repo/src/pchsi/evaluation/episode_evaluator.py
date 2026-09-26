"""Single-episode E1 orchestration over frozen Runtime Core contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .action_trace import ActionTrace, TraceProvenance
from .condition_execution_binding import ConditionBoundEpisodeCellV1
from .select_execution_identity import (
    SelectI1ExecutionProfileV1,
    P4_SELECT_EVALUATION_CONTEXT,
    SelectBoundEpisodeCellV1,
    SelectExecutionIdentityV1,
    validate_select_execution_profile_binding,
)
from .policy_call_evidence import PolicyCallEvidenceV1, build_policy_call_evidence
from .alfworld_adapter import SpawnedAlfworldAdapter
from .alfworld_contracts import (
    MenuSnapshot,
    ResetPublicState,
    StepPublicState,
)
from .artifact_publisher import ArtifactPublisher
from .attempt_state import (
    CloseFailureEvidenceCode,
    OperationalFinalizationStatus,
    ScientificOutcomeStatus,
)
from .budget import (
    BudgetLimits,
    BudgetState,
    EpisodeTerminationReason,
)
from .canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    require_nonnegative_int,
    sha256_bytes,
    sha256_text,
)
from .cell_lock import build_scientific_cell_lock
from .episode_artifact import (
    AttemptBundleBytes,
    build_attempt_bundle_bytes,
)
from .episode_sequence import (
    EpisodeSequenceInput,
    validate_episode_sequence,
)
from .policy_client import PolicyClient
from .policy_attempt_adapter import (
    BoundI1PolicyExecutionProfileV1,
    PolicyAttemptAdapterV1,
    RAW_POLICY_ATTEMPT_ADAPTER_V1,
)
from .policy_execution_profile import (
    PolicyExecutionProfileV1,
    R0_EXECUTION_PROFILE_V1,
)
from .raw_policy_prompt import (
    ExecutedTransition,
    InterfaceFeedbackCode,
    build_raw_policy_prompt,
    sha256_executed_transitions,
)
from .rendered_prompt import PromptRenderer
from .run_schedule import (
    REPLICATE_SEEDS,
    ScheduledCell,
    execution_attempt_id,
)
from .schema_models import (
    AttemptReceiptV1,
    BudgetSnapshotV1,
    EpisodeArtifactV1,
    PublicTransitionRecordV1,
)
from .task_manifest import FrozenTaskRecord
from .trace_assembler import (
    TraceAssemblyInput,
    assemble_action_trace,
    validate_policy_call_trace_alignment,
)
from .public_transition import build_public_transition
from .runtime_core import (
    AttemptOutcome,
    finalize_environment_result,
    process_completed_generation,
    validate_runtime_preconditions,
)


@dataclass(frozen=True, slots=True)
class EpisodeExecutionConfig:
    run_id: str
    cell: (
        ScheduledCell
        | ConditionBoundEpisodeCellV1
        | SelectBoundEpisodeCellV1
    )
    execution_attempt_id: str
    attempt_ordinal: int
    task: FrozenTaskRecord
    seed: int
    evaluator_commit: str
    design_merge_commit: str
    runtime_core_commit: str
    raw_protocol_sha256: str
    split_access_sha256: str
    gamefile_identity_manifest_sha256: str
    environment_runtime_manifest_sha256: str
    policy_runtime_manifest_sha256: str
    policy_request_schema_sha256: str
    run_schedule_sha256: str
    gamefile_sha256: str
    budget_limits: BudgetLimits = BudgetLimits()
    task_access_manifest_sha256: str | None = None
    policy_condition_manifest_sha256: str | None = None
    condition_run_schedule_sha256: str | None = None
    access_class: str | None = None
    policy_condition_id: str | None = None
    condition_cell_id: str | None = None
    evaluation_context: str | None = None
    select_execution_identity: SelectExecutionIdentityV1 | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ValueError("run_id must be non-empty")
        if not isinstance(
            self.cell,
            (
                ScheduledCell,
                ConditionBoundEpisodeCellV1,
                SelectBoundEpisodeCellV1,
            ),
        ):
            raise TypeError(
                "cell has unsupported execution binding"
            )
        if not isinstance(self.task, FrozenTaskRecord):
            raise TypeError("task must be FrozenTaskRecord")
        ordinal = require_nonnegative_int(
            "attempt_ordinal",
            self.attempt_ordinal,
        )
        if self.execution_attempt_id != execution_attempt_id(
            scheduled_cell_id=self.cell.scheduled_cell_id,
            attempt_ordinal=ordinal,
        ):
            raise ValueError("execution_attempt_id mismatch")
        if (
            self.cell.task_index != self.task.index
            or self.cell.task_id != self.task.task_id
            or self.cell.seed != self.seed
        ):
            raise ValueError("cell/task/seed identity mismatch")
        if not isinstance(self.budget_limits, BudgetLimits):
            raise TypeError("budget_limits must be BudgetLimits")
        for name in (
            "raw_protocol_sha256",
            "split_access_sha256",
            "gamefile_identity_manifest_sha256",
            "environment_runtime_manifest_sha256",
            "policy_runtime_manifest_sha256",
            "policy_request_schema_sha256",
            "run_schedule_sha256",
            "gamefile_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        for name in (
            "evaluator_commit",
            "design_merge_commit",
            "runtime_core_commit",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be non-empty")
        condition_fields = (
            self.task_access_manifest_sha256,
            self.policy_condition_manifest_sha256,
            self.condition_run_schedule_sha256,
            self.access_class,
            self.policy_condition_id,
            self.condition_cell_id,
        )

        condition_present = tuple(
            value is not None
            for value in condition_fields
        )

        if (
            any(condition_present)
            and not all(condition_present)
        ):
            raise ValueError(
                "condition execution identity fields "
                "must be supplied together"
            )

        if all(condition_present):
            for name in (
                "task_access_manifest_sha256",
                "policy_condition_manifest_sha256",
                "condition_run_schedule_sha256",
            ):
                require_lower_sha256(
                    name,
                    getattr(self, name),
                )

        identity = (
            self.select_execution_identity
        )

        # ----------------------------------------------------
        # Legacy E1 / P1 DEV
        # ----------------------------------------------------
        if identity is None:
            if self.evaluation_context is not None:
                raise ValueError(
                    "legacy/P1 execution must not set "
                    "SELECT evaluation_context"
                )

            if isinstance(
                self.cell,
                SelectBoundEpisodeCellV1,
            ):
                raise ValueError(
                    "SELECT cell requires "
                    "select_execution_identity"
                )

            if all(condition_present):
                if not isinstance(
                    self.cell,
                    ConditionBoundEpisodeCellV1,
                ):
                    raise ValueError(
                        "P1 execution requires "
                        "condition-bound cell"
                    )

                if (
                    self.access_class
                    != "DEV_VISIBLE"
                    or self.policy_condition_id
                    != "P4-R0-PI0"
                ):
                    raise ValueError(
                        "P1 execution requires "
                        "DEV_VISIBLE P4-R0-PI0"
                    )

                if (
                    self.condition_cell_id
                    != self.cell.scheduled_cell_id
                ):
                    raise ValueError(
                        "condition cell identity mismatch"
                    )

                if (
                    self.cell.policy_condition_id
                    != self.policy_condition_id
                ):
                    raise ValueError(
                        "condition cell policy identity mismatch"
                    )

                if (
                    self.cell.access_class.value
                    != self.access_class
                ):
                    raise ValueError(
                        "condition cell access identity mismatch"
                    )

                if (
                    self.split_access_sha256
                    != self.task_access_manifest_sha256
                ):
                    raise ValueError(
                        "split_access_sha256 must equal "
                        "P1 task access manifest hash"
                    )

                if (
                    self.run_schedule_sha256
                    != self.condition_run_schedule_sha256
                ):
                    raise ValueError(
                        "run_schedule_sha256 must equal "
                        "P1 condition schedule hash"
                    )

        # ----------------------------------------------------
        # Formal Harness-OFF SELECT
        # ----------------------------------------------------
        else:
            if (
                type(identity)
                is not SelectExecutionIdentityV1
            ):
                raise TypeError(
                    "select_execution_identity has wrong type"
                )

            if (
                self.evaluation_context
                != P4_SELECT_EVALUATION_CONTEXT
            ):
                raise ValueError(
                    "SELECT evaluation_context mismatch"
                )

            if not all(condition_present):
                raise ValueError(
                    "SELECT execution requires complete "
                    "condition identity"
                )

            if not isinstance(
                self.cell,
                SelectBoundEpisodeCellV1,
            ):
                raise ValueError(
                    "SELECT execution requires "
                    "SelectBoundEpisodeCellV1"
                )

            if (
                self.cell.execution_identity
                != identity
            ):
                raise ValueError(
                    "SELECT cell/execution identity mismatch"
                )

            if (
                self.access_class
                != identity.access_class
                or self.policy_condition_id
                != identity.policy_condition_id
                or self.condition_cell_id
                != identity.condition_cell_id
            ):
                raise ValueError(
                    "SELECT config identity mismatch"
                )

            if (
                self.task_access_manifest_sha256
                != identity.task_access_manifest_sha256
                or self.policy_condition_manifest_sha256
                != identity.policy_condition_manifest_sha256
                or self.condition_run_schedule_sha256
                != identity.condition_run_schedule_sha256
            ):
                raise ValueError(
                    "SELECT manifest identity mismatch"
                )

            if (
                self.policy_runtime_manifest_sha256
                != identity
                .select_policy_runtime_manifest_sha256
            ):
                raise ValueError(
                    "SELECT runtime identity mismatch"
                )

            if (
                self.split_access_sha256
                != identity.task_access_manifest_sha256
            ):
                raise ValueError(
                    "SELECT split/access identity mismatch"
                )

            if (
                self.run_schedule_sha256
                != identity.condition_run_schedule_sha256
            ):
                raise ValueError(
                    "SELECT schedule identity mismatch"
                )



@dataclass(frozen=True, slots=True)
class EpisodeDependencies:
    environment: SpawnedAlfworldAdapter
    policy_client: PolicyClient
    prompt_renderer: PromptRenderer
    artifact_publisher: ArtifactPublisher
    policy_execution_profile: (
        PolicyExecutionProfileV1
        | SelectI1ExecutionProfileV1
        | BoundI1PolicyExecutionProfileV1
    ) = R0_EXECUTION_PROFILE_V1
    policy_attempt_adapter: PolicyAttemptAdapterV1 = RAW_POLICY_ATTEMPT_ADAPTER_V1


@dataclass(frozen=True, slots=True)
class EpisodeAttemptResult:
    traces: tuple[ActionTrace, ...]
    transitions: tuple[PublicTransitionRecordV1, ...]
    final_budget: BudgetState
    scientific_outcome_status: ScientificOutcomeStatus
    operational_finalization_status: OperationalFinalizationStatus
    termination_reason: str
    success: bool | None
    attempt_bundle: AttemptBundleBytes | None


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _parse_public_task_goal(observation: str) -> str:
    if not isinstance(observation, str):
        raise TypeError("reset observation must be str")
    prefix = "Your task is to:"
    for line in observation.splitlines():
        if line.startswith(prefix):
            goal = line[len(prefix):].strip()
            if goal:
                return goal
    raise ValueError("public task goal parser contract failure")


def _config_sha256(
    config: EpisodeExecutionConfig,
) -> str:
    payload: dict[str, object] = {
        "evaluator_commit":
            config.evaluator_commit,
        "runtime_core_commit":
            config.runtime_core_commit,
        "raw_protocol_sha256":
            config.raw_protocol_sha256,
        "split_access_sha256":
            config.split_access_sha256,
        "gamefile_identity_manifest_sha256": (
            config.gamefile_identity_manifest_sha256
        ),
        "environment_runtime_manifest_sha256": (
            config.environment_runtime_manifest_sha256
        ),
        "policy_runtime_manifest_sha256": (
            config.policy_runtime_manifest_sha256
        ),
        "policy_request_schema_sha256": (
            config.policy_request_schema_sha256
        ),
        "run_schedule_sha256": (
            config.run_schedule_sha256
        ),
    }

    identity = (
        config.select_execution_identity
    )

    if identity is not None:
        payload.update({
            "evaluation_context":
                config.evaluation_context,
            "logical_condition_id":
                identity.logical_condition_id,
            "checkpoint_instance_id":
                identity.checkpoint_instance_id,
            "training_seed":
                identity.training_seed,
            "served_model_name":
                identity.served_model_name,
            "select_policy_runtime_manifest_sha256": (
                identity
                .select_policy_runtime_manifest_sha256
            ),
        })

    return sha256_bytes(
        canonical_json_bytes(
            payload
        )
    )


def _replicate_id(seed: int) -> int:
    try:
        return REPLICATE_SEEDS.index(seed)
    except ValueError as error:
        raise ValueError("seed is not a frozen E1 replicate seed") from error


def _provenance(
    *,
    config: EpisodeExecutionConfig,
    provider_request_id: str,
    history: tuple[ExecutedTransition, ...],
    profile: (
        PolicyExecutionProfileV1
        | SelectI1ExecutionProfileV1
        | BoundI1PolicyExecutionProfileV1
    ),
    memory_version: str = "MEMORY_M0_V1",
    memory_state_sha256: str | None = None,
) -> TraceProvenance:
    identity = (
        config.select_execution_identity
    )

    if identity is not None:
        validate_select_execution_profile_binding(
            identity=identity,
            profile=profile,
            expected_request_schema_sha256=config.policy_request_schema_sha256,
        )

        arm_id = (
            identity.logical_condition_id
        )

        split_and_access_version = (
            "P4_SELECT_EVALUATION_LINEAGE_V1"
        )

        access_mode = (
            "TASK_ACCESS_MANIFEST_V1"
        )

        evaluation_context = (
            identity.evaluation_context
        )

        logical_condition_id = (
            identity.logical_condition_id
        )

        checkpoint_instance_id = (
            identity.checkpoint_instance_id
        )

        training_seed = (
            identity.training_seed
        )

        select_runtime_sha = (
            identity
            .select_policy_runtime_manifest_sha256
        )

    else:
        arm_id = profile.arm_id

        split_and_access_version = (
            "P1_B_ACCESS_V1"
            if config.condition_cell_id is not None
            else "SPLIT_AND_ACCESS_V1"
        )

        access_mode = (
            "TASK_ACCESS_MANIFEST_V1"
            if config.condition_cell_id is not None
            else "TRUSTED_MANIFEST_DIRECT_V1"
        )

        evaluation_context = None
        logical_condition_id = None
        checkpoint_instance_id = None
        training_seed = None
        select_runtime_sha = None

    return TraceProvenance(
        run_id=config.run_id,
        task_id=config.task.task_id,
        episode_id=config.execution_attempt_id,
        replicate_id=_replicate_id(
            config.seed
        ),
        arm_id=arm_id,
        code_commit=config.evaluator_commit,
        config_sha256=_config_sha256(
            config
        ),
        provider="vllm",
        model_name=(
            profile.served_model_name
        ),
        model_version=(
            config.policy_runtime_manifest_sha256
        ),
        provider_request_id=(
            provider_request_id
        ),
        retry_count=config.attempt_ordinal,
        timestamp_utc=_utc_now(),
        split_and_access_version=(
            split_and_access_version
        ),
        split_name=config.task.split,
        access_mode=access_mode,
        policy_version=(
            profile.policy_version
        ),
        seed=config.seed,
        memory_version=memory_version,
        memory_state_sha256=(
            sha256_executed_transitions(history)
            if memory_state_sha256 is None
            else memory_state_sha256
        ),
        task_access_manifest_sha256=(
            config.task_access_manifest_sha256
        ),
        policy_condition_manifest_sha256=(
            config.policy_condition_manifest_sha256
        ),
        condition_run_schedule_sha256=(
            config.condition_run_schedule_sha256
        ),
        access_class=config.access_class,
        policy_condition_id=(
            config.policy_condition_id
        ),
        condition_cell_id=(
            config.condition_cell_id
        ),
        evaluation_context=(
            evaluation_context
        ),
        logical_condition_id=(
            logical_condition_id
        ),
        checkpoint_instance_id=(
            checkpoint_instance_id
        ),
        training_seed=training_seed,
        select_policy_runtime_manifest_sha256=(
            select_runtime_sha
        ),
    )


def _started_receipt(
    *,
    config: EpisodeExecutionConfig,
    created_at_utc: str,
) -> AttemptReceiptV1:
    return AttemptReceiptV1(
        schema_id="E1_ATTEMPT_RECEIPT_V1",
        schema_version=1,
        receipt_kind="STARTED",
        run_id=config.run_id,
        scheduled_cell_id=config.cell.scheduled_cell_id,
        execution_attempt_id=config.execution_attempt_id,
        attempt_ordinal=config.attempt_ordinal,
        evaluator_commit=config.evaluator_commit,
        design_merge_commit=config.design_merge_commit,
        runtime_core_commit=config.runtime_core_commit,
        run_schedule_sha256=config.run_schedule_sha256,
        scientific_outcome_status=(
            ScientificOutcomeStatus.NOT_PRODUCED.value
        ),
        operational_finalization_status=(
            OperationalFinalizationStatus.STAGING.value
        ),
        episode_semantic_sha256=None,
        attempt_bundle_sha256=None,
        terminal_class=None,
        error_code=None,
        created_at_utc=created_at_utc,
    )


def _terminal_receipt(
    *,
    config: EpisodeExecutionConfig,
    scientific: ScientificOutcomeStatus,
    operational: OperationalFinalizationStatus,
    terminal_class: str,
    error_code: str | None,
    bundle: AttemptBundleBytes | None,
) -> AttemptReceiptV1:
    return AttemptReceiptV1(
        schema_id="E1_ATTEMPT_RECEIPT_V1",
        schema_version=1,
        receipt_kind="TERMINAL",
        run_id=config.run_id,
        scheduled_cell_id=config.cell.scheduled_cell_id,
        execution_attempt_id=config.execution_attempt_id,
        attempt_ordinal=config.attempt_ordinal,
        evaluator_commit=config.evaluator_commit,
        design_merge_commit=config.design_merge_commit,
        runtime_core_commit=config.runtime_core_commit,
        run_schedule_sha256=config.run_schedule_sha256,
        scientific_outcome_status=scientific.value,
        operational_finalization_status=operational.value,
        episode_semantic_sha256=(
            None if bundle is None else bundle.episode_semantic_sha256
        ),
        attempt_bundle_sha256=(
            None if bundle is None else bundle.attempt_bundle_sha256
        ),
        terminal_class=terminal_class,
        error_code=error_code,
        created_at_utc=_utc_now(),
    )


def _budget_snapshot(state: BudgetState) -> BudgetSnapshotV1:
    return BudgetSnapshotV1(
        policy_attempt_count=state.policy_attempt_count,
        environment_step_count=state.environment_step_count,
        protocol_failure_count=state.protocol_failure_count,
        inadmissible_action_count=state.inadmissible_action_count,
        consecutive_nonexecuted_attempt_count=(
            state.consecutive_nonexecuted_attempt_count
        ),
    )


@dataclass(frozen=True, slots=True)
class _EnvironmentCloseEvidence:
    clean_close: bool
    worker_reaped: bool
    status: str | None
    exit_code: int | None


def _read_worker_reap_state(
    environment,
) -> tuple[bool, int | None]:
    # Fail closed unless the concrete adapter confirms process exit.
    try:
        worker_alive = environment.worker_alive
    except BaseException:
        worker_alive = None

    try:
        process_exitcode = environment.process_exitcode
    except BaseException:
        process_exitcode = None

    exit_code = (
        process_exitcode
        if type(process_exitcode) is int
        else None
    )
    worker_reaped = (
        worker_alive is False
        and exit_code is not None
    )
    return worker_reaped, exit_code


def _close_environment(
    environment,
) -> _EnvironmentCloseEvidence:
    try:
        status = environment.close()
    except BaseException:
        worker_reaped, exit_code = (
            _read_worker_reap_state(environment)
        )
        return _EnvironmentCloseEvidence(
            clean_close=False,
            worker_reaped=worker_reaped,
            status="CLOSE_EXCEPTION",
            exit_code=exit_code,
        )

    worker_reaped, process_exitcode = (
        _read_worker_reap_state(environment)
    )
    status_name = getattr(status, "status", None)
    terminal_exitcode = getattr(
        status,
        "exit_code",
        None,
    )

    if (
        type(terminal_exitcode) is not int
        or terminal_exitcode != process_exitcode
    ):
        worker_reaped = False

    clean_close = (
        status_name
        in {
            "CLOSED",
            "WORKER_ALREADY_EXITED",
        }
        and worker_reaped
    )

    return _EnvironmentCloseEvidence(
        clean_close=clean_close,
        worker_reaped=worker_reaped,
        status=(
            status_name
            if isinstance(status_name, str)
            else None
        ),
        exit_code=process_exitcode,
    )


def _write_terminal_best_effort(
    *,
    publisher,
    receipt: AttemptReceiptV1,
) -> bool:
    try:
        publisher.write_terminal_receipt(receipt)
    except BaseException:
        return False
    return True


def _early_result(
    *,
    config: EpisodeExecutionConfig,
    dependencies: EpisodeDependencies,
    budget: BudgetState,
    traces: tuple[ActionTrace, ...],
    transitions: tuple[PublicTransitionRecordV1, ...],
    reason: str,
    terminal_class: str,
    error_code: str | None,
) -> EpisodeAttemptResult:
    close_evidence = _close_environment(
        dependencies.environment
    )
    operational = (
        OperationalFinalizationStatus.PUBLISHED
        if close_evidence.clean_close
        else OperationalFinalizationStatus.CLOSE_FAILED_RECORDED
    )
    receipt = _terminal_receipt(
        config=config,
        scientific=ScientificOutcomeStatus.NOT_PRODUCED,
        operational=operational,
        terminal_class=terminal_class,
        error_code=error_code,
        bundle=None,
    )
    if not _write_terminal_best_effort(
        publisher=dependencies.artifact_publisher,
        receipt=receipt,
    ):
        operational = OperationalFinalizationStatus.ARTIFACT_IO_FAILED
    return EpisodeAttemptResult(
        traces=traces,
        transitions=transitions,
        final_budget=budget,
        scientific_outcome_status=(
            ScientificOutcomeStatus.NOT_PRODUCED
        ),
        operational_finalization_status=operational,
        termination_reason=reason,
        success=None,
        attempt_bundle=None,
    )


def run_single_episode(
    *,
    config: EpisodeExecutionConfig,
    dependencies: EpisodeDependencies,
) -> EpisodeAttemptResult:
    if not isinstance(config, EpisodeExecutionConfig):
        raise TypeError("config must be EpisodeExecutionConfig")
    if not isinstance(dependencies, EpisodeDependencies):
        raise TypeError("dependencies must be EpisodeDependencies")

    if (
        type(dependencies.policy_execution_profile) is SelectI1ExecutionProfileV1
        and config.select_execution_identity is None
    ):
        raise ValueError("explicit SELECT I1 profile requires SELECT identity")
    if config.select_execution_identity is not None:
        validate_select_execution_profile_binding(
            identity=config.select_execution_identity,
            profile=dependencies.policy_execution_profile,
            expected_request_schema_sha256=config.policy_request_schema_sha256,
        )

    started_at = _utc_now()
    started = _started_receipt(
        config=config,
        created_at_utc=started_at,
    )
    try:
        dependencies.artifact_publisher.write_started_receipt(
            started
        )
    except BaseException:
        _close_environment(dependencies.environment)
        return EpisodeAttemptResult(
            traces=(),
            transitions=(),
            final_budget=BudgetState(),
            scientific_outcome_status=(
                ScientificOutcomeStatus.NOT_PRODUCED
            ),
            operational_finalization_status=(
                OperationalFinalizationStatus.ARTIFACT_IO_FAILED
            ),
            termination_reason="INFRASTRUCTURE_ERROR",
            success=None,
            attempt_bundle=None,
        )

    try:
        reset_state = dependencies.environment.reset()
        if not isinstance(reset_state, ResetPublicState):
            raise TypeError("reset must return ResetPublicState")
        if (
            reset_state.gamefile_latch.resolved_gamefile
            != config.task.gamefile
        ):
            raise ValueError("reset gamefile identity mismatch")
        public_task_goal = _parse_public_task_goal(
            reset_state.observation
        )
    except BaseException as error:
        return _early_result(
            config=config,
            dependencies=dependencies,
            budget=BudgetState(),
            traces=(),
            transitions=(),
            reason="INFRASTRUCTURE_ERROR",
            terminal_class="PRE_RESULT_INFRASTRUCTURE_ERROR",
            error_code=type(error).__name__,
        )

    budget = BudgetState()
    history: tuple[ExecutedTransition, ...] = ()
    feedback: InterfaceFeedbackCode | None = None
    observation = reset_state.observation
    menu: MenuSnapshot = reset_state.menu
    initial_observation = observation
    traces: list[ActionTrace] = []
    transitions: list[PublicTransitionRecordV1] = []
    policy_calls: list[PolicyCallEvidenceV1] = []
    condition_bound_mode = config.condition_cell_id is not None
    profile = dependencies.policy_execution_profile
    if not isinstance(
        profile,
        (
            PolicyExecutionProfileV1,
            SelectI1ExecutionProfileV1,
            BoundI1PolicyExecutionProfileV1,
        ),
    ):
        raise TypeError(
            "policy_execution_profile must be "
            "PolicyExecutionProfileV1"
        )
    capture_policy_calls = (
        condition_bound_mode
        or profile.requires_diagnostic_policy_call_evidence
    )
    last_score: int | float | None = None
    final_done: bool | None = False
    final_won: bool | None = False
    termination_reason: str | None = None
    success: bool | None = False
    scientific = ScientificOutcomeStatus.TASK_FAILURE

    while termination_reason is None:
        prepared_policy_attempt = dependencies.policy_attempt_adapter.prepare(
            public_task_goal=public_task_goal,
            observation=observation,
            executed_transitions=history,
            policy_visible_commands=menu.commands,
            harness_visible_commands=menu.commands,
            environment_commands=menu.commands,
            interface_feedback=feedback,
            budget_state=budget,
            budget_limits=config.budget_limits,
        )
        precondition = prepared_policy_attempt.precondition
        if not precondition.should_call_policy:
            reason = precondition.termination_reason
            if reason is None:
                raise AssertionError(
                    "closed precondition has no termination reason"
                )
            if (
                reason
                is EpisodeTerminationReason.PROTOCOL_CONFIGURATION_ERROR
            ):
                return _early_result(
                    config=config,
                    dependencies=dependencies,
                    budget=budget,
                    traces=tuple(traces),
                    transitions=tuple(transitions),
                    reason=reason.value,
                    terminal_class="PROTOCOL_CONFIGURATION_ERROR",
                    error_code="INVALID_MENU",
                )
            termination_reason = reason.value
            break

        prompt = prepared_policy_attempt.prompt_text
        if prompt is None:
            raise AssertionError("policy-attempt adapter authorized call without prompt")
        expected_prompt = dependencies.prompt_renderer.render(
            prompt_text=prompt
        )
        request_id = (
            f"{config.execution_attempt_id}-"
            f"m{budget.policy_attempt_count:03d}"
        )
        request = profile.build_request(
            prompt_text=prompt,
            seed=config.seed,
            request_id=request_id,
            admissible_commands=(
                menu.commands
                if profile.requires_current_admissible_commands
                else None
            ),
        )
        try:
            if capture_policy_calls:
                call_result = dependencies.policy_client.generate_with_evidence(
                    request=request,
                    expected_prompt=expected_prompt,
                )
                generation = call_result.generation
                policy_calls.append(
                    build_policy_call_evidence(
                        model_call_index=budget.policy_attempt_count,
                        public_task_goal=public_task_goal,
                        observation=observation,
                        admissible_commands=menu.commands,
                        executed_history=history,
                        interface_feedback_before=feedback,
                        budget_before=budget,
                        request=request,
                        expected_prompt=expected_prompt,
                        generation=generation,
                        transport_evidence=call_result.transport_evidence,
                    )
                )
            else:
                generation = dependencies.policy_client.generate(
                    request=request,
                    expected_prompt=expected_prompt,
                )
        except BaseException as error:
            return _early_result(
                config=config,
                dependencies=dependencies,
                budget=budget,
                traces=tuple(traces),
                transitions=tuple(transitions),
                reason="INFRASTRUCTURE_ERROR",
                terminal_class="PRE_RESULT_INFRASTRUCTURE_ERROR",
                error_code=type(error).__name__,
            )

        current_policy_call = (
            policy_calls[-1]
            if capture_policy_calls
            else None
        )
        decision = dependencies.policy_attempt_adapter.process(
            raw_response=generation.raw_response_text,
            visible_admissible_commands=menu.commands,
            prepared=prepared_policy_attempt,
            budget_limits=config.budget_limits,
        )

        if not decision.should_call_env:
            trace = assemble_action_trace(
                TraceAssemblyInput(
                    provenance=_provenance(
                        config=config,
                        provider_request_id=(
                            generation.provider_request_id
                        ),
                        history=history,
                        profile=profile,
                        memory_version=prepared_policy_attempt.memory_version,
                        memory_state_sha256=prepared_policy_attempt.memory_state_sha256,
                    ),
                    model_call_index=(
                        decision.budget_before
                        .policy_attempt_count
                    ),
                    public_task_goal=public_task_goal,
                    observation=observation,
                    prompt_text=prompt,
                    menu=menu,
                    generation=generation,
                    decision=decision,
                )
            )
            if current_policy_call is not None:
                validate_policy_call_trace_alignment(
                    evidence=current_policy_call,
                    trace=trace,
                )
            traces.append(trace)
            budget = decision.budget_after
            feedback = decision.feedback_code
            if decision.termination_reason is not None:
                termination_reason = (
                    decision.termination_reason.value
                )
            continue

        try:
            raw_result = dependencies.environment.step(
                decision.candidate_environment_action
            )
            if not isinstance(raw_result, StepPublicState):
                raise TypeError(
                    "step must return validated StepPublicState"
                )
        except BaseException as error:
            finalized = finalize_environment_result(
                decision,
                environment_terminated=False,
                infrastructure_error=True,
            )
            trace = assemble_action_trace(
                TraceAssemblyInput(
                    provenance=_provenance(
                        config=config,
                        provider_request_id=(
                            generation.provider_request_id
                        ),
                        history=history,
                        profile=profile,
                        memory_version=prepared_policy_attempt.memory_version,
                        memory_state_sha256=prepared_policy_attempt.memory_state_sha256,
                    ),
                    model_call_index=(
                        decision.budget_before
                        .policy_attempt_count
                    ),
                    public_task_goal=public_task_goal,
                    observation=observation,
                    prompt_text=prompt,
                    menu=menu,
                    generation=generation,
                    decision=finalized,
                    environment_exception_type=(
                        type(error).__name__
                    ),
                )
            )
            if current_policy_call is not None:
                validate_policy_call_trace_alignment(
                    evidence=current_policy_call,
                    trace=trace,
                )
            traces.append(trace)
            budget = finalized.budget_after
            return _early_result(
                config=config,
                dependencies=dependencies,
                budget=budget,
                traces=tuple(traces),
                transitions=tuple(transitions),
                reason="INFRASTRUCTURE_ERROR",
                terminal_class="PRE_RESULT_INFRASTRUCTURE_ERROR",
                error_code=type(error).__name__,
            )

        finalized = finalize_environment_result(
            decision,
            environment_terminated=raw_result.done,
            infrastructure_error=False,
        )
        trace = assemble_action_trace(
            TraceAssemblyInput(
                provenance=_provenance(
                    config=config,
                    provider_request_id=(
                        generation.provider_request_id
                    ),
                    history=history,
                    profile=profile,
                    memory_version=prepared_policy_attempt.memory_version,
                    memory_state_sha256=prepared_policy_attempt.memory_state_sha256,
                ),
                model_call_index=(
                    decision.budget_before
                    .policy_attempt_count
                ),
                public_task_goal=public_task_goal,
                observation=observation,
                prompt_text=prompt,
                menu=menu,
                generation=generation,
                decision=finalized,
                accepted_result=raw_result,
            )
        )
        transition = build_public_transition(
            scheduled_cell_id=config.cell.scheduled_cell_id,
            execution_attempt_id=config.execution_attempt_id,
            model_call_index=(
                decision.budget_before.policy_attempt_count
            ),
            environment_step_index=(
                decision.budget_before.environment_step_count
            ),
            submitted_action=(
                decision.candidate_environment_action
            ),
            pre_observation=observation,
            pre_menu=menu,
            result=raw_result,
        )
        if current_policy_call is not None:
            validate_policy_call_trace_alignment(
                evidence=current_policy_call,
                trace=trace,
            )
        traces.append(trace)
        transitions.append(transition)
        history = (
            *history,
            ExecutedTransition(
                action=(
                    decision.candidate_environment_action
                ),
                resulting_observation=(
                    raw_result.observation
                ),
            ),
        )
        observation = raw_result.observation
        menu = raw_result.menu
        feedback = None
        budget = finalized.budget_after
        last_score = raw_result.score
        final_done = raw_result.done
        final_won = raw_result.won

        if raw_result.done:
            success = raw_result.won
            scientific = (
                ScientificOutcomeStatus.SUCCESS
                if raw_result.won
                else ScientificOutcomeStatus.TASK_FAILURE
            )
            termination_reason = "ENVIRONMENT_TERMINATED"
        elif finalized.termination_reason is not None:
            success = False
            scientific = ScientificOutcomeStatus.TASK_FAILURE
            termination_reason = (
                finalized.termination_reason.value
            )

    if termination_reason is None:
        raise AssertionError("episode loop ended without termination")

    sequence = EpisodeSequenceInput(
        traces=tuple(traces),
        public_transitions=tuple(transitions),
        final_budget=budget,
        final_success=success,
        final_done=final_done,
        final_won=final_won,
        termination_reason=termination_reason,
    )
    validate_episode_sequence(sequence)

    completed_at = _utc_now()
    episode = EpisodeArtifactV1(
        schema_id="E1_EPISODE_ARTIFACT_V1",
        schema_version=1,
        run_id=config.run_id,
        scheduled_cell_id=config.cell.scheduled_cell_id,
        execution_attempt_id=config.execution_attempt_id,
        attempt_ordinal=config.attempt_ordinal,
        task_index=config.task.index,
        task_id=config.task.task_id,
        task_type=config.task.task_type,
        gamefile_sha1=config.task.gamefile_sha1,
        gamefile_sha256=config.gamefile_sha256,
        seed=config.seed,
        evaluator_commit=config.evaluator_commit,
        design_merge_commit=config.design_merge_commit,
        runtime_core_commit=config.runtime_core_commit,
        raw_protocol_sha256=config.raw_protocol_sha256,
        split_access_sha256=config.split_access_sha256,
        gamefile_identity_manifest_sha256=(
            config.gamefile_identity_manifest_sha256
        ),
        environment_runtime_manifest_sha256=(
            config.environment_runtime_manifest_sha256
        ),
        policy_runtime_manifest_sha256=(
            config.policy_runtime_manifest_sha256
        ),
        policy_request_schema_sha256=(
            config.policy_request_schema_sha256
        ),
        scientific_outcome_status=scientific.value,
        operational_finalization_status=(
            OperationalFinalizationStatus.PUBLISHED.value
        ),
        success=success,
        termination_reason=termination_reason,
        final_score=last_score,
        final_done=final_done,
        final_won=final_won,
        final_budget=_budget_snapshot(budget),
        trace_count=len(traces),
        public_transition_count=len(transitions),
        environment_call_trace_count=(
            budget.environment_step_count
        ),
        initial_observation_sha256=sha256_text(
            initial_observation
        ),
        final_observation_sha256=sha256_text(
            observation
        ),
        episode_semantic_sha256="0" * 64,
        task_access_manifest_sha256=config.task_access_manifest_sha256,
        policy_condition_manifest_sha256=config.policy_condition_manifest_sha256,
        condition_run_schedule_sha256=config.condition_run_schedule_sha256,
        access_class=config.access_class,
        policy_condition_id=config.policy_condition_id,
        condition_cell_id=config.condition_cell_id,
        evaluation_context=config.evaluation_context,
        logical_condition_id=(
            config.select_execution_identity.logical_condition_id
            if config.select_execution_identity is not None
            else None
        ),
        checkpoint_instance_id=(
            config.select_execution_identity.checkpoint_instance_id
            if config.select_execution_identity is not None
            else None
        ),
        training_seed=(
            config.select_execution_identity.training_seed
            if config.select_execution_identity is not None
            else None
        ),
        select_policy_runtime_manifest_sha256=(
            config.select_execution_identity
            .select_policy_runtime_manifest_sha256
            if config.select_execution_identity is not None
            else None
        ),
        started_at_utc=started_at,
        completed_at_utc=completed_at,
    )
    bundle = build_attempt_bundle_bytes(
        episode_artifact=episode,
        traces=tuple(traces),
        policy_calls=(
            tuple(policy_calls)
            if capture_policy_calls
            else None
        ),
        public_transitions=tuple(transitions),
    )
    corrected_episode = EpisodeArtifactV1.from_json(
        bundle.attempt_json
    )
    lock = build_scientific_cell_lock(
        episode_artifact=corrected_episode,
        bundle=bundle,
        run_schedule_sha256=config.run_schedule_sha256,
    )

    operational = OperationalFinalizationStatus.PUBLISHED
    try:
        dependencies.artifact_publisher.stage_bundle(
            execution_attempt_id=config.execution_attempt_id,
            bundle=bundle,
        )
        dependencies.artifact_publisher.write_scientific_cell_lock(
            lock
        )
        dependencies.artifact_publisher.publish_staged_directory(
            execution_attempt_id=config.execution_attempt_id,
            lock=lock,
        )
    except BaseException:
        operational = (
            OperationalFinalizationStatus.PUBLICATION_PENDING
        )

    close_evidence = _close_environment(
        dependencies.environment
    )
    close_failure_error_code: str | None = None
    if (
        not close_evidence.clean_close
        and operational
        is OperationalFinalizationStatus.PUBLISHED
    ):
        operational = (
            OperationalFinalizationStatus.CLOSE_FAILED_RECORDED
        )
        close_failure_error_code = (
            CloseFailureEvidenceCode
            .WORKER_REAPED_NO_CONTAMINATION.value
            if close_evidence.worker_reaped
            else CloseFailureEvidenceCode
            .WORKER_NOT_REAPED.value
        )

    terminal = _terminal_receipt(
        config=config,
        scientific=scientific,
        operational=operational,
        terminal_class=(
            "SCIENTIFIC_RESULT"
            if operational
            is OperationalFinalizationStatus.PUBLISHED
            else "POST_RESULT_OPERATIONAL_ERROR"
        ),
        error_code=(
            None
            if operational
            is OperationalFinalizationStatus.PUBLISHED
            else (
                close_failure_error_code
                if operational
                is OperationalFinalizationStatus.CLOSE_FAILED_RECORDED
                else operational.value
            )
        ),
        bundle=bundle,
    )
    if not _write_terminal_best_effort(
        publisher=dependencies.artifact_publisher,
        receipt=terminal,
    ):
        operational = (
            OperationalFinalizationStatus.ARTIFACT_IO_FAILED
        )

    return EpisodeAttemptResult(
        traces=tuple(traces),
        transitions=tuple(transitions),
        final_budget=budget,
        scientific_outcome_status=scientific,
        operational_finalization_status=operational,
        termination_reason=termination_reason,
        success=success,
        attempt_bundle=bundle,
    )
