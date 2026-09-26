from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import (
    ContractError,
    domain_sha256,
    sha256_file,
    write_json_create_once,
)


def _artifact_ref(
    *,
    logical_name: str,
    retention_class: str,
    path: Path,
    schema_id: str | None = None,
) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ContractError(f"ARTIFACT_FILE_INVALID:{path}")
    return {
        "logical_name": logical_name,
        "retention_class": retention_class,
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "schema_id": schema_id,
    }


def build_input_artifact_index(
    *,
    round_id: str,
    stage_id: str,
    refs: list[dict[str, Any]],
) -> dict[str, Any]:
    value = {
        "schema_id": "ROUND_ARTIFACT_INDEX_V1",
        "schema_version": 1,
        "round_id": round_id,
        "stage_id": stage_id,
        "direction": "INPUT",
        "artifacts": refs,
        "artifact_index_sha256": "",
    }
    value["artifact_index_sha256"] = domain_sha256(
        value["schema_id"],
        value,
        sha_field="artifact_index_sha256",
    )
    return value


def build_output_artifact_index(
    *,
    round_id: str,
    stage_id: str,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    value = {
        "schema_id": "ROUND_ARTIFACT_INDEX_V1",
        "schema_version": 1,
        "round_id": round_id,
        "stage_id": stage_id,
        "direction": "OUTPUT",
        "artifacts": artifacts,
        "artifact_index_sha256": "",
    }
    value["artifact_index_sha256"] = domain_sha256(
        value["schema_id"],
        value,
        sha_field="artifact_index_sha256",
    )
    return value


def build_stage_receipt(
    *,
    round_id: str,
    stage_id: str,
    stage_attempt_id: str,
    input_artifact_index_sha256: str,
    output_artifact_index_sha256: str | None,
    runner_freeze_root_sha256: str,
    authorization_sha256: str,
    started_from_receipt_sha256: str | None,
    previous_stage_receipt_sha256: str | None,
    terminal_status: str,
    scientific_missingness_class: str | None,
    model_training_executed: bool | None,
    model_training_execution_status: str,
    failure_summary: str | None,
) -> dict[str, Any]:
    value = {
        "schema_id": "ROUND_STAGE_RECEIPT_V1",
        "schema_version": 1,
        "round_id": round_id,
        "stage_id": stage_id,
        "stage_attempt_id": stage_attempt_id,
        "input_artifact_index_sha256": input_artifact_index_sha256,
        "output_artifact_index_sha256": output_artifact_index_sha256,
        "runner_freeze_root_sha256": runner_freeze_root_sha256,
        "authorization_sha256": authorization_sha256,
        "started_from_receipt_sha256": started_from_receipt_sha256,
        "previous_stage_receipt_sha256": previous_stage_receipt_sha256,
        "terminal_status": terminal_status,
        "scientific_missingness_class": scientific_missingness_class,
        "provider_or_environment_called": False,
        "model_training_executed": model_training_executed,
        "model_training_execution_status": model_training_execution_status,
        "failure_summary": failure_summary,
        "stage_receipt_sha256": "",
    }
    value["stage_receipt_sha256"] = domain_sha256(
        value["schema_id"],
        value,
        sha_field="stage_receipt_sha256",
    )
    return value


def create_attempt_root(path: Path) -> Path:
    path = path.resolve()
    if path.exists():
        raise ContractError(f"STAGE_ATTEMPT_ROOT_ALREADY_EXISTS:{path}")
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_attempt_json(
    attempt_root: Path,
    filename: str,
    value: dict[str, Any],
) -> Path:
    path = attempt_root / filename
    write_json_create_once(path, value)
    return path


def artifact_ref_for_output(
    *,
    logical_name: str,
    retention_class: str,
    path: Path,
    schema_id: str | None = None,
) -> dict[str, Any]:
    return _artifact_ref(
        logical_name=logical_name,
        retention_class=retention_class,
        path=path,
        schema_id=schema_id,
    )
