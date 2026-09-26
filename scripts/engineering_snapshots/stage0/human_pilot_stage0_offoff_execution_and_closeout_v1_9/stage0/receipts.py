from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import (
    Stage0Error,
    append_canonical_json_line,
    domain_sha256,
    read_json_lines,
    require_lower_sha256,
)

SCHEMA_ID = "HUMAN_PILOT_STAGE0_CELL_RECEIPT_V1"


def make_cell_receipt(
    *,
    condition_id: str,
    condition_cell_id: str,
    manifest_index: int,
    task_id: str,
    seed: int,
    execution_attempt_id: str,
    attempt_bundle_sha256: str,
    success: bool,
    termination_reason: str,
    previous_receipt_sha256: str | None,
) -> dict[str, Any]:
    require_lower_sha256("attempt_bundle_sha256", attempt_bundle_sha256)
    if previous_receipt_sha256 is not None:
        require_lower_sha256(
            "previous_receipt_sha256",
            previous_receipt_sha256,
        )
    value: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "condition_id": condition_id,
        "condition_cell_id": condition_cell_id,
        "manifest_index": manifest_index,
        "task_id": task_id,
        "seed": seed,
        "execution_attempt_id": execution_attempt_id,
        "attempt_bundle_sha256": attempt_bundle_sha256,
        "success": success,
        "termination_reason": termination_reason,
        "memory_state": "OFF",
        "harness_state": "OFF",
        "previous_receipt_sha256": previous_receipt_sha256,
        "receipt_sha256": "",
    }
    value["receipt_sha256"] = domain_sha256(
        SCHEMA_ID,
        value,
        sha_field="receipt_sha256",
    )
    return value


def _validate_receipt(value: dict[str, Any]) -> None:
    if value.get("schema_id") != SCHEMA_ID:
        raise Stage0Error("CELL_RECEIPT_SCHEMA_CHANGED")
    expected = value.get("receipt_sha256")
    require_lower_sha256("receipt_sha256", expected)
    observed = domain_sha256(
        SCHEMA_ID,
        value,
        sha_field="receipt_sha256",
    )
    if observed != expected:
        raise Stage0Error("CELL_RECEIPT_HASH_MISMATCH")
    if value.get("memory_state") != "OFF":
        raise Stage0Error("CELL_RECEIPT_MEMORY_NOT_OFF")
    if value.get("harness_state") != "OFF":
        raise Stage0Error("CELL_RECEIPT_HARNESS_NOT_OFF")
    if type(value.get("success")) is not bool:
        raise Stage0Error("CELL_RECEIPT_SUCCESS_INVALID")


def load_receipts(path: Path) -> tuple[dict[str, Any], ...]:
    rows = read_json_lines(path)
    previous: str | None = None
    identities: set[tuple[str, str]] = set()
    for row in rows:
        _validate_receipt(row)
        if row.get("previous_receipt_sha256") != previous:
            raise Stage0Error("CELL_RECEIPT_CHAIN_BROKEN")
        identity = (row["condition_id"], row["condition_cell_id"])
        if identity in identities:
            raise Stage0Error("CELL_RECEIPT_DUPLICATE_IDENTITY")
        identities.add(identity)
        previous = row["receipt_sha256"]
    return rows


def append_receipt(path: Path, value: dict[str, Any]) -> None:
    _validate_receipt(value)
    existing = load_receipts(path)
    expected_previous = None if not existing else existing[-1]["receipt_sha256"]
    if value.get("previous_receipt_sha256") != expected_previous:
        raise Stage0Error("CELL_RECEIPT_APPEND_PREVIOUS_MISMATCH")
    identity = (value["condition_id"], value["condition_cell_id"])
    if any(
        (row["condition_id"], row["condition_cell_id"]) == identity
        for row in existing
    ):
        raise Stage0Error("CELL_RECEIPT_ALREADY_EXISTS")
    append_canonical_json_line(path, value)
