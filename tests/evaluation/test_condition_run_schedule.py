import pytest

from pchsi.evaluation.condition_run_schedule import (
    ConditionRunPurpose,
    build_condition_run_schedule,
    condition_cell_id,
)
from pchsi.evaluation.distillation_access import (
    DistillationAccessClass,
    HistoricalAccessFlag,
    TaskAccessManifestV1,
    TaskAccessRecordV1,
)
from pchsi.evaluation.policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
    TrainingMethod,
)


def policy():
    return PolicyConditionManifestV1(
        schema_id=PolicyConditionManifestV1.SCHEMA_ID,
        schema_version=1,
        policy_condition_id="P4-R0-PI0",
        base_model_repository="Qwen/Qwen2.5-3B-Instruct",
        base_model_revision="a" * 40,
        checkpoint_kind=CheckpointKind.BASE_MODEL,
        checkpoint_path=None,
        checkpoint_sha256=None,
        training_method=TrainingMethod.NONE,
        training_run_id=None,
        training_config_sha256=None,
        policy_runtime_manifest_sha256="b" * 64,
        tokenizer_identity_manifest_sha256="c" * 64,
        chat_template_sha256="d" * 64,
        served_model_name="Qwen2.5-3B-Instruct-E1",
        policy_version="pi0",
        memory_version="MEMORY_M0_V1",
        raw_protocol_sha256="e" * 64,
        runtime_core_commit="f" * 40,
        evaluator_commit="1" * 40,
    )


def record(index, access_class):
    permissions = {
        DistillationAccessClass.DEV_VISIBLE: (
            True, True, False, False
        ),
        DistillationAccessClass.SELECT_SUMMARY_ONLY: (
            False, False, True, False
        ),
    }[access_class]
    return TaskAccessRecordV1(
        manifest_index=index,
        task_id=f"task-{index}",
        dataset_split="train",
        task_type="pick_and_place_simple",
        gamefile=f"/dataset/task-{index}/game.tw-pddl",
        gamefile_sha1=f"{index + 1:040x}",
        gamefile_sha256=f"{index + 1:064x}",
        historical_access_flags=(
            HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
        ),
        access_class=access_class,
        teacher_call_permitted=permissions[0],
        training_permitted=permissions[1],
        select_evaluation_permitted=permissions[2],
        confirmatory_permitted=permissions[3],
        provenance_sources=(f"audit:{index}",),
    )


def manifest():
    records = (
        record(0, DistillationAccessClass.DEV_VISIBLE),
        record(1, DistillationAccessClass.SELECT_SUMMARY_ONLY),
        record(2, DistillationAccessClass.DEV_VISIBLE),
    )
    return TaskAccessManifestV1(
        schema_id=TaskAccessManifestV1.SCHEMA_ID,
        schema_version=1,
        manifest_id="manifest",
        dataset_version="json_2.1.1",
        historical_access_audit_sha256="9" * 64,
        record_count=len(records),
        records=records,
    )


def test_cell_id_is_condition_bound():
    assert condition_cell_id(
        policy_condition_id="P4-R0-PI0",
        manifest_index=7,
        seed=17,
    ) == "p4-P4-R0-PI0-t00007-s0000000017"


def test_schedule_is_not_hard_coded_to_134():
    schedule = build_condition_run_schedule(
        task_access_manifest=manifest(),
        task_access_manifest_sha256="a" * 64,
        policy_condition=policy(),
        policy_condition_manifest_sha256="b" * 64,
        run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,
        target_access_class=DistillationAccessClass.DEV_VISIBLE,
        replicate_seeds=(17, 31),
        output_namespace="p1-pi0-dev-v1",
    )
    assert schedule.cell_count == 4
    assert [cell.manifest_index for cell in schedule.cells] == [
        0, 2, 0, 2
    ]
    assert [cell.seed for cell in schedule.cells] == [
        17, 17, 31, 31
    ]


def test_p1_rejects_non_dev_target():
    with pytest.raises(ValueError, match="P1_PI0_DEV_ROLLOUT"):
        build_condition_run_schedule(
            task_access_manifest=manifest(),
            task_access_manifest_sha256="a" * 64,
            policy_condition=policy(),
            policy_condition_manifest_sha256="b" * 64,
            run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,
            target_access_class=(
                DistillationAccessClass.SELECT_SUMMARY_ONLY
            ),
            replicate_seeds=(17,),
            output_namespace="invalid",
        )


@pytest.mark.parametrize("seeds", [(), (17, 17), (-1,)])
def test_invalid_seed_schedules_are_rejected(seeds):
    with pytest.raises((TypeError, ValueError)):
        build_condition_run_schedule(
            task_access_manifest=manifest(),
            task_access_manifest_sha256="a" * 64,
            policy_condition=policy(),
            policy_condition_manifest_sha256="b" * 64,
            run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,
            target_access_class=DistillationAccessClass.DEV_VISIBLE,
            replicate_seeds=seeds,
            output_namespace="p1-dev",
        )


def test_schedule_round_trip():
    schedule = build_condition_run_schedule(
        task_access_manifest=manifest(),
        task_access_manifest_sha256="a" * 64,
        policy_condition=policy(),
        policy_condition_manifest_sha256="b" * 64,
        run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,
        target_access_class=DistillationAccessClass.DEV_VISIBLE,
        replicate_seeds=(17,),
        output_namespace="p1-dev",
    )
    assert type(schedule).from_json(schedule.to_json()) == schedule
