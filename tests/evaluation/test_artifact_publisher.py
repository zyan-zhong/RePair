from __future__ import annotations

import errno
import json
import os
import stat
from pathlib import Path

import pytest

import pchsi.evaluation.artifact_publisher as artifact_publisher_module
from pchsi.evaluation.artifact_publisher import (
    ArtifactPublisher,
)
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
)
from pchsi.evaluation.episode_artifact import AttemptBundleBytes
from pchsi.evaluation.schema_models import (
    AttemptReceiptV1,
    ScientificCellLockV1,
)

ATTEMPT_ID = "e1-t0000-s0000000017-a000"
CELL_ID = "e1-t0000-s0000000017"


def _bundle(*, suffix: bytes = b"") -> AttemptBundleBytes:
    files = (
        ("attempt.json", b'{"attempt":1}\n' + suffix),
        ("action_traces.jsonl", b'{"trace":1}\n'),
        ("public_transitions.jsonl", b""),
    )
    checksum_text = "".join(
        f"{sha256_bytes(data)}  {name}\n"
        for name, data in files
    ).encode("utf-8")
    identities = [
        {"filename": name, "sha256": sha256_bytes(data)}
        for name, data in (*files, ("SHA256SUMS", checksum_text))
    ]
    return AttemptBundleBytes(
        attempt_json=files[0][1],
        action_traces_jsonl=files[1][1],
        public_transitions_jsonl=files[2][1],
        checksums_text=checksum_text,
        episode_semantic_sha256="c" * 64,
        attempt_bundle_sha256=sha256_bytes(
            canonical_json_bytes(identities)
        ),
    )


def _started() -> AttemptReceiptV1:
    return AttemptReceiptV1(
        schema_id="E1_ATTEMPT_RECEIPT_V1",
        schema_version=1,
        receipt_kind="STARTED",
        run_id="run-e1",
        scheduled_cell_id=CELL_ID,
        execution_attempt_id=ATTEMPT_ID,
        attempt_ordinal=0,
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        run_schedule_sha256="a" * 64,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_NOT_PRODUCED"
        ),
        operational_finalization_status="STAGING",
        episode_semantic_sha256=None,
        attempt_bundle_sha256=None,
        terminal_class=None,
        error_code=None,
        created_at_utc="2026-08-07T00:00:00Z",
    )


def _terminal(bundle: AttemptBundleBytes) -> AttemptReceiptV1:
    return AttemptReceiptV1(
        schema_id="E1_ATTEMPT_RECEIPT_V1",
        schema_version=1,
        receipt_kind="TERMINAL",
        run_id="run-e1",
        scheduled_cell_id=CELL_ID,
        execution_attempt_id=ATTEMPT_ID,
        attempt_ordinal=0,
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        run_schedule_sha256="a" * 64,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"
        ),
        operational_finalization_status="PUBLISHED",
        episode_semantic_sha256=(
            bundle.episode_semantic_sha256
        ),
        attempt_bundle_sha256=(
            bundle.attempt_bundle_sha256
        ),
        terminal_class="SCIENTIFIC_RESULT",
        error_code=None,
        created_at_utc="2026-08-07T00:00:01Z",
    )


def _lock(bundle: AttemptBundleBytes) -> ScientificCellLockV1:
    return ScientificCellLockV1(
        schema_id="E1_SCIENTIFIC_CELL_LOCK_V1",
        schema_version=1,
        run_id="run-e1",
        scheduled_cell_id=CELL_ID,
        execution_attempt_id=ATTEMPT_ID,
        run_schedule_sha256="a" * 64,
        episode_semantic_sha256=(
            bundle.episode_semantic_sha256
        ),
        attempt_bundle_sha256=(
            bundle.attempt_bundle_sha256
        ),
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"
        ),
        evaluator_commit="evaluator",
    )


def test_publication_is_directory_level_atomic_and_no_clobber(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    publisher = ArtifactPublisher(run_root=tmp_path / "run")

    started_path = publisher.write_started_receipt(_started())
    staging = publisher.stage_bundle(
        execution_attempt_id=ATTEMPT_ID,
        bundle=bundle,
    )

    final = tmp_path / "run" / "attempts" / ATTEMPT_ID
    assert staging.is_dir()
    assert not final.exists()

    publisher.write_scientific_cell_lock(_lock(bundle))
    published = publisher.publish_staged_directory(
        execution_attempt_id=ATTEMPT_ID,
        lock=_lock(bundle),
    )
    terminal_path = publisher.write_terminal_receipt(
        _terminal(bundle)
    )

    assert published == final
    assert final.is_dir()
    assert not staging.exists()
    assert set(path.name for path in final.iterdir()) == {
        "attempt.json",
        "action_traces.jsonl",
        "public_transitions.jsonl",
        "SHA256SUMS",
    }
    assert stat.S_IMODE(started_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(terminal_path.stat().st_mode) == 0o600

    with pytest.raises(FileExistsError):
        publisher.write_started_receipt(_started())
    with pytest.raises(FileExistsError):
        publisher.write_terminal_receipt(_terminal(bundle))
    with pytest.raises(FileExistsError):
        publisher.stage_bundle(
            execution_attempt_id=ATTEMPT_ID,
            bundle=bundle,
        )


def test_every_started_attempt_gets_one_terminal_receipt(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    publisher = ArtifactPublisher(run_root=tmp_path / "run")
    publisher.publish_scientific_attempt(
        started_receipt=_started(),
        terminal_receipt=_terminal(bundle),
        lock=_lock(bundle),
        bundle=bundle,
    )

    ledger = tmp_path / "run" / "attempt_ledger"
    assert (ledger / f"{ATTEMPT_ID}.started.json").is_file()
    assert (ledger / f"{ATTEMPT_ID}.terminal.json").is_file()
    assert len(tuple(ledger.glob("*.started.json"))) == 1
    assert len(tuple(ledger.glob("*.terminal.json"))) == 1



def test_guarded_posix_fallback_handles_renameat2_einval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle()
    publisher = ArtifactPublisher(run_root=tmp_path / "run")

    publisher.write_started_receipt(_started())
    staging = publisher.stage_bundle(
        execution_attempt_id=ATTEMPT_ID,
        bundle=bundle,
    )
    lock = _lock(bundle)
    publisher.write_scientific_cell_lock(lock)

    def unsupported(*args, **kwargs):
        raise OSError(
            errno.EINVAL,
            "filesystem does not support RENAME_NOREPLACE",
        )

    monkeypatch.setattr(
        artifact_publisher_module,
        "_rename_directory_native_noreplace",
        unsupported,
    )

    final = tmp_path / "run" / "attempts" / ATTEMPT_ID
    published = publisher.publish_staged_directory(
        execution_attempt_id=ATTEMPT_ID,
        lock=lock,
    )

    assert published == final
    assert final.is_dir()
    assert not staging.exists()


def test_guarded_posix_fallback_refuses_existing_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle()
    publisher = ArtifactPublisher(run_root=tmp_path / "run")

    publisher.write_started_receipt(_started())
    staging = publisher.stage_bundle(
        execution_attempt_id=ATTEMPT_ID,
        bundle=bundle,
    )
    lock = _lock(bundle)
    publisher.write_scientific_cell_lock(lock)

    def unsupported(*args, **kwargs):
        raise OSError(
            errno.EINVAL,
            "filesystem does not support RENAME_NOREPLACE",
        )

    monkeypatch.setattr(
        artifact_publisher_module,
        "_rename_directory_native_noreplace",
        unsupported,
    )

    final = tmp_path / "run" / "attempts" / ATTEMPT_ID
    final.mkdir(mode=0o700)
    sentinel = final / "do-not-overwrite"
    sentinel.write_text("sentinel\\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        publisher.publish_staged_directory(
            execution_attempt_id=ATTEMPT_ID,
            lock=lock,
        )

    assert staging.is_dir()
    assert sentinel.read_text(encoding="utf-8") == "sentinel\\n"


def test_publish_staged_directory_requires_matching_scientific_lock(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    publisher = ArtifactPublisher(run_root=tmp_path / "run")
    publisher.write_started_receipt(_started())
    publisher.stage_bundle(
        execution_attempt_id=ATTEMPT_ID,
        bundle=bundle,
    )

    lock = _lock(bundle)

    with pytest.raises(FileNotFoundError):
        publisher.publish_staged_directory(
            execution_attempt_id=ATTEMPT_ID,
            lock=lock,
        )
