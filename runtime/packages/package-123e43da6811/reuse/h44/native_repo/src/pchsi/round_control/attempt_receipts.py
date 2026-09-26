from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os

from pchsi.reference_loop.canonical import canonical_json_without_newline

from .common import (
    hashed_payload,
    require_nonnegative_int,
    require_sha256,
    require_text,
)


@dataclass(frozen=True)
class StageAttemptReceiptV1:
    round_id: str
    stage_id: str
    attempt_ordinal: int
    status: str
    input_artifact_sha256: str
    output_artifact_sha256: str | None
    previous_attempt_receipt_sha256: str | None
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "STAGE_ATTEMPT_RECEIPT_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "stage_id": self.stage_id,
            "attempt_ordinal": self.attempt_ordinal,
            "status": self.status,
            "input_artifact_sha256": self.input_artifact_sha256,
            "output_artifact_sha256": self.output_artifact_sha256,
            "previous_attempt_receipt_sha256": self.previous_attempt_receipt_sha256,
            "receipt_sha256": self.receipt_sha256,
        }


def freeze_stage_attempt_receipt(
    *,
    round_id: str,
    stage_id: str,
    attempt_ordinal: int,
    status: str,
    input_artifact_sha256: str,
    output_artifact_sha256: str | None,
    previous_attempt_receipt_sha256: str | None,
) -> StageAttemptReceiptV1:
    require_text("round_id", round_id)
    require_text("stage_id", stage_id)
    require_nonnegative_int("attempt_ordinal", attempt_ordinal)
    if status not in {"STARTED", "COMPLETED", "FAILED", "CENSORED"}:
        raise ValueError("unsupported stage attempt status")
    require_sha256("input_artifact_sha256", input_artifact_sha256)
    if output_artifact_sha256 is not None:
        require_sha256("output_artifact_sha256", output_artifact_sha256)
    if previous_attempt_receipt_sha256 is not None:
        require_sha256(
            "previous_attempt_receipt_sha256",
            previous_attempt_receipt_sha256,
        )
    if attempt_ordinal == 0 and previous_attempt_receipt_sha256 is not None:
        raise ValueError("first attempt cannot reference a previous receipt")
    if attempt_ordinal > 0 and previous_attempt_receipt_sha256 is None:
        raise ValueError("subsequent attempt must reference the previous receipt")
    if status == "STARTED" and output_artifact_sha256 is not None:
        raise ValueError("started attempt cannot publish an output artifact")
    if status == "COMPLETED" and output_artifact_sha256 is None:
        raise ValueError("completed attempt requires an output artifact")

    payload = {
        "schema_id": "STAGE_ATTEMPT_RECEIPT_V1",
        "schema_version": 1,
        "round_id": round_id,
        "stage_id": stage_id,
        "attempt_ordinal": attempt_ordinal,
        "status": status,
        "input_artifact_sha256": input_artifact_sha256,
        "output_artifact_sha256": output_artifact_sha256,
        "previous_attempt_receipt_sha256": previous_attempt_receipt_sha256,
    }
    hashed = hashed_payload(
        domain="STAGE_ATTEMPT_RECEIPT_V1",
        hash_field="receipt_sha256",
        payload=payload,
    )
    return StageAttemptReceiptV1(
        round_id=round_id,
        stage_id=stage_id,
        attempt_ordinal=attempt_ordinal,
        status=status,
        input_artifact_sha256=input_artifact_sha256,
        output_artifact_sha256=output_artifact_sha256,
        previous_attempt_receipt_sha256=previous_attempt_receipt_sha256,
        receipt_sha256=hashed["receipt_sha256"],
    )


def publish_receipt_no_clobber(
    path: Path,
    receipt: StageAttemptReceiptV1,
) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_without_newline(receipt.to_dict()) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("receipt write made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def load_receipt(path: Path) -> StageAttemptReceiptV1:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_id") != "STAGE_ATTEMPT_RECEIPT_V1":
        raise ValueError("unexpected stage attempt receipt schema")
    value = freeze_stage_attempt_receipt(
        round_id=payload["round_id"],
        stage_id=payload["stage_id"],
        attempt_ordinal=payload["attempt_ordinal"],
        status=payload["status"],
        input_artifact_sha256=payload["input_artifact_sha256"],
        output_artifact_sha256=payload["output_artifact_sha256"],
        previous_attempt_receipt_sha256=payload[
            "previous_attempt_receipt_sha256"
        ],
    )
    if value.receipt_sha256 != payload.get("receipt_sha256"):
        raise ValueError("stage attempt receipt SHA mismatch")
    return value
