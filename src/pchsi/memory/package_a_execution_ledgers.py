from __future__ import annotations

import os
from pathlib import Path
import shutil

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    sha256_file,
)
from pchsi.memory.effect_ledger import (
    make_memory_effect_entry_v1,
)
from pchsi.memory.event_ledger import (
    make_memory_event_entry_v1,
)
from pchsi.memory.exposure_ledger import (
    make_memory_exposure_entry_v1,
)
from pchsi.memory.ledger_common import (
    append_ledger_entry_v1,
    read_ledger_v1,
)
from pchsi.memory.promotion_ledger import (
    make_memory_promotion_entry_v1,
)


PACKAGE_A_LEDGER_KINDS = (
    "MEMORY_EVENT_LEDGER_V1",
    "MEMORY_RECORD_EFFECT_LEDGER_V1",
    "MEMORY_PROMOTION_LEDGER_V1",
    "MEMORY_EXPOSURE_LEDGER_V1",
)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise OSError("os.write made no progress")
        view = view[count:]


def _write_once(
    path: Path,
    data: bytes,
) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )
    try:
        _write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_directory(path: Path) -> None:
    fd = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ledger_id(
    *,
    candidate_id: str,
    ledger_kind: str,
) -> str:
    return sha256_bytes(
        b"FAILURE_MEMORY_PACKAGE_A_LEDGER_ID_V1"
        + b"\0"
        + canonical_json_bytes(
            {
                "candidate_id": candidate_id,
                "ledger_kind": ledger_kind,
            }
        )
    )


def _entry_id(
    *,
    candidate_id: str,
    ledger_kind: str,
    canonical_record_sha256: str,
) -> str:
    return sha256_bytes(
        b"FAILURE_MEMORY_PACKAGE_A_LEDGER_ENTRY_ID_V1"
        + b"\0"
        + canonical_json_bytes(
            {
                "candidate_id": candidate_id,
                "ledger_kind": ledger_kind,
                "canonical_record_sha256": (
                    canonical_record_sha256
                ),
            }
        )
    )


def write_package_a_materialization_ledgers_v1(
    *,
    ledger_root: Path,
    candidate_id: str,
    initial_record,
    source_report,
    eligibility_bundle,
    event_time_utc: str,
    repository_commit: str,
) -> Path:
    require_lower_sha256(
        "candidate_id",
        candidate_id,
    )
    if (
        not isinstance(event_time_utc, str)
        or not event_time_utc
    ):
        raise ValueError(
            "event_time_utc must be nonempty str"
        )
    if (
        not isinstance(repository_commit, str)
        or len(repository_commit) != 40
        or any(
            ch not in "0123456789abcdef"
            for ch in repository_commit
        )
    ):
        raise ValueError(
            "repository_commit must be "
            "40 lowercase hex"
        )

    root = Path(ledger_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(
            "ledger_root must be existing "
            "non-symlink directory"
        )

    if (
        eligibility_bundle is not None
        and eligibility_bundle.governed_record
        is not None
    ):
        selected_record = (
            eligibility_bundle.governed_record
        )
        decision = "DESCRIPTIVE_DEV_ALLOWED"
        access_scope = "SAME_TASK_DEV_ALLOWED"
        eligibility_status = "ELIGIBLE"
    else:
        selected_record = initial_record
        decision = "DESCRIPTIVE_DEV_DENIED"
        access_scope = "STAGING_ONLY"
        eligibility_status = (
            "NO_ELIGIBILITY_BUNDLE"
            if eligibility_bundle is None
            else eligibility_bundle.status
        )

    lineage_id = selected_record.memory_lineage_id
    record_version = selected_record.record_version
    canonical_record_sha256 = (
        selected_record.canonical_record_sha256
    )
    require_lower_sha256(
        "canonical_record_sha256",
        canonical_record_sha256,
    )

    final_dir = root / candidate_id
    temp_dir = root / f".{candidate_id}.tmp"

    if final_dir.exists() or final_dir.is_symlink():
        raise FileExistsError(str(final_dir))
    if temp_dir.exists() or temp_dir.is_symlink():
        raise FileExistsError(str(temp_dir))

    temp_dir.mkdir(mode=0o700)

    filenames = {
        "MEMORY_EVENT_LEDGER_V1": (
            "memory_event_ledger.jsonl"
        ),
        "MEMORY_RECORD_EFFECT_LEDGER_V1": (
            "memory_record_effect_ledger.jsonl"
        ),
        "MEMORY_PROMOTION_LEDGER_V1": (
            "memory_promotion_ledger.jsonl"
        ),
        "MEMORY_EXPOSURE_LEDGER_V1": (
            "memory_exposure_ledger.jsonl"
        ),
    }

    common = {
        "memory_lineage_id": lineage_id,
        "record_version": record_version,
        "event_time_utc": event_time_utc,
        "repository_commit": repository_commit,
        "previous_entry_sha256": None,
    }

    entries = {
        "MEMORY_EVENT_LEDGER_V1": (
            make_memory_event_entry_v1(
                ledger_id=_ledger_id(
                    candidate_id=candidate_id,
                    ledger_kind=(
                        "MEMORY_EVENT_LEDGER_V1"
                    ),
                ),
                entry_id=_entry_id(
                    candidate_id=candidate_id,
                    ledger_kind=(
                        "MEMORY_EVENT_LEDGER_V1"
                    ),
                    canonical_record_sha256=(
                        canonical_record_sha256
                    ),
                ),
                event_type=(
                    "DESCRIPTIVE_ELIGIBILITY_EVALUATED"
                ),
                details={
                    "candidate_id": candidate_id,
                    "source_integrity_status": (
                        source_report.status
                    ),
                    "source_integrity_report_sha256": (
                        source_report.report_sha256
                    ),
                    "descriptive_eligibility_status": (
                        eligibility_status
                    ),
                    "canonical_record_sha256": (
                        canonical_record_sha256
                    ),
                },
                **common,
            )
        ),
        "MEMORY_RECORD_EFFECT_LEDGER_V1": (
            make_memory_effect_entry_v1(
                ledger_id=_ledger_id(
                    candidate_id=candidate_id,
                    ledger_kind=(
                        "MEMORY_RECORD_EFFECT_LEDGER_V1"
                    ),
                ),
                entry_id=_entry_id(
                    candidate_id=candidate_id,
                    ledger_kind=(
                        "MEMORY_RECORD_EFFECT_LEDGER_V1"
                    ),
                    canonical_record_sha256=(
                        canonical_record_sha256
                    ),
                ),
                effect_status="UNTESTED",
                effect_evidence_scope="UNTESTED",
                evidence_ids=(),
                **common,
            )
        ),
        "MEMORY_PROMOTION_LEDGER_V1": (
            make_memory_promotion_entry_v1(
                ledger_id=_ledger_id(
                    candidate_id=candidate_id,
                    ledger_kind=(
                        "MEMORY_PROMOTION_LEDGER_V1"
                    ),
                ),
                entry_id=_entry_id(
                    candidate_id=candidate_id,
                    ledger_kind=(
                        "MEMORY_PROMOTION_LEDGER_V1"
                    ),
                    canonical_record_sha256=(
                        canonical_record_sha256
                    ),
                ),
                decision=decision,
                access_scope=access_scope,
                referenced_report_ids=(
                    source_report.report_sha256,
                ),
                **common,
            )
        ),
        "MEMORY_EXPOSURE_LEDGER_V1": (
            make_memory_exposure_entry_v1(
                ledger_id=_ledger_id(
                    candidate_id=candidate_id,
                    ledger_kind=(
                        "MEMORY_EXPOSURE_LEDGER_V1"
                    ),
                ),
                entry_id=_entry_id(
                    candidate_id=candidate_id,
                    ledger_kind=(
                        "MEMORY_EXPOSURE_LEDGER_V1"
                    ),
                    canonical_record_sha256=(
                        canonical_record_sha256
                    ),
                ),
                exposure_status=(
                    "NOT_EXPOSED_PACKAGE_A"
                ),
                **common,
            )
        ),
    }

    try:
        for kind in PACKAGE_A_LEDGER_KINDS:
            path = temp_dir / filenames[kind]
            append_ledger_entry_v1(
                path,
                entries[kind],
            )
            lock_path = (
                temp_dir / f".{path.name}.lock"
            )
            if lock_path.exists():
                lock_path.unlink()

            rebuilt = read_ledger_v1(path)
            if rebuilt != (entries[kind],):
                raise RuntimeError(
                    f"{kind} publication audit failed"
                )

        ledger_manifest = canonical_json_bytes(
            {
                "schema_id": (
                    "FAILURE_MEMORY_PACKAGE_A_LEDGER_SET_V1"
                ),
                "schema_version": 1,
                "candidate_id": candidate_id,
                "memory_lineage_id": lineage_id,
                "record_version": record_version,
                "canonical_record_sha256": (
                    canonical_record_sha256
                ),
                "effect_authority": "UNTESTED",
                "policy_exposure": (
                    "NOT_EXPOSED_PACKAGE_A"
                ),
                "ledgers": [
                    {
                        "ledger_kind": kind,
                        "relative_path": filenames[kind],
                        "sha256": sha256_file(
                            temp_dir
                            / filenames[kind]
                        ),
                    }
                    for kind in PACKAGE_A_LEDGER_KINDS
                ],
            }
        )
        _write_once(
            temp_dir / "ledger_set.json",
            ledger_manifest,
        )
        _write_once(
            temp_dir / "ledger_set.sha256",
            (
                sha256_bytes(ledger_manifest)
                + "\n"
            ).encode("ascii"),
        )
        _fsync_directory(temp_dir)

        os.replace(temp_dir, final_dir)
        _fsync_directory(root)
    except BaseException:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )
        raise

    return final_dir
