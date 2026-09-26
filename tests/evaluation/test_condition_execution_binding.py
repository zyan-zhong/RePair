import pytest

from pchsi.evaluation.condition_execution_binding import (
    ConditionBoundEpisodeCellV1,
    bind_condition_cell,
)
from pchsi.evaluation.condition_run_schedule import (
    ConditionRunScheduleCellV1,
)
from pchsi.evaluation.distillation_access import (
    DistillationAccessClass,
    HistoricalAccessFlag,
    TaskAccessRecordV1,
)
from pchsi.evaluation.policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
    TrainingMethod,
)
from pchsi.evaluation.run_schedule import execution_attempt_id


def _valid_policy_condition() -> PolicyConditionManifestV1:
    return PolicyConditionManifestV1(
        "POLICY_CONDITION_MANIFEST_V1",
        1,
        "P4-R0-PI0",
        "Qwen/Qwen2.5-3B-Instruct",
        "a" * 40,
        CheckpointKind.BASE_MODEL,
        None,
        None,
        TrainingMethod.NONE,
        None,
        None,
        "b" * 64,
        "c" * 64,
        "d" * 64,
        "Qwen2.5-3B-Instruct-E1",
        "pi0",
        "MEMORY_M0_V1",
        "e" * 64,
        "f" * 40,
        "1" * 40,
    )


def _valid_task_access() -> TaskAccessRecordV1:
    return TaskAccessRecordV1(
        7,
        "t7",
        "valid_unseen",
        "family",
        "/d/t7/game.tw-pddl",
        "a" * 40,
        "b" * 64,
        (HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,),
        DistillationAccessClass.DEV_VISIBLE,
        True,
        True,
        False,
        False,
        ("evidence:7",),
    )


def test_condition_cell_id_is_preserved():
    schedule_cell = ConditionRunScheduleCellV1(
        "p4-P4-R0-PI0-t00007-s0000000017",
        7,
        "t7",
        17,
    )
    cell = bind_condition_cell(
        schedule_cell=schedule_cell,
        task_access=_valid_task_access(),
        policy_condition=_valid_policy_condition(),
    )
    assert cell.scheduled_cell_id == schedule_cell.condition_cell_id
    assert execution_attempt_id(
        scheduled_cell_id=cell.scheduled_cell_id,
        attempt_ordinal=0,
    ).startswith(cell.scheduled_cell_id)


def test_condition_bound_cell_rejects_select_access():
    with pytest.raises(ValueError, match="DEV_VISIBLE"):
        ConditionBoundEpisodeCellV1(
            scheduled_cell_id=(
                "p4-P4-R0-PI0-t00000-s0000000017"
            ),
            task_index=0,
            task_id="task-0",
            seed=17,
            policy_condition_id="P4-R0-PI0",
            access_class=(
                DistillationAccessClass.SELECT_SUMMARY_ONLY
            ),
        )


def test_condition_bound_cell_rejects_noncanonical_id():
    with pytest.raises(ValueError, match="canonical"):
        ConditionBoundEpisodeCellV1(
            scheduled_cell_id="forged-cell",
            task_index=0,
            task_id="task-0",
            seed=17,
            policy_condition_id="P4-R0-PI0",
            access_class=DistillationAccessClass.DEV_VISIBLE,
        )
