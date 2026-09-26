"""Frozen in-memory models for E1 evaluator wire artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Self

from .canonical_evidence import (
    canonical_json_text,
    strict_json_loads,
)
from .schema_contract import (
    validate_payload_against_schema,
)


def _require_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("wire value must be a JSON object")
    if any(not isinstance(key, str) for key in value):
        raise TypeError("wire object keys must be strings")
    return value


def _expect_keys(
    payload: dict[str, object],
    expected: set[str],
) -> None:
    observed = set(payload)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise ValueError(
            f"wire object is missing required fields: {missing}"
        )
    if unknown:
        raise ValueError(
            f"wire object contains unknown fields: {unknown}"
        )


def _tuple_of_strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a JSON array")
    if any(not isinstance(item, str) for item in value):
        raise TypeError(f"{name} items must be strings")
    return tuple(value)


def _tuple_of_ints(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a JSON array")
    if any(type(item) is not int for item in value):
        raise TypeError(f"{name} items must be integers")
    return tuple(value)


class _SchemaModel:
    SCHEMA_ID: ClassVar[str]
    SCHEMA_VERSION: ClassVar[int] = 1

    def to_dict(self) -> dict[str, object]:
        raise NotImplementedError

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())

    @classmethod
    def from_json(cls, value: str | bytes) -> Self:
        return cls.from_dict(strict_json_loads(value))

    @classmethod
    def from_dict(cls, value: object) -> Self:
        raise NotImplementedError

    def _validate(self) -> None:
        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )


@dataclass(frozen=True, slots=True)
class BudgetSnapshotV1:
    policy_attempt_count: int
    environment_step_count: int
    protocol_failure_count: int
    inadmissible_action_count: int
    consecutive_nonexecuted_attempt_count: int

    _KEYS: ClassVar[set[str]] = {
        "policy_attempt_count",
        "environment_step_count",
        "protocol_failure_count",
        "inadmissible_action_count",
        "consecutive_nonexecuted_attempt_count",
    }

    def __post_init__(self) -> None:
        for name in self._KEYS:
            value = getattr(self, name)
            if type(value) is not int:
                raise TypeError(f"{name} must be int")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_attempt_count": self.policy_attempt_count,
            "environment_step_count": self.environment_step_count,
            "protocol_failure_count": self.protocol_failure_count,
            "inadmissible_action_count": self.inadmissible_action_count,
            "consecutive_nonexecuted_attempt_count": (
                self.consecutive_nonexecuted_attempt_count
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> "BudgetSnapshotV1":
        payload = _require_mapping(value)
        _expect_keys(payload, cls._KEYS)
        return cls(
            policy_attempt_count=payload["policy_attempt_count"],
            environment_step_count=payload["environment_step_count"],
            protocol_failure_count=payload["protocol_failure_count"],
            inadmissible_action_count=payload["inadmissible_action_count"],
            consecutive_nonexecuted_attempt_count=(
                payload["consecutive_nonexecuted_attempt_count"]
            ),
        )


@dataclass(frozen=True, slots=True)
class RunScheduleCellV1:
    scheduled_cell_id: str
    task_index: int
    task_id: str
    seed: int

    _KEYS: ClassVar[set[str]] = {
        "scheduled_cell_id",
        "task_index",
        "task_id",
        "seed",
    }

    def __post_init__(self) -> None:
        for name in ("scheduled_cell_id", "task_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be non-empty")
        for name in ("task_index", "seed"):
            value = getattr(self, name)
            if type(value) is not int:
                raise TypeError(f"{name} must be int")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "scheduled_cell_id": self.scheduled_cell_id,
            "task_index": self.task_index,
            "task_id": self.task_id,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, value: object) -> "RunScheduleCellV1":
        payload = _require_mapping(value)
        _expect_keys(payload, cls._KEYS)
        return cls(
            scheduled_cell_id=payload["scheduled_cell_id"],
            task_index=payload["task_index"],
            task_id=payload["task_id"],
            seed=payload["seed"],
        )


@dataclass(frozen=True, slots=True)
class PublicTransitionRecordV1(_SchemaModel):
    SCHEMA_ID: ClassVar[str] = "E1_PUBLIC_TRANSITION_RECORD_V1"

    schema_id: str
    schema_version: int
    scheduled_cell_id: str
    execution_attempt_id: str
    model_call_index: int
    environment_step_index: int
    submitted_action: str
    pre_action_observation: str
    pre_action_observation_sha256: str
    pre_action_admissible_commands: tuple[str, ...]
    pre_action_admissible_commands_sha256: str
    resulting_observation: str
    resulting_observation_sha256: str
    resulting_admissible_commands: tuple[str, ...]
    resulting_admissible_commands_sha256: str
    done: bool
    won: bool
    score: int | float
    pre_action_visibility: str
    resulting_visibility: str

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "scheduled_cell_id",
        "execution_attempt_id",
        "model_call_index",
        "environment_step_index",
        "submitted_action",
        "pre_action_observation",
        "pre_action_observation_sha256",
        "pre_action_admissible_commands",
        "pre_action_admissible_commands_sha256",
        "resulting_observation",
        "resulting_observation_sha256",
        "resulting_admissible_commands",
        "resulting_admissible_commands_sha256",
        "done",
        "won",
        "score",
        "pre_action_visibility",
        "resulting_visibility",
    }

    def __post_init__(self) -> None:
        self._validate()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "scheduled_cell_id": self.scheduled_cell_id,
            "execution_attempt_id": self.execution_attempt_id,
            "model_call_index": self.model_call_index,
            "environment_step_index": self.environment_step_index,
            "submitted_action": self.submitted_action,
            "pre_action_observation": self.pre_action_observation,
            "pre_action_observation_sha256": (
                self.pre_action_observation_sha256
            ),
            "pre_action_admissible_commands": list(
                self.pre_action_admissible_commands
            ),
            "pre_action_admissible_commands_sha256": (
                self.pre_action_admissible_commands_sha256
            ),
            "resulting_observation": self.resulting_observation,
            "resulting_observation_sha256": (
                self.resulting_observation_sha256
            ),
            "resulting_admissible_commands": list(
                self.resulting_admissible_commands
            ),
            "resulting_admissible_commands_sha256": (
                self.resulting_admissible_commands_sha256
            ),
            "done": self.done,
            "won": self.won,
            "score": self.score,
            "pre_action_visibility": self.pre_action_visibility,
            "resulting_visibility": self.resulting_visibility,
        }

    @classmethod
    def from_dict(cls, value: object) -> "PublicTransitionRecordV1":
        payload = _require_mapping(value)
        _expect_keys(payload, cls._KEYS)
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            scheduled_cell_id=payload["scheduled_cell_id"],
            execution_attempt_id=payload["execution_attempt_id"],
            model_call_index=payload["model_call_index"],
            environment_step_index=payload["environment_step_index"],
            submitted_action=payload["submitted_action"],
            pre_action_observation=payload["pre_action_observation"],
            pre_action_observation_sha256=(
                payload["pre_action_observation_sha256"]
            ),
            pre_action_admissible_commands=_tuple_of_strings(
                payload["pre_action_admissible_commands"],
                "pre_action_admissible_commands",
            ),
            pre_action_admissible_commands_sha256=(
                payload["pre_action_admissible_commands_sha256"]
            ),
            resulting_observation=payload["resulting_observation"],
            resulting_observation_sha256=(
                payload["resulting_observation_sha256"]
            ),
            resulting_admissible_commands=_tuple_of_strings(
                payload["resulting_admissible_commands"],
                "resulting_admissible_commands",
            ),
            resulting_admissible_commands_sha256=(
                payload["resulting_admissible_commands_sha256"]
            ),
            done=payload["done"],
            won=payload["won"],
            score=payload["score"],
            pre_action_visibility=payload["pre_action_visibility"],
            resulting_visibility=payload["resulting_visibility"],
        )


@dataclass(frozen=True, slots=True)
class AttemptReceiptV1(_SchemaModel):
    SCHEMA_ID: ClassVar[str] = "E1_ATTEMPT_RECEIPT_V1"

    schema_id: str
    schema_version: int
    receipt_kind: str
    run_id: str
    scheduled_cell_id: str
    execution_attempt_id: str
    attempt_ordinal: int
    evaluator_commit: str
    design_merge_commit: str
    runtime_core_commit: str
    run_schedule_sha256: str
    scientific_outcome_status: str
    operational_finalization_status: str
    episode_semantic_sha256: str | None
    attempt_bundle_sha256: str | None
    terminal_class: str | None
    error_code: str | None
    created_at_utc: str

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "receipt_kind",
        "run_id",
        "scheduled_cell_id",
        "execution_attempt_id",
        "attempt_ordinal",
        "evaluator_commit",
        "design_merge_commit",
        "runtime_core_commit",
        "run_schedule_sha256",
        "scientific_outcome_status",
        "operational_finalization_status",
        "episode_semantic_sha256",
        "attempt_bundle_sha256",
        "terminal_class",
        "error_code",
        "created_at_utc",
    }

    def __post_init__(self) -> None:
        self._validate()

    def to_dict(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in (
                "schema_id",
                "schema_version",
                "receipt_kind",
                "run_id",
                "scheduled_cell_id",
                "execution_attempt_id",
                "attempt_ordinal",
                "evaluator_commit",
                "design_merge_commit",
                "runtime_core_commit",
                "run_schedule_sha256",
                "scientific_outcome_status",
                "operational_finalization_status",
                "episode_semantic_sha256",
                "attempt_bundle_sha256",
                "terminal_class",
                "error_code",
                "created_at_utc",
            )
        }

    @classmethod
    def from_dict(cls, value: object) -> "AttemptReceiptV1":
        payload = _require_mapping(value)
        _expect_keys(payload, cls._KEYS)
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class ScientificCellLockV1(_SchemaModel):
    SCHEMA_ID: ClassVar[str] = "E1_SCIENTIFIC_CELL_LOCK_V1"

    schema_id: str
    schema_version: int
    run_id: str
    scheduled_cell_id: str
    execution_attempt_id: str
    run_schedule_sha256: str
    episode_semantic_sha256: str
    attempt_bundle_sha256: str
    scientific_outcome_status: str
    evaluator_commit: str

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "run_id",
        "scheduled_cell_id",
        "execution_attempt_id",
        "run_schedule_sha256",
        "episode_semantic_sha256",
        "attempt_bundle_sha256",
        "scientific_outcome_status",
        "evaluator_commit",
    }

    def __post_init__(self) -> None:
        self._validate()

    def to_dict(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in (
                "schema_id",
                "schema_version",
                "run_id",
                "scheduled_cell_id",
                "execution_attempt_id",
                "run_schedule_sha256",
                "episode_semantic_sha256",
                "attempt_bundle_sha256",
                "scientific_outcome_status",
                "evaluator_commit",
            )
        }

    @classmethod
    def from_dict(cls, value: object) -> "ScientificCellLockV1":
        payload = _require_mapping(value)
        _expect_keys(payload, cls._KEYS)
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class EpisodeArtifactV1(_SchemaModel):
    SCHEMA_ID: ClassVar[str] = "E1_EPISODE_ARTIFACT_V1"

    schema_id: str
    schema_version: int
    run_id: str
    scheduled_cell_id: str
    execution_attempt_id: str
    attempt_ordinal: int
    task_index: int
    task_id: str
    task_type: str
    gamefile_sha1: str
    gamefile_sha256: str
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
    scientific_outcome_status: str
    operational_finalization_status: str
    success: bool | None
    termination_reason: str
    final_score: int | float | None
    final_done: bool | None
    final_won: bool | None
    final_budget: BudgetSnapshotV1
    trace_count: int
    public_transition_count: int
    environment_call_trace_count: int
    initial_observation_sha256: str
    final_observation_sha256: str
    episode_semantic_sha256: str
    started_at_utc: str
    completed_at_utc: str
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

    _P1_KEYS: ClassVar[set[str]] = {
        "task_access_manifest_sha256",
        "policy_condition_manifest_sha256",
        "condition_run_schedule_sha256",
        "access_class",
        "policy_condition_id",
        "condition_cell_id",
    }

    _SELECT_KEYS: ClassVar[set[str]] = {
        "evaluation_context",
        "logical_condition_id",
        "checkpoint_instance_id",
        "training_seed",
        "select_policy_runtime_manifest_sha256",
    }

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "run_id",
        "scheduled_cell_id",
        "execution_attempt_id",
        "attempt_ordinal",
        "task_index",
        "task_id",
        "task_type",
        "gamefile_sha1",
        "gamefile_sha256",
        "seed",
        "evaluator_commit",
        "design_merge_commit",
        "runtime_core_commit",
        "raw_protocol_sha256",
        "split_access_sha256",
        "gamefile_identity_manifest_sha256",
        "environment_runtime_manifest_sha256",
        "policy_runtime_manifest_sha256",
        "policy_request_schema_sha256",
        "scientific_outcome_status",
        "operational_finalization_status",
        "success",
        "termination_reason",
        "final_score",
        "final_done",
        "final_won",
        "final_budget",
        "trace_count",
        "public_transition_count",
        "environment_call_trace_count",
        "initial_observation_sha256",
        "final_observation_sha256",
        "episode_semantic_sha256",
        "started_at_utc",
        "completed_at_utc",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.final_budget, BudgetSnapshotV1):
            raise TypeError(
                "final_budget must be BudgetSnapshotV1"
            )
        condition_values = tuple(
            getattr(self, name)
            for name in self._P1_KEYS
        )

        condition_present = tuple(
            value is not None
            for value in condition_values
        )

        if (
            any(condition_present)
            and not all(condition_present)
        ):
            raise ValueError(
                "condition identity fields must be supplied together"
            )

        select_extras = (
            self.logical_condition_id,
            self.checkpoint_instance_id,
            self.training_seed,
            self.select_policy_runtime_manifest_sha256,
        )

        # ----------------------------------------------------
        # Legacy / P1 DEV
        # ----------------------------------------------------
        if self.evaluation_context is None:
            if any(
                value is not None
                for value in select_extras
            ):
                raise ValueError(
                    "SELECT artifact identity requires "
                    "evaluation_context"
                )

            if all(condition_present):
                if (
                    self.access_class
                    != "DEV_VISIBLE"
                ):
                    raise ValueError(
                        "P1 episode access_class must be DEV_VISIBLE"
                    )

                if (
                    self.policy_condition_id
                    != "P4-R0-PI0"
                ):
                    raise ValueError(
                        "P1 episode policy_condition_id "
                        "must be P4-R0-PI0"
                    )

                if (
                    self.condition_cell_id
                    != self.scheduled_cell_id
                ):
                    raise ValueError(
                        "condition_cell_id must equal "
                        "scheduled_cell_id"
                    )

        # ----------------------------------------------------
        # Formal SELECT
        # ----------------------------------------------------
        elif (
            self.evaluation_context
            == "P4_HARNESS_OFF_SELECT"
        ):
            if not all(condition_present):
                raise ValueError(
                    "SELECT episode requires complete "
                    "condition identity"
                )

            if (
                self.access_class
                != "SELECT_SUMMARY_ONLY"
            ):
                raise ValueError(
                    "SELECT episode access_class mismatch"
                )

            if (
                self.condition_cell_id
                != self.scheduled_cell_id
            ):
                raise ValueError(
                    "SELECT condition_cell_id mismatch"
                )

            for name in (
                "logical_condition_id",
                "checkpoint_instance_id",
                "select_policy_runtime_manifest_sha256",
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
                        f"SELECT episode requires {name}"
                    )

            if (
                self.policy_condition_id
                != self.checkpoint_instance_id
            ):
                raise ValueError(
                    "SELECT episode policy/checkpoint mismatch"
                )

            if (
                self.logical_condition_id
                == "P4-R0-PI0"
            ):
                if self.training_seed is not None:
                    raise ValueError(
                        "SELECT pi0 episode forbids training_seed"
                    )

            else:
                if (
                    type(self.training_seed)
                    is not int
                    or self.training_seed < 0
                ):
                    raise ValueError(
                        "SELECT trained episode requires "
                        "non-negative training_seed"
                    )

        else:
            raise ValueError(
                "unknown evaluation_context"
            )

        self._validate()

    def to_dict(self) -> dict[str, object]:
        result = {
            name: getattr(self, name)
            for name in self._KEYS
            if name != "final_budget"
        }
        result["final_budget"] = self.final_budget.to_dict()
        if self.condition_cell_id is not None:
            for name in self._P1_KEYS:
                result[name] = getattr(self, name)
        if self.evaluation_context is not None:
            for name in self._SELECT_KEYS:
                result[name] = getattr(
                    self,
                    name,
                )

        return result

    @classmethod
    def from_dict(cls, value: object) -> "EpisodeArtifactV1":
        payload = _require_mapping(value)
        base_keys = cls._KEYS
        observed = set(payload)

        allowed = (
            base_keys,
            base_keys | cls._P1_KEYS,
            (
                base_keys
                | cls._P1_KEYS
                | cls._SELECT_KEYS
            ),
        )

        if observed not in allowed:
            missing = sorted(
                base_keys - observed
            )

            unknown = sorted(
                observed
                - (
                    base_keys
                    | cls._P1_KEYS
                    | cls._SELECT_KEYS
                )
            )

            raise ValueError(
                "episode artifact fields mismatch: "
                f"missing={missing}, unknown={unknown}"
            )

        values = dict(payload)
        values["final_budget"] = BudgetSnapshotV1.from_dict(payload["final_budget"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class RunScheduleV1(_SchemaModel):
    SCHEMA_ID: ClassVar[str] = "E1_RUN_SCHEDULE_V1"

    schema_id: str
    schema_version: int
    schedule_id: str
    task_manifest_sha256: str
    replicate_seeds: tuple[int, ...]
    order: str
    cell_count: int
    primary_statistical_unit: str
    replicates_are_not_independent_tasks: bool
    pooled_670_iid_headline_result: str
    cells: tuple[RunScheduleCellV1, ...]

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "schedule_id",
        "task_manifest_sha256",
        "replicate_seeds",
        "order",
        "cell_count",
        "primary_statistical_unit",
        "replicates_are_not_independent_tasks",
        "pooled_670_iid_headline_result",
        "cells",
    }

    def __post_init__(self) -> None:
        if any(
            not isinstance(cell, RunScheduleCellV1)
            for cell in self.cells
        ):
            raise TypeError(
                "cells must contain RunScheduleCellV1"
            )
        self._validate()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "schedule_id": self.schedule_id,
            "task_manifest_sha256": self.task_manifest_sha256,
            "replicate_seeds": list(self.replicate_seeds),
            "order": self.order,
            "cell_count": self.cell_count,
            "primary_statistical_unit": (
                self.primary_statistical_unit
            ),
            "replicates_are_not_independent_tasks": (
                self.replicates_are_not_independent_tasks
            ),
            "pooled_670_iid_headline_result": (
                self.pooled_670_iid_headline_result
            ),
            "cells": [
                cell.to_dict()
                for cell in self.cells
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> "RunScheduleV1":
        payload = _require_mapping(value)
        _expect_keys(payload, cls._KEYS)
        raw_cells = payload["cells"]
        if not isinstance(raw_cells, list):
            raise TypeError("cells must be a JSON array")
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            schedule_id=payload["schedule_id"],
            task_manifest_sha256=payload["task_manifest_sha256"],
            replicate_seeds=_tuple_of_ints(
                payload["replicate_seeds"],
                "replicate_seeds",
            ),
            order=payload["order"],
            cell_count=payload["cell_count"],
            primary_statistical_unit=(
                payload["primary_statistical_unit"]
            ),
            replicates_are_not_independent_tasks=(
                payload["replicates_are_not_independent_tasks"]
            ),
            pooled_670_iid_headline_result=(
                payload["pooled_670_iid_headline_result"]
            ),
            cells=tuple(
                RunScheduleCellV1.from_dict(item)
                for item in raw_cells
            ),
        )
