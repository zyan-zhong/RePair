"""Immutable action provenance for RAW-BASELINE-V1.

The trace separates the proposed Phase-Critical Harness from the deterministic
controllers used by the frozen historical V7B.3c baseline. Historical source:
commit 206be4fce0c853754f353374bd89cda954190e14, evaluator lines 1398-1557.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import math
from typing import Any


type JsonScalar = None | bool | int | float | str
type FrozenJsonValue = JsonScalar | FrozenJsonArray | FrozenJsonObject


def sha256_text(text: str) -> str:
    """Return the SHA-256 hex digest of UTF-8 text."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_string_sequence(values: Sequence[str]) -> str:
    """Hash a string sequence with explicit JSON element boundaries."""

    canonical = json.dumps(
        list(values),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return sha256_text(canonical)


@dataclass(frozen=True, slots=True)
class FrozenJsonArray:
    """Immutable JSON array."""

    items: tuple[FrozenJsonValue, ...]

    def to_python(self) -> list[Any]:
        return [thaw_json(item) for item in self.items]


@dataclass(frozen=True, slots=True)
class FrozenJsonObject:
    """Immutable JSON object with canonical key order."""

    items: tuple[tuple[str, FrozenJsonValue], ...]

    def __post_init__(self) -> None:
        keys = tuple(key for key, _ in self.items)
        if keys != tuple(sorted(keys)):
            raise ValueError("FrozenJsonObject keys must be sorted")
        if len(keys) != len(set(keys)):
            raise ValueError("FrozenJsonObject keys must be unique")

    def to_python(self) -> dict[str, Any]:
        return {key: thaw_json(value) for key, value in self.items}


EMPTY_METADATA = FrozenJsonObject(())


def freeze_json(value: object) -> FrozenJsonValue:
    """Deep-freeze a JSON-compatible value and reject non-finite floats."""

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON metadata cannot contain NaN or infinity")
        return value
    if isinstance(value, FrozenJsonArray | FrozenJsonObject):
        return value
    if isinstance(value, Mapping):
        frozen_items: list[tuple[str, FrozenJsonValue]] = []
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError("JSON metadata object keys must be strings")
            frozen_items.append((key, freeze_json(value[key])))
        return FrozenJsonObject(tuple(frozen_items))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return FrozenJsonArray(tuple(freeze_json(item) for item in value))
    raise TypeError(f"unsupported JSON metadata type: {type(value).__name__}")


def thaw_json(value: FrozenJsonValue) -> Any:
    """Return a JSON-serialisable Python representation."""

    if isinstance(value, FrozenJsonObject):
        return value.to_python()
    if isinstance(value, FrozenJsonArray):
        return value.to_python()
    return value


class PipelineVariant(str, Enum):
    """Fixed, scientifically distinct decision pipelines."""

    RAW_V1 = "raw_v1"
    PHASE_CRITICAL_V1 = "phase_critical_v1"
    HISTORICAL_V7B3C = "historical_v7b3c"


class StageName(str, Enum):
    """Canonical action-transform stages; order is fixed by pipeline."""

    PHASE_CRITICAL_HARNESS = "phase_critical_harness"
    HISTORICAL_PHASE_CONTROLLER = "historical_phase_controller"
    HISTORICAL_ACTION_GUARD = "historical_action_guard"


class StageStatus(str, Enum):
    EXECUTED = "executed"
    SKIPPED = "skipped"


class ExecutionStatus(str, Enum):
    EXECUTED = "executed"
    NOT_EXECUTED = "not_executed"
    ENVIRONMENT_ERROR = "environment_error"


PIPELINE_STAGE_ORDER: dict[PipelineVariant, tuple[StageName, ...]] = {
    PipelineVariant.RAW_V1: (),
    PipelineVariant.PHASE_CRITICAL_V1: (StageName.PHASE_CRITICAL_HARNESS,),
    PipelineVariant.HISTORICAL_V7B3C: (
        StageName.HISTORICAL_PHASE_CONTROLLER,
        StageName.HISTORICAL_ACTION_GUARD,
    ),
}


def _validate_optional_nonempty_text(
    *,
    name: str,
    value: str | None,
) -> None:
    """Validate optional provenance text when supplied."""

    if value is None:
        return

    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be str or None"
        )

    if not value.strip():
        raise ValueError(
            f"{name} must be non-empty when supplied"
        )


def _validate_optional_nonnegative_int(
    *,
    name: str,
    value: int | None,
) -> None:
    """Validate an optional nonnegative integer."""

    if value is None:
        return

    if type(value) is not int:
        raise TypeError(
            f"{name} must be int or None"
        )

    if value < 0:
        raise ValueError(
            f"{name} must be non-negative"
        )


def _validate_optional_lower_sha256(
    *,
    name: str,
    value: str | None,
) -> None:
    """Validate an optional 64-character lowercase SHA-256."""

    if value is None:
        return

    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be str or None"
        )

    lower_hex = "0123456789abcdef"

    if (
        len(value) != 64
        or any(
            character not in lower_hex
            for character in value
        )
    ):
        raise ValueError(
            f"{name} must be a 64-character "
            "lowercase hexadecimal SHA-256"
        )


@dataclass(frozen=True, slots=True)
class TraceProvenance:
    """Identifiers needed to reproduce and locate one model decision."""

    run_id: str
    task_id: str
    episode_id: str
    replicate_id: int
    arm_id: str
    code_commit: str
    config_sha256: str
    provider: str
    model_name: str
    model_version: str | None
    provider_request_id: str | None
    retry_count: int
    timestamp_utc: str
    split_and_access_version: str | None = None
    split_name: str | None = None
    access_mode: str | None = None
    policy_version: str | None = None
    seed: int | None = None
    memory_version: str | None = None
    memory_state_sha256: str | None = None
    task_access_manifest_sha256: str | None = None
    policy_condition_manifest_sha256: str | None = None
    condition_run_schedule_sha256: str | None = None
    access_class: str | None = None
    policy_condition_id: str | None = None
    condition_cell_id: str | None = None
    evaluation_context: str | None = None
    logical_condition_id: str | None = None
    checkpoint_instance_id: str | None = None
    training_seed: int | None = None
    select_policy_runtime_manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        required = {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "episode_id": self.episode_id,
            "arm_id": self.arm_id,
            "code_commit": self.code_commit,
            "config_sha256": self.config_sha256,
            "provider": self.provider,
            "model_name": self.model_name,
            "timestamp_utc": self.timestamp_utc,
        }
        for name, value in required.items():
            if not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.replicate_id < 0:
            raise ValueError("replicate_id must be non-negative")
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        parsed = datetime.fromisoformat(self.timestamp_utc.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timestamp_utc must include a timezone")

        for name in (
            "split_and_access_version",
            "split_name",
            "access_mode",
            "policy_version",
            "memory_version",
        ):
            _validate_optional_nonempty_text(
                name=name,
                value=getattr(self, name),
            )

        _validate_optional_nonnegative_int(
            name="seed",
            value=self.seed,
        )

        _validate_optional_lower_sha256(
            name="memory_state_sha256",
            value=self.memory_state_sha256,
        )

        split_bundle = (
            self.split_and_access_version,
            self.split_name,
            self.access_mode,
        )

        split_present = tuple(
            value is not None
            for value in split_bundle
        )

        if any(split_present) and not all(
            split_present
        ):
            raise ValueError(
                "split provenance fields must be "
                "supplied together"
            )

        memory_bundle = (
            self.memory_version,
            self.memory_state_sha256,
        )

        memory_present = tuple(
            value is not None
            for value in memory_bundle
        )

        if any(memory_present) and not all(
            memory_present
        ):
            raise ValueError(
                "memory provenance fields must be "
                "supplied together"
            )

        condition_bundle = (
            self.task_access_manifest_sha256,
            self.policy_condition_manifest_sha256,
            self.condition_run_schedule_sha256,
            self.access_class,
            self.policy_condition_id,
            self.condition_cell_id,
        )

        condition_present = tuple(
            value is not None
            for value in condition_bundle
        )

        if (
            any(condition_present)
            and not all(condition_present)
        ):
            raise ValueError(
                "condition provenance fields must be supplied together"
            )

        for name in (
            "task_access_manifest_sha256",
            "policy_condition_manifest_sha256",
            "condition_run_schedule_sha256",
        ):
            _validate_optional_lower_sha256(
                name=name,
                value=getattr(self, name),
            )

        for name in (
            "access_class",
            "policy_condition_id",
            "condition_cell_id",
        ):
            _validate_optional_nonempty_text(
                name=name,
                value=getattr(self, name),
            )

        select_extras = (
            self.logical_condition_id,
            self.checkpoint_instance_id,
            self.training_seed,
            self.select_policy_runtime_manifest_sha256,
        )

        # ----------------------------------------------------
        # Legacy E1 / P1 DEV path
        # ----------------------------------------------------
        if self.evaluation_context is None:
            if any(
                value is not None
                for value in select_extras
            ):
                raise ValueError(
                    "SELECT provenance requires evaluation_context"
                )

            if all(condition_present):
                if self.access_class != "DEV_VISIBLE":
                    raise ValueError(
                        "P1 trace access_class must be DEV_VISIBLE"
                    )

                if (
                    self.policy_condition_id
                    != "P4-R0-PI0"
                ):
                    raise ValueError(
                        "P1 trace policy_condition_id "
                        "must be P4-R0-PI0"
                    )

        # ----------------------------------------------------
        # Formal Harness-OFF SELECT path
        # ----------------------------------------------------
        elif (
            self.evaluation_context
            == "P4_HARNESS_OFF_SELECT"
        ):
            if not all(condition_present):
                raise ValueError(
                    "SELECT trace requires complete "
                    "condition provenance"
                )

            if (
                self.access_class
                != "SELECT_SUMMARY_ONLY"
            ):
                raise ValueError(
                    "SELECT trace access_class mismatch"
                )

            for name in (
                "logical_condition_id",
                "checkpoint_instance_id",
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
                        f"SELECT trace requires {name}"
                    )

            if (
                self.select_policy_runtime_manifest_sha256
                is None
            ):
                raise ValueError(
                    "SELECT trace requires runtime manifest hash"
                )

            _validate_optional_lower_sha256(
                name=(
                    "select_policy_runtime_manifest_sha256"
                ),
                value=(
                    self
                    .select_policy_runtime_manifest_sha256
                ),
            )

            _validate_optional_nonnegative_int(
                name="training_seed",
                value=self.training_seed,
            )

            if (
                self.policy_condition_id
                != self.checkpoint_instance_id
            ):
                raise ValueError(
                    "SELECT trace policy/checkpoint mismatch"
                )

            if (
                self.split_and_access_version
                != "P4_SELECT_EVALUATION_LINEAGE_V1"
            ):
                raise ValueError(
                    "SELECT trace lineage identity mismatch"
                )

            # Original model version pi0
            if (
                self.logical_condition_id
                == "P4-R0-PI0"
            ):
                if self.training_seed is not None:
                    raise ValueError(
                        "SELECT pi0 trace forbids training_seed"
                    )

                if (
                    self.model_name
                    != "Qwen2.5-3B-Instruct-E1"
                ):
                    raise ValueError(
                        "SELECT pi0 model identity mismatch"
                    )

            # Trained model pi1:
            # three concrete LoRA realizations share
            # the same scientific logical condition.
            else:
                if self.training_seed is None:
                    raise ValueError(
                        "SELECT trained trace requires training_seed"
                    )

                if (
                    self.model_name
                    != self.checkpoint_instance_id
                ):
                    raise ValueError(
                        "SELECT trained model/checkpoint mismatch"
                    )

        else:
            raise ValueError(
                "unknown evaluation_context"
            )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "episode_id": self.episode_id,
            "replicate_id": self.replicate_id,
            "arm_id": self.arm_id,
            "code_commit": self.code_commit,
            "config_sha256": self.config_sha256,
            "provider": self.provider,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "provider_request_id": self.provider_request_id,
            "retry_count": self.retry_count,
            "timestamp_utc": self.timestamp_utc,
            "split_and_access_version": (
                self.split_and_access_version
            ),
            "split_name": self.split_name,
            "access_mode": self.access_mode,
            "policy_version": self.policy_version,
            "seed": self.seed,
            "memory_version": self.memory_version,
            "memory_state_sha256": (
                self.memory_state_sha256
            ),
        }
        if self.condition_cell_id is not None:
            result.update({
                "task_access_manifest_sha256": self.task_access_manifest_sha256,
                "policy_condition_manifest_sha256": self.policy_condition_manifest_sha256,
                "condition_run_schedule_sha256": self.condition_run_schedule_sha256,
                "access_class": self.access_class,
                "policy_condition_id": self.policy_condition_id,
                "condition_cell_id": self.condition_cell_id,
            })
        if self.evaluation_context is not None:
            result.update({
                "evaluation_context":
                    self.evaluation_context,
                "logical_condition_id":
                    self.logical_condition_id,
                "checkpoint_instance_id":
                    self.checkpoint_instance_id,
                "training_seed":
                    self.training_seed,
                "select_policy_runtime_manifest_sha256": (
                    self
                    .select_policy_runtime_manifest_sha256
                ),
            })

        return result


@dataclass(frozen=True, slots=True)
class ActionStage:
    """One named action-transform stage with immutable structured metadata."""

    name: StageName
    status: StageStatus
    input_action: str
    output_action: str
    metadata: FrozenJsonObject = EMPTY_METADATA

    def __post_init__(self) -> None:
        if self.status is StageStatus.SKIPPED and self.input_action != self.output_action:
            raise ValueError("skipped action stage cannot change the action")

    @classmethod
    def build(
        cls,
        *,
        name: StageName | str,
        status: StageStatus | str,
        input_action: str,
        output_action: str,
        metadata: Mapping[str, object] | FrozenJsonObject | None = None,
    ) -> "ActionStage":
        frozen = freeze_json({} if metadata is None else metadata)
        if not isinstance(frozen, FrozenJsonObject):
            raise TypeError("stage metadata must be a JSON object")
        return cls(
            name=StageName(name),
            status=StageStatus(status),
            input_action=input_action,
            output_action=output_action,
            metadata=frozen,
        )

    @property
    def changed(self) -> bool:
        return self.input_action != self.output_action

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "status": self.status.value,
            "input_action": self.input_action,
            "output_action": self.output_action,
            "changed": self.changed,
            "metadata": self.metadata.to_python(),
        }


@dataclass(frozen=True, slots=True)
class ActionTrace:
    """Immutable decision/action trace with a fixed pipeline definition."""

    provenance: TraceProvenance
    pipeline_variant: PipelineVariant
    model_call_index: int
    environment_step_index: int | None
    execution_status: ExecutionStatus
    public_task_goal: str
    public_task_goal_sha256: str
    observation: str
    observation_sha256: str
    prompt_text: str
    prompt_sha256: str
    admissible_commands: tuple[str, ...]
    admissible_commands_sha256: str
    raw_model_response: str
    raw_response_sha256: str
    literal_action: str
    parsed_phase: str | None
    model_reason: str | None
    parser_status: str
    parser_error: str | None
    parser_metadata: FrozenJsonObject
    literal_action_exactly_admissible: bool
    literal_action_casefold_admissible: bool
    stages: tuple[ActionStage, ...]
    final_executed_action: str | None
    final_action_admissible: bool | None
    attempt_outcome: str | None = None
    failure_stage: str | None = None
    failure_code: str | None = None
    normalized_action: str | None = None
    admissibility_status: str | None = None
    feedback_code: str | None = None
    policy_attempt_count_before: int | None = None
    policy_attempt_count_after: int | None = None
    environment_step_count_before: int | None = None
    environment_step_count_after: int | None = None
    protocol_failure_count: int | None = None
    inadmissible_action_count: int | None = None
    consecutive_nonexecuted_attempt_count: int | None = None
    episode_termination_reason: str | None = None
    submitted_environment_action: str | None = None
    resulting_observation: str | None = None
    resulting_observation_sha256: str | None = None
    environment_event_flags: FrozenJsonObject = EMPTY_METADATA
    protocol_failure_count_before: int | None = None
    inadmissible_action_count_before: int | None = None
    consecutive_nonexecuted_attempt_count_before: int | None = None

    def __post_init__(self) -> None:
        if self.model_call_index < 0:
            raise ValueError("model_call_index must be non-negative")
        if self.public_task_goal_sha256 != sha256_text(self.public_task_goal):
            raise ValueError("public_task_goal_sha256 does not match content")
        if self.observation_sha256 != sha256_text(self.observation):
            raise ValueError("observation_sha256 does not match content")
        if self.prompt_sha256 != sha256_text(self.prompt_text):
            raise ValueError("prompt_sha256 does not match content")
        if self.admissible_commands_sha256 != sha256_string_sequence(
            self.admissible_commands
        ):
            raise ValueError("admissible_commands_sha256 does not match content")
        if self.raw_response_sha256 != sha256_text(self.raw_model_response):
            raise ValueError("raw_response_sha256 does not match content")

        canonical = PIPELINE_STAGE_ORDER[self.pipeline_variant]
        names = tuple(stage.name for stage in self.stages)
        if names != canonical[: len(names)]:
            raise ValueError("stage names must follow the fixed pipeline order")

        previous = self.literal_action
        for stage in self.stages:
            if stage.input_action != previous:
                raise ValueError(
                    f"{stage.name.value}.input_action must equal previous output"
                )
            previous = stage.output_action

        if self.execution_status is ExecutionStatus.EXECUTED:
            if names != canonical:
                raise ValueError("executed trace must contain the full pipeline stage set")
            if self.environment_step_index is None or self.environment_step_index < 0:
                raise ValueError("executed trace requires a non-negative environment step")
            if self.final_executed_action is None:
                raise ValueError("executed trace requires final_executed_action")
            if self.final_action_admissible is None:
                raise ValueError("executed trace requires final_action_admissible")
            if self.final_executed_action != previous:
                raise ValueError("final_executed_action must equal final stage output")
        elif self.execution_status is ExecutionStatus.ENVIRONMENT_ERROR:
            if names != canonical:
                raise ValueError(
                    "environment-error trace must contain the full pipeline stage set"
                )
            if self.environment_step_index is None or self.environment_step_index < 0:
                raise ValueError(
                    "environment-error trace requires a non-negative environment step"
                )
            if self.final_executed_action is not None:
                raise ValueError(
                    "environment-error trace cannot have final_executed_action"
                )
            if self.final_action_admissible is not None:
                raise ValueError(
                    "environment-error trace cannot have final_action_admissible"
                )
        else:
            if self.environment_step_index is not None:
                raise ValueError("non-executed trace cannot have environment_step_index")
            if self.final_executed_action is not None:
                raise ValueError("non-executed trace cannot have final_executed_action")
            if self.final_action_admissible is not None:
                raise ValueError("non-executed trace cannot have admissibility result")

        if not isinstance(self.environment_event_flags, FrozenJsonObject):
            raise TypeError("environment_event_flags must be a FrozenJsonObject")

        if self.resulting_observation is None:
            if self.resulting_observation_sha256 is not None:
                raise ValueError(
                    "resulting_observation_sha256 requires resulting_observation"
                )
        elif self.resulting_observation_sha256 != sha256_text(
            self.resulting_observation
        ):
            raise ValueError(
                "resulting_observation_sha256 does not match content"
            )

        runtime_fields_supplied = (
            self.execution_status is ExecutionStatus.ENVIRONMENT_ERROR
            or any(
                value is not None
                for value in (
                    self.attempt_outcome,
                    self.failure_stage,
                    self.failure_code,
                    self.normalized_action,
                    self.admissibility_status,
                    self.feedback_code,
                    self.policy_attempt_count_before,
                    self.policy_attempt_count_after,
                    self.environment_step_count_before,
                    self.environment_step_count_after,
                    self.protocol_failure_count,
                    self.inadmissible_action_count,
                    self.consecutive_nonexecuted_attempt_count,
                    self.episode_termination_reason,
                    self.submitted_environment_action,
                    self.resulting_observation,
                    self.resulting_observation_sha256,
                    self.protocol_failure_count_before,
                    self.inadmissible_action_count_before,
                    (
                        self
                        .consecutive_nonexecuted_attempt_count_before
                    ),
                )
            )
            or self.environment_event_flags != EMPTY_METADATA
        )

        if runtime_fields_supplied:
            if (
                self.pipeline_variant
                is not PipelineVariant.RAW_V1
            ):
                raise ValueError(
                    "runtime-core fields require "
                    "RAW_V1 pipeline"
                )

            if self.stages:
                raise ValueError(
                    "runtime-core RAW trace cannot "
                    "contain action stages"
                )

            if self.parsed_phase is not None:
                raise ValueError(
                    "runtime-core RAW trace cannot "
                    "contain parsed_phase"
                )

            if self.model_reason is not None:
                raise ValueError(
                    "runtime-core RAW trace cannot "
                    "contain model_reason"
                )

            required_provenance = {
                "split_and_access_version": (
                    self.provenance
                    .split_and_access_version
                ),
                "split_name": (
                    self.provenance.split_name
                ),
                "access_mode": (
                    self.provenance.access_mode
                ),
                "policy_version": (
                    self.provenance.policy_version
                ),
                "seed": self.provenance.seed,
                "memory_version": (
                    self.provenance.memory_version
                ),
                "memory_state_sha256": (
                    self.provenance
                    .memory_state_sha256
                ),
            }

            missing_provenance = [
                name
                for name, value
                in required_provenance.items()
                if value is None
            ]

            if missing_provenance:
                raise ValueError(
                    "runtime-core trace provenance "
                    "is incomplete: "
                    + ", ".join(
                        missing_provenance
                    )
                )

            required_runtime_fields = {
                "attempt_outcome": self.attempt_outcome,
                "admissibility_status": self.admissibility_status,
                "policy_attempt_count_before": self.policy_attempt_count_before,
                "policy_attempt_count_after": self.policy_attempt_count_after,
                "environment_step_count_before": self.environment_step_count_before,
                "environment_step_count_after": self.environment_step_count_after,
                "protocol_failure_count": self.protocol_failure_count,
                "inadmissible_action_count": self.inadmissible_action_count,
                "consecutive_nonexecuted_attempt_count": (
                    self.consecutive_nonexecuted_attempt_count
                ),
                "protocol_failure_count_before": (
                    self.protocol_failure_count_before
                ),
                "inadmissible_action_count_before": (
                    self.inadmissible_action_count_before
                ),
                (
                    "consecutive_nonexecuted_"
                    "attempt_count_before"
                ): (
                    self
                    .consecutive_nonexecuted_attempt_count_before
                ),
            }

            missing = [
                name
                for name, value in required_runtime_fields.items()
                if value is None
            ]
            if missing:
                raise ValueError(
                    "runtime-core trace fields are incomplete: "
                    + ", ".join(missing)
                )

            for name in (
                "attempt_outcome",
                "failure_stage",
                "failure_code",
                "normalized_action",
                "admissibility_status",
                "feedback_code",
                "episode_termination_reason",
                "submitted_environment_action",
                "resulting_observation",
            ):
                value = getattr(self, name)
                if value is not None and not isinstance(value, str):
                    raise TypeError(f"{name} must be str or None")

            for name in (
                "policy_attempt_count_before",
                "policy_attempt_count_after",
                "environment_step_count_before",
                "environment_step_count_after",
                "protocol_failure_count",
                "inadmissible_action_count",
                "consecutive_nonexecuted_attempt_count",
                "protocol_failure_count_before",
                "inadmissible_action_count_before",
                (
                    "consecutive_nonexecuted_"
                    "attempt_count_before"
                ),
            ):
                _validate_optional_nonnegative_int(
                    name=name,
                    value=getattr(self, name),
                )

            policy_before = self.policy_attempt_count_before
            policy_after = self.policy_attempt_count_after
            environment_before = self.environment_step_count_before
            environment_after = self.environment_step_count_after

            protocol_before = (
                self.protocol_failure_count_before
            )
            inadmissible_before = (
                self.inadmissible_action_count_before
            )
            consecutive_before = (
                self
                .consecutive_nonexecuted_attempt_count_before
            )

            protocol_after = (
                self.protocol_failure_count
            )
            inadmissible_after = (
                self.inadmissible_action_count
            )
            consecutive_after = (
                self
                .consecutive_nonexecuted_attempt_count
            )

            if policy_before is None or policy_after is None:
                raise AssertionError("validated policy counters are missing")
            if environment_before is None or environment_after is None:
                raise AssertionError("validated environment counters are missing")

            if (
                protocol_before is None
                or inadmissible_before is None
                or consecutive_before is None
                or protocol_after is None
                or inadmissible_after is None
                or consecutive_after is None
            ):
                raise AssertionError(
                    "validated counter lineage is missing"
                )

            if policy_after != policy_before + 1:
                raise ValueError(
                    "policy_attempt_count_after must equal "
                    "policy_attempt_count_before + 1"
                )

            # Report an impossible starting component before deriving
            # deltas from that already-invalid state.
            if environment_before > policy_before:
                raise ValueError(
                    "environment_step_count_before cannot "
                    "exceed policy_attempt_count_before"
                )

            if protocol_before > policy_before:
                raise ValueError(
                    "protocol_failure_count_before cannot "
                    "exceed policy_attempt_count_before"
                )

            if inadmissible_before > policy_before:
                raise ValueError(
                    "inadmissible_action_count_before cannot "
                    "exceed policy_attempt_count_before"
                )

            environment_delta = environment_after - environment_before

            if environment_delta not in (0, 1):
                raise ValueError(
                    "environment_step_count must increase by zero or one"
                )

            # A format or off-list result did not call the environment.
            # Report this direct outcome violation before the aggregate
            # after-state conservation check.
            if (
                self.attempt_outcome
                in {
                    "FORMAT_PROTOCOL_FAILURE",
                    "ACTION_NOT_ADMISSIBLE",
                }
                and environment_delta != 0
            ):
                raise ValueError(
                    "environment_step_count cannot increase "
                    "for a nonexecuted outcome"
                )

            if policy_before != (
                environment_before
                + protocol_before
                + inadmissible_before
            ):
                raise ValueError(
                    "before counter conservation failed"
                )

            if policy_after != (
                environment_after
                + protocol_after
                + inadmissible_after
            ):
                raise ValueError(
                    "after counter conservation failed"
                )

            if self.model_call_index != policy_before:
                raise ValueError(
                    "model_call_index must equal "
                    "policy_attempt_count_before"
                )

            allowed_outcomes = {
                "ACTION_EXECUTED",
                "FORMAT_PROTOCOL_FAILURE",
                "ACTION_NOT_ADMISSIBLE",
                "INFRASTRUCTURE_ERROR",
            }
            if self.attempt_outcome not in allowed_outcomes:
                raise ValueError("attempt_outcome is not recognized")

            allowed_admissibility = {
                "not_checked",
                "exact_member",
                "not_admissible",
            }
            if self.admissibility_status not in allowed_admissibility:
                raise ValueError("admissibility_status is not recognized")

            if (
                self.attempt_outcome
                == "FORMAT_PROTOCOL_FAILURE"
            ):
                if self.parser_status != "failed":
                    raise ValueError(
                        "format failure requires "
                        "failed parser_status"
                    )
            else:
                if self.parser_status != "success":
                    raise ValueError(
                        "non-format runtime outcome "
                        "requires successful parser_status"
                    )

                if self.normalized_action is None:
                    raise ValueError(
                        "non-format runtime outcome "
                        "requires normalized_action"
                    )

                if (
                    self.literal_action
                    != self.normalized_action
                ):
                    raise ValueError(
                        "literal_action must equal "
                        "normalized_action for RAW "
                        "runtime traces"
                    )

            if self.attempt_outcome == "FORMAT_PROTOCOL_FAILURE":
                if self.execution_status is not ExecutionStatus.NOT_EXECUTED:
                    raise ValueError(
                        "FORMAT_PROTOCOL_FAILURE requires not_executed status"
                    )
                if environment_delta != 0:
                    raise ValueError(
                        "environment_step_count cannot increase for a format failure"
                    )

                if protocol_after != protocol_before + 1:
                    raise ValueError(
                        "format failure must increment "
                        "protocol_failure_count"
                    )

                if inadmissible_after != inadmissible_before:
                    raise ValueError(
                        "format failure cannot change "
                        "inadmissible_action_count"
                    )

                if consecutive_after != consecutive_before + 1:
                    raise ValueError(
                        "format failure must increment "
                        "consecutive nonexecuted count"
                    )

                if self.failure_stage not in ("envelope", "action_normalization"):
                    raise ValueError(
                        "FORMAT_PROTOCOL_FAILURE requires an envelope or "
                        "action_normalization failure_stage"
                    )
                if self.failure_code is None:
                    raise ValueError("format failure requires failure_code")
                if self.normalized_action is not None:
                    raise ValueError(
                        "format failure cannot have normalized_action"
                    )
                if self.admissibility_status != "not_checked":
                    raise ValueError(
                        "format failure requires not_checked admissibility"
                    )
                if self.feedback_code != "FORMAT_ERROR_V1":
                    raise ValueError(
                        "format failure requires FORMAT_ERROR_V1 feedback"
                    )
                if self.parser_error is None:
                    raise ValueError("format failure requires parser_error")
                if self.literal_action != "":
                    raise ValueError(
                        "format failure requires empty "
                        "literal_action"
                    )
                if (
                    self.environment_event_flags
                    != EMPTY_METADATA
                ):
                    raise ValueError(
                        "format failure requires empty "
                        "environment_event_flags"
                    )
                if self.submitted_environment_action is not None:
                    raise ValueError(
                        "format failure cannot submit an environment action"
                    )
                if self.resulting_observation is not None:
                    raise ValueError(
                        "format failure cannot have resulting_observation"
                    )

            elif self.attempt_outcome == "ACTION_NOT_ADMISSIBLE":
                if self.execution_status is not ExecutionStatus.NOT_EXECUTED:
                    raise ValueError(
                        "ACTION_NOT_ADMISSIBLE requires not_executed status"
                    )
                if environment_delta != 0:
                    raise ValueError(
                        "environment_step_count cannot increase for "
                        "an inadmissible action"
                    )

                if protocol_after != protocol_before:
                    raise ValueError(
                        "inadmissible action cannot change "
                        "protocol_failure_count"
                    )

                if inadmissible_after != inadmissible_before + 1:
                    raise ValueError(
                        "inadmissible action must increment "
                        "inadmissible_action_count"
                    )

                if consecutive_after != consecutive_before + 1:
                    raise ValueError(
                        "inadmissible action must increment "
                        "consecutive nonexecuted count"
                    )

                if self.failure_stage != "admissibility":
                    raise ValueError(
                        "ACTION_NOT_ADMISSIBLE requires admissibility failure_stage"
                    )
                if self.failure_code != "ACTION_NOT_ADMISSIBLE":
                    raise ValueError(
                        "ACTION_NOT_ADMISSIBLE requires matching failure_code"
                    )
                if self.normalized_action is None:
                    raise ValueError(
                        "inadmissible action requires normalized_action"
                    )
                if self.admissibility_status != "not_admissible":
                    raise ValueError(
                        "inadmissible action requires not_admissible status"
                    )
                if self.feedback_code != "INVALID_ACTION_V1":
                    raise ValueError(
                        "inadmissible action requires INVALID_ACTION_V1 feedback"
                    )
                if self.parser_error is not None:
                    raise ValueError(
                        "admissibility failure requires parser success"
                    )
                if (
                    self.environment_event_flags
                    != EMPTY_METADATA
                ):
                    raise ValueError(
                        "inadmissible action requires "
                        "empty environment_event_flags"
                    )
                if self.submitted_environment_action is not None:
                    raise ValueError(
                        "inadmissible action cannot submit an environment action"
                    )
                if self.resulting_observation is not None:
                    raise ValueError(
                        "inadmissible action cannot have resulting_observation"
                    )

            elif self.attempt_outcome == "ACTION_EXECUTED":
                if self.execution_status is not ExecutionStatus.EXECUTED:
                    raise ValueError(
                        "ACTION_EXECUTED requires executed status"
                    )
                if environment_delta != 1:
                    raise ValueError(
                        "environment_step_count must increase by one "
                        "for an executed action"
                    )

                if (
                    self.environment_step_index
                    != environment_before
                ):
                    raise ValueError(
                        "environment_step_index must equal "
                        "environment_step_count_before"
                    )

                if protocol_after != protocol_before:
                    raise ValueError(
                        "executed action cannot change "
                        "protocol_failure_count"
                    )

                if inadmissible_after != inadmissible_before:
                    raise ValueError(
                        "executed action cannot change "
                        "inadmissible_action_count"
                    )

                if consecutive_after != 0:
                    raise ValueError(
                        "executed action must clear "
                        "consecutive nonexecuted count"
                    )

                if self.failure_stage is not None or self.failure_code is not None:
                    raise ValueError(
                        "executed action cannot have a failure stage or code"
                    )
                if self.normalized_action is None:
                    raise ValueError(
                        "executed action requires normalized_action"
                    )
                if self.admissibility_status != "exact_member":
                    raise ValueError(
                        "executed action requires exact_member admissibility"
                    )
                if self.feedback_code is not None:
                    raise ValueError("executed action cannot have feedback_code")
                if self.parser_error is not None:
                    raise ValueError("executed action requires parser success")
                if self.submitted_environment_action is None:
                    raise ValueError(
                        "executed action requires submitted_environment_action"
                    )
                if self.submitted_environment_action != self.normalized_action:
                    raise ValueError(
                        "submitted_environment_action must equal normalized_action"
                    )
                if self.final_executed_action != self.submitted_environment_action:
                    raise ValueError(
                        "final_executed_action must equal submitted_environment_action"
                    )
                if self.resulting_observation is None:
                    raise ValueError(
                        "executed action requires resulting_observation"
                    )
                if self.final_action_admissible is not True:
                    raise ValueError(
                        "executed action requires "
                        "final_action_admissible=True"
                    )
                if (
                    self
                    .consecutive_nonexecuted_attempt_count
                    != 0
                ):
                    raise ValueError(
                        "executed action must clear "
                        "consecutive nonexecuted count"
                    )

            else:
                if self.execution_status is not ExecutionStatus.ENVIRONMENT_ERROR:
                    raise ValueError(
                        "INFRASTRUCTURE_ERROR requires environment_error status"
                    )
                if environment_delta != 1:
                    raise ValueError(
                        "environment_step_count must increase by one "
                        "for an infrastructure error"
                    )

                if (
                    self.environment_step_index
                    != environment_before
                ):
                    raise ValueError(
                        "environment_step_index must equal "
                        "environment_step_count_before"
                    )

                if protocol_after != protocol_before:
                    raise ValueError(
                        "infrastructure error cannot change "
                        "protocol_failure_count"
                    )

                if inadmissible_after != inadmissible_before:
                    raise ValueError(
                        "infrastructure error cannot change "
                        "inadmissible_action_count"
                    )

                if consecutive_after != 0:
                    raise ValueError(
                        "infrastructure error must clear "
                        "consecutive nonexecuted count"
                    )

                if self.failure_stage != "infrastructure":
                    raise ValueError(
                        "INFRASTRUCTURE_ERROR requires infrastructure failure_stage"
                    )
                if self.failure_code != "ENVIRONMENT_STEP_FAILED":
                    raise ValueError(
                        "INFRASTRUCTURE_ERROR requires ENVIRONMENT_STEP_FAILED"
                    )
                if self.normalized_action is None:
                    raise ValueError(
                        "infrastructure error requires normalized_action"
                    )
                if self.admissibility_status != "exact_member":
                    raise ValueError(
                        "infrastructure error requires exact_member admissibility"
                    )
                if self.feedback_code is not None:
                    raise ValueError(
                        "infrastructure error cannot have feedback_code"
                    )
                if self.parser_error is not None:
                    raise ValueError(
                        "infrastructure error requires parser success"
                    )
                if self.submitted_environment_action is None:
                    raise ValueError(
                        "infrastructure error requires submitted_environment_action"
                    )
                if self.submitted_environment_action != self.normalized_action:
                    raise ValueError(
                        "submitted_environment_action must equal normalized_action"
                    )
                if self.submitted_environment_action != previous:
                    raise ValueError(
                        "submitted_environment_action must equal final stage output"
                    )
                if self.resulting_observation is not None:
                    raise ValueError(
                        "infrastructure error cannot have resulting_observation"
                    )
                if self.resulting_observation_sha256 is not None:
                    raise ValueError(
                        "infrastructure error cannot have "
                        "resulting_observation_sha256"
                    )
                if self.episode_termination_reason != "INFRASTRUCTURE_ERROR":
                    raise ValueError(
                        "infrastructure error requires INFRASTRUCTURE_ERROR termination"
                    )

                if (
                    self
                    .consecutive_nonexecuted_attempt_count
                    != 0
                ):
                    raise ValueError(
                        "infrastructure error must clear "
                        "consecutive nonexecuted count"
                    )

                event_flags = (
                    self.environment_event_flags
                    .to_python()
                )

                if set(event_flags) != {
                    "exception_type"
                }:
                    raise ValueError(
                        "infrastructure error flags "
                        "must contain exactly "
                        "exception_type"
                    )

                exception_type = event_flags[
                    "exception_type"
                ]

                if (
                    not isinstance(
                        exception_type,
                        str,
                    )
                    or not exception_type.strip()
                ):
                    raise ValueError(
                        "exception_type must be a "
                        "nonblank string"
                    )


    @classmethod
    def build(
        cls,
        *,
        provenance: TraceProvenance,
        pipeline_variant: PipelineVariant | str,
        model_call_index: int,
        environment_step_index: int | None,
        execution_status: ExecutionStatus | str,
        public_task_goal: str,
        observation: str,
        prompt_text: str,
        admissible_commands: Sequence[str],
        raw_model_response: str,
        literal_action: str,
        parsed_phase: str | None,
        model_reason: str | None,
        parser_status: str,
        parser_error: str | None,
        parser_metadata: Mapping[str, object] | FrozenJsonObject | None,
        literal_action_exactly_admissible: bool,
        literal_action_casefold_admissible: bool,
        stages: Sequence[ActionStage],
        final_executed_action: str | None,
        final_action_admissible: bool | None,
        attempt_outcome: str | None = None,
        failure_stage: str | None = None,
        failure_code: str | None = None,
        normalized_action: str | None = None,
        admissibility_status: str | None = None,
        feedback_code: str | None = None,
        policy_attempt_count_before: int | None = None,
        policy_attempt_count_after: int | None = None,
        environment_step_count_before: int | None = None,
        environment_step_count_after: int | None = None,
        protocol_failure_count: int | None = None,
        inadmissible_action_count: int | None = None,
        consecutive_nonexecuted_attempt_count: int | None = None,
        episode_termination_reason: str | None = None,
        submitted_environment_action: str | None = None,
        resulting_observation: str | None = None,
        environment_event_flags: (
            Mapping[str, object]
            | FrozenJsonObject
            | None
        ) = None,
        protocol_failure_count_before: int | None = None,
        inadmissible_action_count_before: int | None = None,
        consecutive_nonexecuted_attempt_count_before: (
            int | None
        ) = None,
    ) -> "ActionTrace":
        frozen_parser_metadata = freeze_json(
            {} if parser_metadata is None else parser_metadata
        )
        if not isinstance(frozen_parser_metadata, FrozenJsonObject):
            raise TypeError("parser_metadata must be a JSON object")
        frozen_environment_event_flags = freeze_json(
            {} if environment_event_flags is None else environment_event_flags
        )
        if not isinstance(frozen_environment_event_flags, FrozenJsonObject):
            raise TypeError("environment_event_flags must be a JSON object")

        resulting_observation_sha256 = (
            None
            if resulting_observation is None
            else sha256_text(resulting_observation)
        )

        commands = tuple(admissible_commands)
        return cls(
            provenance=provenance,
            pipeline_variant=PipelineVariant(pipeline_variant),
            model_call_index=model_call_index,
            environment_step_index=environment_step_index,
            execution_status=ExecutionStatus(execution_status),
            public_task_goal=public_task_goal,
            public_task_goal_sha256=sha256_text(public_task_goal),
            observation=observation,
            observation_sha256=sha256_text(observation),
            prompt_text=prompt_text,
            prompt_sha256=sha256_text(prompt_text),
            admissible_commands=commands,
            admissible_commands_sha256=sha256_string_sequence(commands),
            raw_model_response=raw_model_response,
            raw_response_sha256=sha256_text(raw_model_response),
            literal_action=literal_action,
            parsed_phase=parsed_phase,
            model_reason=model_reason,
            parser_status=parser_status,
            parser_error=parser_error,
            parser_metadata=frozen_parser_metadata,
            literal_action_exactly_admissible=literal_action_exactly_admissible,
            literal_action_casefold_admissible=literal_action_casefold_admissible,
            stages=tuple(stages),
            final_executed_action=final_executed_action,
            final_action_admissible=final_action_admissible,
            attempt_outcome=attempt_outcome,
            failure_stage=failure_stage,
            failure_code=failure_code,
            normalized_action=normalized_action,
            admissibility_status=admissibility_status,
            feedback_code=feedback_code,
            policy_attempt_count_before=policy_attempt_count_before,
            policy_attempt_count_after=policy_attempt_count_after,
            environment_step_count_before=environment_step_count_before,
            environment_step_count_after=environment_step_count_after,
            protocol_failure_count=protocol_failure_count,
            inadmissible_action_count=inadmissible_action_count,
            consecutive_nonexecuted_attempt_count=(
                consecutive_nonexecuted_attempt_count
            ),
            episode_termination_reason=episode_termination_reason,
            submitted_environment_action=submitted_environment_action,
            resulting_observation=resulting_observation,
            resulting_observation_sha256=resulting_observation_sha256,
            environment_event_flags=frozen_environment_event_flags,
            protocol_failure_count_before=(
                protocol_failure_count_before
            ),
            inadmissible_action_count_before=(
                inadmissible_action_count_before
            ),
            consecutive_nonexecuted_attempt_count_before=(
                consecutive_nonexecuted_attempt_count_before
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "pipeline_variant": self.pipeline_variant.value,
            "model_call_index": self.model_call_index,
            "environment_step_index": self.environment_step_index,
            "execution_status": self.execution_status.value,
            "public_task_goal": self.public_task_goal,
            "public_task_goal_sha256": self.public_task_goal_sha256,
            "observation": self.observation,
            "observation_sha256": self.observation_sha256,
            "prompt_text": self.prompt_text,
            "prompt_sha256": self.prompt_sha256,
            "admissible_commands": list(self.admissible_commands),
            "admissible_commands_sha256": self.admissible_commands_sha256,
            "raw_model_response": self.raw_model_response,
            "raw_response_sha256": self.raw_response_sha256,
            "literal_action": self.literal_action,
            "parsed_phase": self.parsed_phase,
            "model_reason": self.model_reason,
            "parser_status": self.parser_status,
            "parser_error": self.parser_error,
            "parser_metadata": self.parser_metadata.to_python(),
            "literal_action_exactly_admissible": self.literal_action_exactly_admissible,
            "literal_action_casefold_admissible": self.literal_action_casefold_admissible,
            "stages": [stage.to_dict() for stage in self.stages],
            "final_executed_action": self.final_executed_action,
            "final_action_admissible": self.final_action_admissible,
            "attempt_outcome": self.attempt_outcome,
            "failure_stage": self.failure_stage,
            "failure_code": self.failure_code,
            "normalized_action": self.normalized_action,
            "admissibility_status": self.admissibility_status,
            "feedback_code": self.feedback_code,
            "policy_attempt_count_before": self.policy_attempt_count_before,
            "policy_attempt_count_after": self.policy_attempt_count_after,
            "environment_step_count_before": self.environment_step_count_before,
            "environment_step_count_after": self.environment_step_count_after,
            "protocol_failure_count": self.protocol_failure_count,
            "inadmissible_action_count": self.inadmissible_action_count,
            "consecutive_nonexecuted_attempt_count": (
                self.consecutive_nonexecuted_attempt_count
            ),
            "episode_termination_reason": self.episode_termination_reason,
            "submitted_environment_action": self.submitted_environment_action,
            "resulting_observation": self.resulting_observation,
            "resulting_observation_sha256": self.resulting_observation_sha256,
            "environment_event_flags": (
                self.environment_event_flags.to_python()
            ),
            "protocol_failure_count_before": (
                self.protocol_failure_count_before
            ),
            "inadmissible_action_count_before": (
                self.inadmissible_action_count_before
            ),
            (
                "consecutive_nonexecuted_"
                "attempt_count_before"
            ): (
                self
                .consecutive_nonexecuted_attempt_count_before
            ),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
