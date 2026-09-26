"""Bind reviewed P1 DEV schedule cells into episode execution."""

from __future__ import annotations

from dataclasses import dataclass

from .condition_run_schedule import (
    ConditionRunScheduleCellV1,
    condition_cell_id as build_condition_cell_id,
)
from .distillation_access import (
    DistillationAccessClass,
    TaskAccessRecordV1,
)
from .policy_condition import PolicyConditionManifestV1


@dataclass(frozen=True, slots=True)
class ConditionBoundEpisodeCellV1:
    scheduled_cell_id: str
    task_index: int
    task_id: str
    seed: int
    policy_condition_id: str
    access_class: DistillationAccessClass

    def __post_init__(self) -> None:
        if not isinstance(
            self.scheduled_cell_id,
            str,
        ) or not self.scheduled_cell_id:
            raise ValueError(
                "scheduled_cell_id must be non-empty"
            )
        if type(self.task_index) is not int:
            raise TypeError("task_index must be int")
        if self.task_index < 0:
            raise ValueError(
                "task_index must be non-negative"
            )
        if not isinstance(
            self.task_id,
            str,
        ) or not self.task_id:
            raise ValueError("task_id must be non-empty")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError(
                "seed must be a non-negative int"
            )
        if self.policy_condition_id != "P4-R0-PI0":
            raise ValueError(
                "P1 DEV cell requires P4-R0-PI0"
            )
        if (
            self.access_class
            is not DistillationAccessClass.DEV_VISIBLE
        ):
            raise ValueError(
                "P1 DEV cell requires DEV_VISIBLE"
            )

        expected = build_condition_cell_id(
            policy_condition_id=self.policy_condition_id,
            manifest_index=self.task_index,
            seed=self.seed,
        )
        if self.scheduled_cell_id != expected:
            raise ValueError(
                "scheduled_cell_id is not canonical"
            )


def bind_condition_cell(
    *,
    schedule_cell: ConditionRunScheduleCellV1,
    task_access: TaskAccessRecordV1,
    policy_condition: PolicyConditionManifestV1,
) -> ConditionBoundEpisodeCellV1:
    if not isinstance(
        schedule_cell,
        ConditionRunScheduleCellV1,
    ):
        raise TypeError(
            "schedule_cell must be ConditionRunScheduleCellV1"
        )
    if not isinstance(
        task_access,
        TaskAccessRecordV1,
    ):
        raise TypeError(
            "task_access must be TaskAccessRecordV1"
        )
    if not isinstance(
        policy_condition,
        PolicyConditionManifestV1,
    ):
        raise TypeError(
            "policy_condition must be PolicyConditionManifestV1"
        )

    if (
        task_access.manifest_index
        != schedule_cell.manifest_index
        or task_access.task_id
        != schedule_cell.task_id
    ):
        raise ValueError(
            "schedule/access identity mismatch"
        )
    if (
        task_access.access_class
        is not DistillationAccessClass.DEV_VISIBLE
    ):
        raise ValueError(
            "P1 DEV binding requires DEV_VISIBLE"
        )
    if (
        policy_condition.policy_condition_id
        != "P4-R0-PI0"
    ):
        raise ValueError(
            "P1 DEV binding requires P4-R0-PI0"
        )

    return ConditionBoundEpisodeCellV1(
        scheduled_cell_id=schedule_cell.condition_cell_id,
        task_index=schedule_cell.manifest_index,
        task_id=schedule_cell.task_id,
        seed=schedule_cell.seed,
        policy_condition_id=(
            policy_condition.policy_condition_id
        ),
        access_class=task_access.access_class,
    )
