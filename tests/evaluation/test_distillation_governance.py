from dataclasses import replace

import pytest

from pchsi.evaluation.condition_run_schedule import (
    ConditionRunPurpose,
    build_condition_run_schedule,
)
from pchsi.evaluation.distillation_access import (
    DistillationAccessClass,
    HistoricalAccessAuditRecordV1,
    HistoricalAccessAuditV1,
    HistoricalAccessFlag,
    TaskAccessManifestV1,
    TaskAccessRecordV1,
)
from pchsi.evaluation.distillation_governance import (
    DistillationGovernanceBundleV1,
    canonical_model_sha256,
    validate_distillation_governance_bundle,
)
from pchsi.evaluation.policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
    TrainingMethod,
)


def parts():
    audit_record = HistoricalAccessAuditRecordV1(
        task_id="task-0",
        gamefile="/dataset/task-0/game.tw-pddl",
        dataset_split="valid_unseen",
        first_known_access_date=None,
        access_flags=(
            HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
            HistoricalAccessFlag.USED_FOR_METHOD_DESIGN,
        ),
        evidence_sources=("project-ledger",),
    )
    audit = HistoricalAccessAuditV1(
        schema_id=HistoricalAccessAuditV1.SCHEMA_ID,
        schema_version=1,
        audit_id="audit",
        dataset_version="json_2.1.1",
        record_count=1,
        records=(audit_record,),
    )
    access_record = TaskAccessRecordV1(
        manifest_index=0,
        task_id=audit_record.task_id,
        dataset_split=audit_record.dataset_split,
        task_type="pick_and_place_simple",
        gamefile=audit_record.gamefile,
        gamefile_sha1="a" * 40,
        gamefile_sha256="b" * 64,
        historical_access_flags=audit_record.access_flags,
        access_class=DistillationAccessClass.DEV_VISIBLE,
        teacher_call_permitted=True,
        training_permitted=True,
        select_evaluation_permitted=False,
        confirmatory_permitted=False,
        provenance_sources=("audit",),
    )
    access = TaskAccessManifestV1(
        schema_id=TaskAccessManifestV1.SCHEMA_ID,
        schema_version=1,
        manifest_id="manifest",
        dataset_version="json_2.1.1",
        historical_access_audit_sha256=(
            canonical_model_sha256(audit)
        ),
        record_count=1,
        records=(access_record,),
    )
    policy = PolicyConditionManifestV1(
        schema_id=PolicyConditionManifestV1.SCHEMA_ID,
        schema_version=1,
        policy_condition_id="P4-R0-PI0",
        base_model_repository="Qwen/Qwen2.5-3B-Instruct",
        base_model_revision="c" * 40,
        checkpoint_kind=CheckpointKind.BASE_MODEL,
        checkpoint_path=None,
        checkpoint_sha256=None,
        training_method=TrainingMethod.NONE,
        training_run_id=None,
        training_config_sha256=None,
        policy_runtime_manifest_sha256="d" * 64,
        tokenizer_identity_manifest_sha256="e" * 64,
        chat_template_sha256="f" * 64,
        served_model_name="Qwen2.5-3B-Instruct-E1",
        policy_version="pi0",
        memory_version="MEMORY_M0_V1",
        raw_protocol_sha256="1" * 64,
        runtime_core_commit="2" * 40,
        evaluator_commit="3" * 40,
    )
    schedule = build_condition_run_schedule(
        task_access_manifest=access,
        task_access_manifest_sha256=canonical_model_sha256(access),
        policy_condition=policy,
        policy_condition_manifest_sha256=canonical_model_sha256(
            policy
        ),
        run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,
        target_access_class=DistillationAccessClass.DEV_VISIBLE,
        replicate_seeds=(17,),
        output_namespace="p1-dev",
    )
    return audit, access, policy, schedule


def bundle():
    audit, access, policy, schedule = parts()
    return DistillationGovernanceBundleV1(
        historical_access_audit=audit,
        task_access_manifest=access,
        policy_condition=policy,
        schedule=schedule,
    )


def test_canonical_hash_is_stable():
    audit, access, _, _ = parts()
    assert canonical_model_sha256(audit) == (
        canonical_model_sha256(audit)
    )
    assert len(canonical_model_sha256(access)) == 64


def test_valid_bundle_passes():
    validate_distillation_governance_bundle(bundle())


def test_access_manifest_must_bind_audit_hash():
    value = bundle()
    bad_access = replace(
        value.task_access_manifest,
        historical_access_audit_sha256="0" * 64,
    )
    with pytest.raises(
        ValueError,
        match="historical_access_audit_sha256",
    ):
        validate_distillation_governance_bundle(
            replace(value, task_access_manifest=bad_access)
        )


def test_access_flags_must_match_audit():
    value = bundle()
    bad_record = replace(
        value.task_access_manifest.records[0],
        historical_access_flags=(
            HistoricalAccessFlag.AGGREGATE_ONLY,
        ),
    )
    bad_access = replace(
        value.task_access_manifest,
        records=(bad_record,),
    )
    with pytest.raises(
        ValueError,
        match="historical access flags",
    ):
        validate_distillation_governance_bundle(
            replace(value, task_access_manifest=bad_access)
        )


def test_schedule_must_bind_policy_hash():
    value = bundle()
    bad_schedule = replace(
        value.schedule,
        policy_condition_manifest_sha256="0" * 64,
    )
    with pytest.raises(
        ValueError,
        match="policy_condition_manifest_sha256",
    ):
        validate_distillation_governance_bundle(
            replace(value, schedule=bad_schedule)
        )



def test_governance_rejects_forged_condition_cell_id() -> None:
    value = bundle()
    original_cell = value.schedule.cells[0]
    forged_cell = replace(
        original_cell,
        condition_cell_id="p4-P4-R0-PI0-t00000-s0000000018",
    )
    forged_schedule = replace(
        value.schedule,
        cells=(forged_cell,),
    )

    with pytest.raises(ValueError, match="condition_cell_id"):
        validate_distillation_governance_bundle(
            replace(value, schedule=forged_schedule)
        )
