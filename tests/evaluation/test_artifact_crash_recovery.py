from __future__ import annotations

import errno
from pathlib import Path

import pytest

import pchsi.evaluation.artifact_publisher as artifact_publisher_module
from pchsi.evaluation.artifact_publisher import (
    ArtifactPublisher,
    InjectedPublicationFault,
    PublicationFaultPoint,
    PublicationRecoveryStatus,
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
        scientific_outcome_status="SCIENTIFIC_OUTCOME_NOT_PRODUCED",
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
        episode_semantic_sha256=bundle.episode_semantic_sha256,
        attempt_bundle_sha256=bundle.attempt_bundle_sha256,
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
        episode_semantic_sha256=bundle.episode_semantic_sha256,
        attempt_bundle_sha256=bundle.attempt_bundle_sha256,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"
        ),
        evaluator_commit="evaluator",
    )


def _inject_at(target: PublicationFaultPoint):
    def inject(point: PublicationFaultPoint) -> None:
        if point is target:
            raise InjectedPublicationFault(point.value)
    return inject


def test_publication_retry_uses_identical_staging_bytes(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    publisher = ArtifactPublisher(
        run_root=tmp_path / "run",
        fault_injector=_inject_at(
            PublicationFaultPoint.AFTER_CELL_LOCK
        ),
    )

    with pytest.raises(InjectedPublicationFault):
        publisher.publish_scientific_attempt(
            started_receipt=_started(),
            terminal_receipt=_terminal(bundle),
            lock=_lock(bundle),
            bundle=bundle,
        )

    clean = ArtifactPublisher(run_root=tmp_path / "run")

    with pytest.raises(ValueError, match="identical"):
        clean.recover_publication(
            lock=_lock(bundle),
            bundle=_bundle(suffix=b"changed"),
        )

    result = clean.recover_publication(
        lock=_lock(bundle),
        bundle=bundle,
    )
    assert result.status is PublicationRecoveryStatus.PUBLISHED
    assert result.published_path is not None
    assert result.published_path.is_dir()


def test_lost_staging_remains_unresolved_and_never_authorizes_model_retry(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    publisher = ArtifactPublisher(run_root=tmp_path / "run")
    publisher.write_started_receipt(_started())
    publisher.write_scientific_cell_lock(_lock(bundle))

    result = publisher.recover_publication(
        lock=_lock(bundle),
        bundle=bundle,
    )

    assert result.status is (
        PublicationRecoveryStatus.STAGING_LOST_UNRESOLVED
    )
    assert result.published_path is None


@pytest.mark.parametrize(
    "fault_point",
    list(PublicationFaultPoint),
)
def test_crash_after_each_frozen_boundary_has_defined_recovery(
    tmp_path: Path,
    fault_point: PublicationFaultPoint,
) -> None:
    bundle = _bundle()
    run_root = tmp_path / fault_point.value
    publisher = ArtifactPublisher(
        run_root=run_root,
        fault_injector=_inject_at(fault_point),
    )

    with pytest.raises(InjectedPublicationFault):
        publisher.publish_scientific_attempt(
            started_receipt=_started(),
            terminal_receipt=_terminal(bundle),
            lock=_lock(bundle),
            bundle=bundle,
        )

    clean = ArtifactPublisher(run_root=run_root)
    staging = (
        run_root / "attempts" / ".staging" / ATTEMPT_ID
    )
    final = run_root / "attempts" / ATTEMPT_ID
    lock_path = run_root / "cell_locks" / f"{CELL_ID}.json"
    started_path = (
        run_root
        / "attempt_ledger"
        / f"{ATTEMPT_ID}.started.json"
    )
    terminal_path = (
        run_root
        / "attempt_ledger"
        / f"{ATTEMPT_ID}.terminal.json"
    )

    assert started_path.is_file()
    assert not terminal_path.exists()

    if fault_point is PublicationFaultPoint.AFTER_STARTED_RECEIPT:
        assert not staging.exists()
        assert not final.exists()
        assert not lock_path.exists()
        return

    if fault_point is PublicationFaultPoint.AFTER_PARTIAL_STAGING:
        assert staging.is_dir()
        assert not final.exists()
        assert not lock_path.exists()
        with pytest.raises(ValueError, match="identical"):
            clean.recover_publication(
                lock=_lock(bundle),
                bundle=bundle,
            )
        return

    result = clean.recover_publication(
        lock=_lock(bundle),
        bundle=bundle,
    )
    assert result.status in {
        PublicationRecoveryStatus.PUBLISHED,
        PublicationRecoveryStatus.ALREADY_PUBLISHED,
    }
    assert final.is_dir()
    assert lock_path.is_file()

    clean.write_terminal_receipt(_terminal(bundle))
    assert terminal_path.is_file()



def test_recovery_uses_guarded_posix_fallback_when_noreplace_is_unsupported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle()
    run_root = tmp_path / "run"

    publisher = ArtifactPublisher(
        run_root=run_root,
        fault_injector=_inject_at(
            PublicationFaultPoint.AFTER_CELL_LOCK
        ),
    )

    with pytest.raises(InjectedPublicationFault):
        publisher.publish_scientific_attempt(
            started_receipt=_started(),
            terminal_receipt=_terminal(bundle),
            lock=_lock(bundle),
            bundle=bundle,
        )

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

    clean = ArtifactPublisher(run_root=run_root)
    result = clean.recover_publication(
        lock=_lock(bundle),
        bundle=bundle,
    )

    assert result.status is PublicationRecoveryStatus.PUBLISHED
    assert result.published_path is not None
    assert result.published_path.is_dir()
