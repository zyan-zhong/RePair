from __future__ import annotations

from pchsi.evaluation.run_schedule import (
    REPLICATE_SEEDS,
    build_e1_run_schedule,
    execution_attempt_id,
    scheduled_cell_id,
)
from pchsi.evaluation.task_manifest import FrozenTaskRecord


DIGEST = "a" * 64


def _records() -> tuple[FrozenTaskRecord, ...]:
    return tuple(
        FrozenTaskRecord(
            index=index,
            task_id=(
                "alfworld_valid_unseen_all134_"
                f"{index:04d}"
            ),
            split="valid_unseen",
            task_type="pick_and_place_simple",
            gamefile=f"/dataset/task-{index:04d}/game.tw-pddl",
            gamefile_sha1="b" * 40,
            root=f"/dataset/task-{index:04d}",
            traj_file=f"/dataset/task-{index:04d}/traj_data.json",
        )
        for index in range(134)
    )


def test_schedule_contains_exact_seed_major_670_cells() -> None:
    schedule = build_e1_run_schedule(
        records=_records(),
        task_manifest_sha256=DIGEST,
    )

    assert schedule.schema_id == "E1_RUN_SCHEDULE_V1"
    assert schedule.schedule_id == "E1_RUN_SCHEDULE_V1"
    assert schedule.replicate_seeds == REPLICATE_SEEDS
    assert schedule.order == "seed-major"
    assert schedule.cell_count == 670
    assert len(schedule.cells) == 670

    expected_pairs = [
        (task_index, seed)
        for seed in REPLICATE_SEEDS
        for task_index in range(134)
    ]
    observed_pairs = [
        (cell.task_index, cell.seed)
        for cell in schedule.cells
    ]
    assert observed_pairs == expected_pairs


def test_schedule_ids_are_stable_and_unique() -> None:
    schedule = build_e1_run_schedule(
        records=_records(),
        task_manifest_sha256=DIGEST,
    )

    assert scheduled_cell_id(
        task_index=0,
        seed=17,
    ) == "e1-t0000-s0000000017"
    assert scheduled_cell_id(
        task_index=133,
        seed=101,
    ) == "e1-t0133-s0000000101"

    assert execution_attempt_id(
        scheduled_cell_id="e1-t0000-s0000000017",
        attempt_ordinal=0,
    ) == "e1-t0000-s0000000017-a000"
    assert execution_attempt_id(
        scheduled_cell_id="e1-t0133-s0000000101",
        attempt_ordinal=7,
    ) == "e1-t0133-s0000000101-a007"

    ids = [cell.scheduled_cell_id for cell in schedule.cells]
    assert len(ids) == len(set(ids))


def test_schedule_primary_statistical_unit_is_unique_task() -> None:
    schedule = build_e1_run_schedule(
        records=_records(),
        task_manifest_sha256=DIGEST,
    )

    assert schedule.primary_statistical_unit == "unique_task"
    assert schedule.replicates_are_not_independent_tasks is True
    assert schedule.pooled_670_iid_headline_result == "forbidden"
