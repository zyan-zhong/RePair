from pathlib import Path
import pytest

from pchsi.round_control.attempt_receipts import (
    freeze_stage_attempt_receipt,
    load_receipt,
    publish_receipt_no_clobber,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def test_stage_attempt_receipts_are_append_only(tmp_path: Path) -> None:
    started = freeze_stage_attempt_receipt(
        round_id="r1",
        stage_id="ANALYSIS",
        attempt_ordinal=0,
        status="STARTED",
        input_artifact_sha256=SHA_A,
        output_artifact_sha256=None,
        previous_attempt_receipt_sha256=None,
    )
    path = tmp_path / "attempt_000_started.json"
    publish_receipt_no_clobber(path, started)

    with pytest.raises(FileExistsError):
        publish_receipt_no_clobber(path, started)

    loaded = load_receipt(path)
    assert loaded.receipt_sha256 == started.receipt_sha256


def test_new_attempt_requires_previous_receipt() -> None:
    with pytest.raises(ValueError):
        freeze_stage_attempt_receipt(
            round_id="r1",
            stage_id="ANALYSIS",
            attempt_ordinal=1,
            status="FAILED",
            input_artifact_sha256=SHA_A,
            output_artifact_sha256=SHA_B,
            previous_attempt_receipt_sha256=None,
        )

    retry = freeze_stage_attempt_receipt(
        round_id="r1",
        stage_id="ANALYSIS",
        attempt_ordinal=1,
        status="COMPLETED",
        input_artifact_sha256=SHA_A,
        output_artifact_sha256=SHA_B,
        previous_attempt_receipt_sha256=SHA_C,
    )
    assert retry.attempt_ordinal == 1
