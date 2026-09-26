"""Cross-manifest validation for distillation governance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .canonical_evidence import canonical_json_bytes, sha256_bytes
from .condition_run_schedule import (
    ConditionRunPurpose,
    ConditionRunScheduleV1,
    condition_cell_id,
)
from .distillation_access import (
    DistillationAccessClass,
    HistoricalAccessAuditV1,
    TaskAccessManifestV1,
)
from .policy_condition import PolicyConditionManifestV1


@dataclass(frozen=True, slots=True)
class DistillationGovernanceBundleV1:
    historical_access_audit: HistoricalAccessAuditV1
    task_access_manifest: TaskAccessManifestV1
    policy_condition: PolicyConditionManifestV1
    schedule: ConditionRunScheduleV1


def canonical_model_sha256(model: object) -> str:
    to_dict = getattr(model, "to_dict", None)
    if not callable(to_dict):
        raise TypeError("model must expose to_dict()")
    payload = to_dict()
    if not isinstance(payload, dict):
        raise TypeError("to_dict() must return dict")
    return sha256_bytes(canonical_json_bytes(payload))


def validate_distillation_governance_bundle(
    bundle: DistillationGovernanceBundleV1,
) -> None:
    if type(bundle) is not DistillationGovernanceBundleV1:
        raise TypeError(
            "bundle must be DistillationGovernanceBundleV1"
        )
    audit = bundle.historical_access_audit
    access = bundle.task_access_manifest
    policy = bundle.policy_condition
    schedule = bundle.schedule
    if type(audit) is not HistoricalAccessAuditV1:
        raise TypeError(
            "historical_access_audit has the wrong type"
        )
    if type(access) is not TaskAccessManifestV1:
        raise TypeError("task_access_manifest has the wrong type")
    if type(policy) is not PolicyConditionManifestV1:
        raise TypeError("policy_condition has the wrong type")
    if type(schedule) is not ConditionRunScheduleV1:
        raise TypeError("schedule has the wrong type")

    audit_sha = canonical_model_sha256(audit)
    access_sha = canonical_model_sha256(access)
    policy_sha = canonical_model_sha256(policy)
    if access.historical_access_audit_sha256 != audit_sha:
        raise ValueError(
            "historical_access_audit_sha256 does not bind the audit"
        )
    if access.dataset_version != audit.dataset_version:
        raise ValueError("dataset_version mismatch")

    audit_by_task = {
        record.task_id: record for record in audit.records
    }
    access_by_task = {
        record.task_id: record for record in access.records
    }
    if set(audit_by_task) != set(access_by_task):
        raise ValueError(
            "audit and task access must cover identical task IDs"
        )
    for task_id, access_record in access_by_task.items():
        audit_record = audit_by_task[task_id]
        if access_record.gamefile != audit_record.gamefile:
            raise ValueError(
                f"gamefile mismatch for task {task_id}"
            )
        if access_record.dataset_split != audit_record.dataset_split:
            raise ValueError(
                f"dataset_split mismatch for task {task_id}"
            )
        if (
            access_record.historical_access_flags
            != audit_record.access_flags
        ):
            raise ValueError(
                f"historical access flags mismatch for task {task_id}"
            )

    if schedule.task_access_manifest_sha256 != access_sha:
        raise ValueError(
            "schedule task_access_manifest_sha256 mismatch"
        )
    if schedule.policy_condition_manifest_sha256 != policy_sha:
        raise ValueError(
            "schedule policy_condition_manifest_sha256 mismatch"
        )

    by_index = {
        record.manifest_index: record for record in access.records
    }
    for cell in schedule.cells:
        try:
            record = by_index[cell.manifest_index]
        except KeyError as error:
            raise ValueError(
                "schedule references an unknown manifest_index"
            ) from error
        if cell.task_id != record.task_id:
            raise ValueError(
                "schedule manifest_index/task_id pair mismatch"
            )
        expected_cell_id = condition_cell_id(
            policy_condition_id=policy.policy_condition_id,
            manifest_index=cell.manifest_index,
            seed=cell.seed,
        )
        if cell.condition_cell_id != expected_cell_id:
            raise ValueError(
                "schedule condition_cell_id does not bind "
                "policy condition, manifest index and seed"
            )
        if record.access_class is not schedule.target_access_class:
            raise ValueError(
                "schedule cell access class does not match target"
            )
        if (
            schedule.run_purpose
            is ConditionRunPurpose.P1_PI0_DEV_ROLLOUT
        ):
            if (
                record.access_class
                is not DistillationAccessClass.DEV_VISIBLE
                or not record.teacher_call_permitted
                or not record.training_permitted
            ):
                raise ValueError(
                    "P1 schedule references a non-DEV record"
                )
        else:
            if (
                record.access_class
                is not DistillationAccessClass.SELECT_SUMMARY_ONLY
                or not record.select_evaluation_permitted
            ):
                raise ValueError(
                    "SELECT schedule references a non-SELECT record"
                )


import os


_DESIGN_MERGE_COMMIT = (
    "e777ed20fd91f508680326fcf7c32761978afe77"
)


@dataclass(frozen=True, slots=True)
class GovernanceFreezeResultV1:
    output_dir: Path
    historical_access_audit_sha256: str
    task_access_manifest_sha256: str
    policy_condition_manifest_sha256: str
    condition_run_schedule_sha256: str
    governance_freeze_index_sha256: str


def _write_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def freeze_governance_inputs(
    *,
    historical_access_audit: HistoricalAccessAuditV1,
    task_access_manifest: TaskAccessManifestV1,
    policy_condition: PolicyConditionManifestV1,
    schedule: ConditionRunScheduleV1,
    output_dir: Path,
) -> GovernanceFreezeResultV1:
    bundle = DistillationGovernanceBundleV1(
        historical_access_audit=historical_access_audit,
        task_access_manifest=task_access_manifest,
        policy_condition=policy_condition,
        schedule=schedule,
    )
    validate_distillation_governance_bundle(bundle)

    output = Path(output_dir)
    if os.path.lexists(output):
        raise FileExistsError(f"output already exists: {output}")
    parent = output.parent
    if parent.is_symlink():
        raise ValueError("output parent must not be a symlink")
    if not parent.is_dir():
        raise ValueError(
            "output parent must be an existing directory"
        )

    audit_sha = canonical_model_sha256(historical_access_audit)
    access_sha = canonical_model_sha256(task_access_manifest)
    policy_sha = canonical_model_sha256(policy_condition)
    schedule_sha = canonical_model_sha256(schedule)

    index = {
        "schema_id": "DISTILLATION_GOVERNANCE_FREEZE_INDEX_V1",
        "schema_version": 1,
        "historical_access_audit_sha256": audit_sha,
        "task_access_manifest_sha256": access_sha,
        "policy_condition_manifest_sha256": policy_sha,
        "condition_run_schedule_sha256": schedule_sha,
        "design_merge_commit": _DESIGN_MERGE_COMMIT,
    }
    index_bytes = canonical_json_bytes(index)
    index_sha = sha256_bytes(index_bytes)

    os.mkdir(output, mode=0o700)
    payloads = {
        "historical_access_audit.json": (
            historical_access_audit.to_json().encode("utf-8")
        ),
        "historical_access_audit.sha256": (
            f"{audit_sha}\n".encode("ascii")
        ),
        "task_access_manifest.json": (
            task_access_manifest.to_json().encode("utf-8")
        ),
        "task_access_manifest.sha256": (
            f"{access_sha}\n".encode("ascii")
        ),
        "policy_condition_manifest.json": (
            policy_condition.to_json().encode("utf-8")
        ),
        "policy_condition_manifest.sha256": (
            f"{policy_sha}\n".encode("ascii")
        ),
        "condition_run_schedule.json": (
            schedule.to_json().encode("utf-8")
        ),
        "condition_run_schedule.sha256": (
            f"{schedule_sha}\n".encode("ascii")
        ),
        "governance_freeze_index.json": index_bytes,
        "governance_freeze_index.sha256": (
            f"{index_sha}\n".encode("ascii")
        ),
    }
    for name in sorted(payloads):
        _write_exclusive(output / name, payloads[name])
    directory_fd = os.open(output, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)

    return GovernanceFreezeResultV1(
        output_dir=output,
        historical_access_audit_sha256=audit_sha,
        task_access_manifest_sha256=access_sha,
        policy_condition_manifest_sha256=policy_sha,
        condition_run_schedule_sha256=schedule_sha,
        governance_freeze_index_sha256=index_sha,
    )
