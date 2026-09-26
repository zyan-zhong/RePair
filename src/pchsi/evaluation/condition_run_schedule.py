"""Condition-bound deterministic run schedule contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
import re
from typing import ClassVar, Self

from .canonical_evidence import (
    canonical_json_text,
    require_lower_sha256,
    strict_json_loads,
)
from .distillation_access import (
    DistillationAccessClass,
    TaskAccessManifestV1,
)
from .policy_condition import PolicyConditionManifestV1
from .schema_contract import validate_payload_against_schema


_CONDITION_ID = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
)
_OUTPUT_NAMESPACE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
)


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("wire value must be a JSON object")
    return value


def _expect_keys(payload: dict[str, object], expected: set[str]) -> None:
    missing = sorted(expected - set(payload))
    unknown = sorted(set(payload) - expected)
    if missing:
        raise ValueError(f"wire object is missing required fields: {missing}")
    if unknown:
        raise ValueError(f"wire object contains unknown fields: {unknown}")


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains a forbidden character")
    return value


class ConditionRunPurpose(str, Enum):
    P1_PI0_DEV_ROLLOUT = "P1_PI0_DEV_ROLLOUT"
    P4_HARNESS_OFF_SELECT = "P4_HARNESS_OFF_SELECT"


def condition_cell_id(
    *,
    policy_condition_id: str,
    manifest_index: int,
    seed: int,
) -> str:
    if (
        not isinstance(policy_condition_id, str)
        or _CONDITION_ID.fullmatch(policy_condition_id) is None
    ):
        raise ValueError("policy_condition_id has invalid syntax")
    if type(manifest_index) is not int:
        raise TypeError("manifest_index must be int")
    if not 0 <= manifest_index <= 99999:
        raise ValueError("manifest_index is out of range")
    if type(seed) is not int:
        raise TypeError("seed must be int")
    if not 0 <= seed <= 9999999999:
        raise ValueError("seed is out of range")
    return (
        f"p4-{policy_condition_id}"
        f"-t{manifest_index:05d}"
        f"-s{seed:010d}"
    )


@dataclass(frozen=True, slots=True)
class ConditionRunScheduleCellV1:
    condition_cell_id: str
    manifest_index: int
    task_id: str
    seed: int

    _KEYS: ClassVar[set[str]] = {
        "condition_cell_id",
        "manifest_index",
        "task_id",
        "seed",
    }

    def __post_init__(self) -> None:
        _text("condition_cell_id", self.condition_cell_id)
        _text("task_id", self.task_id)
        if type(self.manifest_index) is not int:
            raise TypeError("manifest_index must be int")
        if not 0 <= self.manifest_index <= 99999:
            raise ValueError("manifest_index is out of range")
        if type(self.seed) is not int:
            raise TypeError("seed must be int")
        if not 0 <= self.seed <= 9999999999:
            raise ValueError("seed is out of range")

    def to_dict(self) -> dict[str, object]:
        return {
            "condition_cell_id": self.condition_cell_id,
            "manifest_index": self.manifest_index,
            "task_id": self.task_id,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "ConditionRunScheduleCellV1":
        payload = _mapping(value)
        _expect_keys(payload, cls._KEYS)
        return cls(
            condition_cell_id=payload["condition_cell_id"],
            manifest_index=payload["manifest_index"],
            task_id=payload["task_id"],
            seed=payload["seed"],
        )


@dataclass(frozen=True, slots=True)
class ConditionRunScheduleV1:
    SCHEMA_ID: ClassVar[str] = "CONDITION_RUN_SCHEDULE_V1"
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    schedule_id: str
    task_access_manifest_sha256: str
    policy_condition_manifest_sha256: str
    run_purpose: ConditionRunPurpose
    target_access_class: DistillationAccessClass
    replicate_seeds: tuple[int, ...]
    order: str
    cell_count: int
    output_namespace: str
    primary_statistical_unit: str
    cells: tuple[ConditionRunScheduleCellV1, ...]

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "schedule_id",
        "task_access_manifest_sha256",
        "policy_condition_manifest_sha256",
        "run_purpose",
        "target_access_class",
        "replicate_seeds",
        "order",
        "cell_count",
        "output_namespace",
        "primary_statistical_unit",
        "cells",
    }

    def __post_init__(self) -> None:
        if self.schema_id != self.SCHEMA_ID:
            raise ValueError("schema_id mismatch")
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("schema_version mismatch")
        _text("schedule_id", self.schedule_id)
        require_lower_sha256(
            "task_access_manifest_sha256",
            self.task_access_manifest_sha256,
        )
        require_lower_sha256(
            "policy_condition_manifest_sha256",
            self.policy_condition_manifest_sha256,
        )
        if type(self.run_purpose) is not ConditionRunPurpose:
            raise TypeError("run_purpose must be ConditionRunPurpose")
        if type(self.target_access_class) is not DistillationAccessClass:
            raise TypeError(
                "target_access_class must be DistillationAccessClass"
            )
        if type(self.replicate_seeds) is not tuple:
            raise TypeError("replicate_seeds must be tuple")
        if not self.replicate_seeds:
            raise ValueError("replicate_seeds must not be empty")
        if any(type(seed) is not int for seed in self.replicate_seeds):
            raise TypeError("replicate_seeds items must be int")
        if any(
            seed < 0 or seed > 9999999999
            for seed in self.replicate_seeds
        ):
            raise ValueError("replicate seed is out of range")
        if len(set(self.replicate_seeds)) != len(
            self.replicate_seeds
        ):
            raise ValueError("replicate_seeds contains duplicates")
        if self.order != "seed-major":
            raise ValueError("order must be seed-major")
        if type(self.cell_count) is not int:
            raise TypeError("cell_count must be int")
        if (
            not isinstance(self.output_namespace, str)
            or _OUTPUT_NAMESPACE.fullmatch(
                self.output_namespace
            ) is None
            or ".." in self.output_namespace
        ):
            raise ValueError("output_namespace has invalid syntax")
        if self.primary_statistical_unit != "unique_task":
            raise ValueError(
                "primary_statistical_unit must be unique_task"
            )
        if type(self.cells) is not tuple:
            raise TypeError("cells must be tuple")
        if not self.cells:
            raise ValueError("cells must not be empty")
        if any(
            type(cell) is not ConditionRunScheduleCellV1
            for cell in self.cells
        ):
            raise TypeError(
                "cells items must be ConditionRunScheduleCellV1"
            )
        if self.cell_count != len(self.cells):
            raise ValueError("cell_count must equal len(cells)")
        cell_ids = [cell.condition_cell_id for cell in self.cells]
        pairs = [
            (cell.manifest_index, cell.task_id, cell.seed)
            for cell in self.cells
        ]
        if len(set(cell_ids)) != len(cell_ids):
            raise ValueError("condition_cell_id values must be unique")
        if len(set(pairs)) != len(pairs):
            raise ValueError("schedule cells contain duplicates")
        if any(
            cell.seed not in self.replicate_seeds
            for cell in self.cells
        ):
            raise ValueError(
                "schedule cell seed is not in replicate_seeds"
            )
        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "schedule_id": self.schedule_id,
            "task_access_manifest_sha256": (
                self.task_access_manifest_sha256
            ),
            "policy_condition_manifest_sha256": (
                self.policy_condition_manifest_sha256
            ),
            "run_purpose": self.run_purpose.value,
            "target_access_class": self.target_access_class.value,
            "replicate_seeds": list(self.replicate_seeds),
            "order": self.order,
            "cell_count": self.cell_count,
            "output_namespace": self.output_namespace,
            "primary_statistical_unit": (
                self.primary_statistical_unit
            ),
            "cells": [cell.to_dict() for cell in self.cells],
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> Self:
        payload = _mapping(value)
        _expect_keys(payload, cls._KEYS)
        seeds = payload["replicate_seeds"]
        cells = payload["cells"]
        if not isinstance(seeds, list):
            raise TypeError("replicate_seeds must be a JSON array")
        if not isinstance(cells, list):
            raise TypeError("cells must be a JSON array")
        try:
            purpose = ConditionRunPurpose(payload["run_purpose"])
            access_class = DistillationAccessClass(
                payload["target_access_class"]
            )
        except (TypeError, ValueError) as error:
            raise ValueError("unknown schedule enum") from error
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            schedule_id=payload["schedule_id"],
            task_access_manifest_sha256=payload[
                "task_access_manifest_sha256"
            ],
            policy_condition_manifest_sha256=payload[
                "policy_condition_manifest_sha256"
            ],
            run_purpose=purpose,
            target_access_class=access_class,
            replicate_seeds=tuple(seeds),
            order=payload["order"],
            cell_count=payload["cell_count"],
            output_namespace=payload["output_namespace"],
            primary_statistical_unit=payload[
                "primary_statistical_unit"
            ],
            cells=tuple(
                ConditionRunScheduleCellV1.from_dict(item)
                for item in cells
            ),
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> Self:
        return cls.from_dict(strict_json_loads(value))


def build_condition_run_schedule(
    *,
    task_access_manifest: TaskAccessManifestV1,
    task_access_manifest_sha256: str,
    policy_condition: PolicyConditionManifestV1,
    policy_condition_manifest_sha256: str,
    run_purpose: ConditionRunPurpose,
    target_access_class: DistillationAccessClass,
    replicate_seeds: Sequence[int],
    output_namespace: str,
) -> ConditionRunScheduleV1:
    if type(task_access_manifest) is not TaskAccessManifestV1:
        raise TypeError(
            "task_access_manifest must be TaskAccessManifestV1"
        )
    if type(policy_condition) is not PolicyConditionManifestV1:
        raise TypeError(
            "policy_condition must be PolicyConditionManifestV1"
        )
    require_lower_sha256(
        "task_access_manifest_sha256",
        task_access_manifest_sha256,
    )
    require_lower_sha256(
        "policy_condition_manifest_sha256",
        policy_condition_manifest_sha256,
    )
    if type(run_purpose) is not ConditionRunPurpose:
        raise TypeError("run_purpose must be ConditionRunPurpose")
    if type(target_access_class) is not DistillationAccessClass:
        raise TypeError(
            "target_access_class must be DistillationAccessClass"
        )
    if isinstance(replicate_seeds, (str, bytes, bytearray)):
        raise TypeError("replicate_seeds must be an integer sequence")
    seeds = tuple(replicate_seeds)
    if not seeds:
        raise ValueError("replicate_seeds must not be empty")
    if any(type(seed) is not int for seed in seeds):
        raise TypeError("replicate_seeds items must be int")
    if any(seed < 0 or seed > 9999999999 for seed in seeds):
        raise ValueError("replicate seed is out of range")
    if len(set(seeds)) != len(seeds):
        raise ValueError("replicate_seeds contains duplicates")
    if (
        not isinstance(output_namespace, str)
        or _OUTPUT_NAMESPACE.fullmatch(output_namespace) is None
        or ".." in output_namespace
    ):
        raise ValueError("output_namespace has invalid syntax")

    expected_class = {
        ConditionRunPurpose.P1_PI0_DEV_ROLLOUT: (
            DistillationAccessClass.DEV_VISIBLE
        ),
        ConditionRunPurpose.P4_HARNESS_OFF_SELECT: (
            DistillationAccessClass.SELECT_SUMMARY_ONLY
        ),
    }[run_purpose]
    if target_access_class is not expected_class:
        raise ValueError(
            f"{run_purpose.value} requires {expected_class.value}"
        )
    if (
        run_purpose
        is ConditionRunPurpose.P1_PI0_DEV_ROLLOUT
        and policy_condition.policy_condition_id != "P4-R0-PI0"
    ):
        raise ValueError(
            "P1_PI0_DEV_ROLLOUT requires P4-R0-PI0"
        )
    selected = tuple(
        record
        for record in task_access_manifest.records
        if record.access_class is target_access_class
    )
    if not selected:
        raise ValueError("target access class selects zero tasks")

    cells = tuple(
        ConditionRunScheduleCellV1(
            condition_cell_id=condition_cell_id(
                policy_condition_id=(
                    policy_condition.policy_condition_id
                ),
                manifest_index=record.manifest_index,
                seed=seed,
            ),
            manifest_index=record.manifest_index,
            task_id=record.task_id,
            seed=seed,
        )
        for seed in seeds
        for record in selected
    )
    return ConditionRunScheduleV1(
        schema_id=ConditionRunScheduleV1.SCHEMA_ID,
        schema_version=ConditionRunScheduleV1.SCHEMA_VERSION,
        schedule_id=(
            f"{run_purpose.value}__"
            f"{policy_condition.policy_condition_id}__"
            f"{output_namespace}"
        ),
        task_access_manifest_sha256=(
            task_access_manifest_sha256
        ),
        policy_condition_manifest_sha256=(
            policy_condition_manifest_sha256
        ),
        run_purpose=run_purpose,
        target_access_class=target_access_class,
        replicate_seeds=seeds,
        order="seed-major",
        cell_count=len(cells),
        output_namespace=output_namespace,
        primary_statistical_unit="unique_task",
        cells=cells,
    )
