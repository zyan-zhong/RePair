"""Frozen 134-task × 5-seed E1 run schedule."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .canonical_evidence import (
    require_lower_sha256,
    require_nonnegative_int,
)
from .schema_models import (
    RunScheduleCellV1,
    RunScheduleV1,
)
from .task_manifest import FrozenTaskRecord


REPLICATE_SEEDS: tuple[int, ...] = (
    17,
    31,
    47,
    73,
    101,
)


@dataclass(frozen=True, slots=True)
class ScheduledCell:
    scheduled_cell_id: str
    task_index: int
    task_id: str
    seed: int

    def __post_init__(self) -> None:
        require_nonnegative_int(
            "task_index",
            self.task_index,
        )
        require_nonnegative_int(
            "seed",
            self.seed,
        )
        if not isinstance(self.task_id, str) or not self.task_id:
            raise ValueError("task_id must be non-empty")
        expected = scheduled_cell_id(
            task_index=self.task_index,
            seed=self.seed,
        )
        if self.scheduled_cell_id != expected:
            raise ValueError(
                "scheduled_cell_id does not match task/seed"
            )


def scheduled_cell_id(
    *,
    task_index: int,
    seed: int,
) -> str:
    task = require_nonnegative_int(
        "task_index",
        task_index,
    )
    replicate_seed = require_nonnegative_int(
        "seed",
        seed,
    )
    if task > 9999:
        raise ValueError(
            "task_index cannot exceed four decimal digits"
        )
    if replicate_seed > 9_999_999_999:
        raise ValueError(
            "seed cannot exceed ten decimal digits"
        )
    return (
        f"e1-t{task:04d}-"
        f"s{replicate_seed:010d}"
    )


def execution_attempt_id(
    *,
    scheduled_cell_id: str,
    attempt_ordinal: int,
) -> str:
    if (
        not isinstance(scheduled_cell_id, str)
        or not scheduled_cell_id
    ):
        raise ValueError(
            "scheduled_cell_id must be non-empty"
        )
    ordinal = require_nonnegative_int(
        "attempt_ordinal",
        attempt_ordinal,
    )
    if ordinal > 999:
        raise ValueError(
            "attempt_ordinal cannot exceed three decimal digits"
        )
    return f"{scheduled_cell_id}-a{ordinal:03d}"


def _freeze_records(
    records: Sequence[FrozenTaskRecord],
) -> tuple[FrozenTaskRecord, ...]:
    if isinstance(
        records,
        (str, bytes, bytearray),
    ):
        raise TypeError(
            "records must be a sequence of FrozenTaskRecord"
        )
    frozen = tuple(records)
    if len(frozen) != 134:
        raise ValueError(
            "E1 schedule requires exactly 134 task records"
        )
    if any(
        not isinstance(record, FrozenTaskRecord)
        for record in frozen
    ):
        raise TypeError(
            "records must contain FrozenTaskRecord"
        )

    for index, record in enumerate(frozen):
        if record.index != index:
            raise ValueError(
                "task records must preserve contiguous index order"
            )
        expected_id = (
            "alfworld_valid_unseen_all134_"
            f"{index:04d}"
        )
        if record.task_id != expected_id:
            raise ValueError(
                "task record ID does not match frozen index"
            )
        if record.split != "valid_unseen":
            raise ValueError(
                "all E1 scheduled tasks must use valid_unseen"
            )
    return frozen


def build_e1_run_schedule(
    *,
    records: Sequence[FrozenTaskRecord],
    task_manifest_sha256: str,
) -> RunScheduleV1:
    frozen_records = _freeze_records(records)
    manifest_sha256 = require_lower_sha256(
        "task_manifest_sha256",
        task_manifest_sha256,
    )

    cells = tuple(
        RunScheduleCellV1(
            scheduled_cell_id=scheduled_cell_id(
                task_index=record.index,
                seed=seed,
            ),
            task_index=record.index,
            task_id=record.task_id,
            seed=seed,
        )
        for seed in REPLICATE_SEEDS
        for record in frozen_records
    )

    return RunScheduleV1(
        schema_id="E1_RUN_SCHEDULE_V1",
        schema_version=1,
        schedule_id="E1_RUN_SCHEDULE_V1",
        task_manifest_sha256=manifest_sha256,
        replicate_seeds=REPLICATE_SEEDS,
        order="seed-major",
        cell_count=670,
        primary_statistical_unit="unique_task",
        replicates_are_not_independent_tasks=True,
        pooled_670_iid_headline_result="forbidden",
        cells=cells,
    )
