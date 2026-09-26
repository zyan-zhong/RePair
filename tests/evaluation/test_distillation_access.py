from dataclasses import FrozenInstanceError
import json

import pytest

from pchsi.evaluation.distillation_access import (
    DistillationAccessClass,
    HistoricalAccessAuditRecordV1,
    HistoricalAccessAuditV1,
    HistoricalAccessFlag,
    TaskAccessManifestV1,
    TaskAccessRecordV1,
)
from pchsi.evaluation.schema_contract import load_schema


def audit_record(
    *,
    task_id="task-0",
    gamefile="/dataset/train/task-0/game.tw-pddl",
    flags=(HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,),
):
    return HistoricalAccessAuditRecordV1(
        task_id=task_id,
        gamefile=gamefile,
        dataset_split="train",
        first_known_access_date=None,
        access_flags=flags,
        evidence_sources=("reviewed-ledger:row-0",),
    )


def access_record(
    *,
    index=0,
    task_id="task-0",
    gamefile="/dataset/train/task-0/game.tw-pddl",
    flags=(HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,),
    access_class=DistillationAccessClass.DEV_VISIBLE,
    permissions=(True, True, False, False),
):
    return TaskAccessRecordV1(
        manifest_index=index,
        task_id=task_id,
        dataset_split="train",
        task_type="pick_and_place_simple",
        gamefile=gamefile,
        gamefile_sha1="a" * 40,
        gamefile_sha256="b" * 64,
        historical_access_flags=flags,
        access_class=access_class,
        teacher_call_permitted=permissions[0],
        training_permitted=permissions[1],
        select_evaluation_permitted=permissions[2],
        confirmatory_permitted=permissions[3],
        provenance_sources=("audit:row-0",),
    )


def test_schemas_are_registered():
    assert load_schema(
        "DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1"
    )["$id"] == "DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1"
    assert load_schema(
        "DISTILLATION_TASK_ACCESS_MANIFEST_V1"
    )["$id"] == "DISTILLATION_TASK_ACCESS_MANIFEST_V1"


def test_audit_round_trip_is_canonical():
    audit = HistoricalAccessAuditV1(
        schema_id=HistoricalAccessAuditV1.SCHEMA_ID,
        schema_version=1,
        audit_id="P1_A_AUDIT_V1",
        dataset_version="json_2.1.1",
        record_count=1,
        records=(audit_record(),),
    )
    assert HistoricalAccessAuditV1.from_json(audit.to_json()) == audit
    assert json.loads(audit.to_json())["record_count"] == 1


def test_records_are_frozen():
    record = audit_record()
    with pytest.raises(FrozenInstanceError):
        record.task_id = "mutated"  # type: ignore[misc]


@pytest.mark.parametrize(
    "flags",
    [
        (
            HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,
            HistoricalAccessFlag.AGGREGATE_ONLY,
        ),
        (
            HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS,
            HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
        ),
    ],
)
def test_no_known_prior_access_is_exclusive(flags):
    with pytest.raises(ValueError, match="NO_KNOWN_PRIOR_ACCESS"):
        audit_record(flags=flags)


def test_incomplete_history_can_coexist_with_observed_flag():
    record = audit_record(
        flags=(
            HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
            HistoricalAccessFlag.EXECUTED_NOT_INSPECTED,
        )
    )
    assert HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE in (
        record.access_flags
    )


def test_dev_visible_requires_exact_permissions():
    with pytest.raises(ValueError, match="DEV_VISIBLE"):
        access_record(permissions=(False, True, False, False))


def test_select_forbids_teacher_and_training():
    with pytest.raises(ValueError, match="SELECT_SUMMARY_ONLY"):
        access_record(
            access_class=DistillationAccessClass.SELECT_SUMMARY_ONLY,
            permissions=(True, False, True, False),
        )


@pytest.mark.parametrize(
    "flag",
    [
        HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
        HistoricalAccessFlag.TRAJECTORY_INSPECTED,
        HistoricalAccessFlag.USED_FOR_METHOD_DESIGN,
        HistoricalAccessFlag.SENT_TO_EXTERNAL_MODEL,
    ],
)
def test_confirmatory_rejects_disqualifying_history(flag):
    with pytest.raises(ValueError, match="CONFIRMATORY_SEALED"):
        access_record(
            flags=(flag,),
            access_class=DistillationAccessClass.CONFIRMATORY_SEALED,
            permissions=(False, False, False, True),
        )


def test_manifest_indices_are_contiguous():
    with pytest.raises(ValueError, match="contiguous"):
        TaskAccessManifestV1(
            schema_id=TaskAccessManifestV1.SCHEMA_ID,
            schema_version=1,
            manifest_id="manifest",
            dataset_version="json_2.1.1",
            historical_access_audit_sha256="c" * 64,
            record_count=1,
            records=(access_record(index=1),),
        )


def test_task_manifest_round_trip():
    manifest = TaskAccessManifestV1(
        schema_id=TaskAccessManifestV1.SCHEMA_ID,
        schema_version=1,
        manifest_id="manifest",
        dataset_version="json_2.1.1",
        historical_access_audit_sha256="c" * 64,
        record_count=1,
        records=(access_record(),),
    )
    assert TaskAccessManifestV1.from_json(
        manifest.to_json()
    ) == manifest
