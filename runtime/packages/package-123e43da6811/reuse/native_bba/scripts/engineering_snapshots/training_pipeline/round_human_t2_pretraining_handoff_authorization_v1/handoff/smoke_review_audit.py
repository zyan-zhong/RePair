from __future__ import annotations

import json
from pathlib import Path
import stat
import zipfile
from typing import Any

from .common import (
    HandoffError,
    domain_sha256,
    require_domain_sha,
    require_file_sha,
    sha256_file,
)


EXPECTED_MEMBERS = {
    "REVIEW_MANIFEST_V1.json",
    "authorities/smoke_authorization.json",
    "authorities/smoke_binding.json",
    "evidence/input_artifact_index.json",
    "evidence/output_artifact_index.json",
    "evidence/smoke_result.json",
    "evidence/started_stage_receipt.json",
    "evidence/terminal_stage_receipt.json",
}


def _json_member(
    archive: zipfile.ZipFile,
    name: str,
) -> dict[str, Any]:
    try:
        raw = archive.read(name)
    except KeyError as exc:
        raise HandoffError(f"SMOKE_REVIEW_MEMBER_MISSING:{name}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HandoffError(f"SMOKE_REVIEW_JSON_INVALID:{name}:{exc}") from exc
    if not isinstance(value, dict):
        raise HandoffError(f"SMOKE_REVIEW_JSON_OBJECT_REQUIRED:{name}")
    return value


def audit_smoke_review_bundle(
    bundle_path: Path,
    *,
    expected_bundle_sha256: str,
    expected_member_count: int,
    expected_runner_freeze_root_sha256: str,
    expected_stage_binding_domain_sha256: str,
    expected_initial_trainable_sha256: str,
) -> dict[str, Any]:
    require_file_sha(
        bundle_path,
        expected_bundle_sha256,
        "SMOKE_REVIEW_BUNDLE",
    )

    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = archive.namelist()
        if len(names) != expected_member_count:
            raise HandoffError(
                f"SMOKE_REVIEW_MEMBER_COUNT_CHANGED:{len(names)}:"
                f"{expected_member_count}"
            )
        if set(names) != EXPECTED_MEMBERS:
            raise HandoffError(
                "SMOKE_REVIEW_MEMBER_SET_CHANGED:"
                + repr(sorted(names))
            )
        if archive.testzip() is not None:
            raise HandoffError("SMOKE_REVIEW_ZIP_CRC_FAILED")

        for info in archive.infolist():
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise HandoffError(
                    f"SMOKE_REVIEW_SYMLINK_MEMBER_FORBIDDEN:{info.filename}"
                )

        review = _json_member(archive, "REVIEW_MANIFEST_V1.json")
        binding = _json_member(
            archive,
            "authorities/smoke_binding.json",
        )
        authorization = _json_member(
            archive,
            "authorities/smoke_authorization.json",
        )
        input_index = _json_member(
            archive,
            "evidence/input_artifact_index.json",
        )
        output_index = _json_member(
            archive,
            "evidence/output_artifact_index.json",
        )
        result = _json_member(
            archive,
            "evidence/smoke_result.json",
        )
        started = _json_member(
            archive,
            "evidence/started_stage_receipt.json",
        )
        terminal = _json_member(
            archive,
            "evidence/terminal_stage_receipt.json",
        )

        require_domain_sha(
            binding,
            schema_id=(
                "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_BINDING_V1"
            ),
            sha_field="smoke_binding_sha256",
        )
        require_domain_sha(
            authorization,
            schema_id=(
                "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_"
                "AUTHORIZATION_V1"
            ),
            sha_field="authorization_sha256",
        )
        require_domain_sha(
            input_index,
            schema_id="ROUND_ARTIFACT_INDEX_V1",
            sha_field="artifact_index_sha256",
        )
        require_domain_sha(
            output_index,
            schema_id="ROUND_ARTIFACT_INDEX_V1",
            sha_field="artifact_index_sha256",
        )
        require_domain_sha(
            started,
            schema_id="ROUND_STAGE_RECEIPT_V1",
            sha_field="stage_receipt_sha256",
        )
        require_domain_sha(
            terminal,
            schema_id="ROUND_STAGE_RECEIPT_V1",
            sha_field="stage_receipt_sha256",
        )
        require_domain_sha(
            result,
            schema_id=(
                "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_RESULT_V1"
            ),
            sha_field="result_sha256",
        )

        file_rows = review.get("files")
        if not isinstance(file_rows, list) or len(file_rows) != 7:
            raise HandoffError("SMOKE_REVIEW_FILE_ROWS_CHANGED")
        observed_rows = {}
        for row in file_rows:
            if not isinstance(row, dict):
                raise HandoffError("SMOKE_REVIEW_FILE_ROW_INVALID")
            path = row.get("path")
            if not isinstance(path, str):
                raise HandoffError("SMOKE_REVIEW_FILE_PATH_INVALID")
            member_name = path
            if member_name not in EXPECTED_MEMBERS:
                raise HandoffError(
                    f"SMOKE_REVIEW_FILE_MEMBER_UNEXPECTED:{member_name}"
                )
            raw = archive.read(member_name)
            import hashlib
            observed_sha = hashlib.sha256(raw).hexdigest()
            if observed_sha != row.get("sha256"):
                raise HandoffError(
                    f"SMOKE_REVIEW_FILE_SHA_MISMATCH:{member_name}"
                )
            if len(raw) != row.get("size_bytes"):
                raise HandoffError(
                    f"SMOKE_REVIEW_FILE_SIZE_MISMATCH:{member_name}"
                )
            observed_rows[member_name] = row

        if review.get("review_status") != "READY_FOR_SMOKE_RESULT_REVIEW":
            raise HandoffError("SMOKE_REVIEW_STATUS_CHANGED")
        if (
            review.get("reviewed_training_stage_freeze_root_sha256")
            != expected_runner_freeze_root_sha256
        ):
            raise HandoffError("SMOKE_REVIEW_RUNNER_FREEZE_ROOT_CHANGED")
        if review.get("model_load_count") != 1:
            raise HandoffError("SMOKE_REVIEW_MODEL_LOAD_COUNT_CHANGED")
        for field in (
            "forward_count",
            "backward_count",
            "optimizer_step_count",
            "training_execution_count",
        ):
            if review.get(field) != 0:
                raise HandoffError(f"SMOKE_REVIEW_{field.upper()}_NOT_ZERO")
        if review.get("formal_training_authorized") is not False:
            raise HandoffError("SMOKE_REVIEW_FORMAL_TRAINING_AUTHORIZED")

        expected_result = {
            "status": "PASS",
            "stage_binding_sha256": expected_stage_binding_domain_sha256,
            "reviewed_training_stage_freeze_root_sha256": (
                expected_runner_freeze_root_sha256
            ),
            "expected_initial_trainable_parameter_sha256": (
                expected_initial_trainable_sha256
            ),
            "observed_initial_trainable_parameter_sha256": (
                expected_initial_trainable_sha256
            ),
            "post_check_trainable_parameter_sha256": (
                expected_initial_trainable_sha256
            ),
            "forward_count": 0,
            "backward_count": 0,
            "optimizer_constructed": False,
            "optimizer_step_count": 0,
            "training_execution_count": 0,
            "model_unloaded": True,
        }
        observed_result = {
            key: result.get(key)
            for key in expected_result
        }
        if observed_result != expected_result:
            raise HandoffError(
                "SMOKE_RESULT_CONTRACT_MISMATCH:"
                + repr(observed_result)
                + ":"
                + repr(expected_result)
            )

        if started.get("terminal_status") != "STARTED":
            raise HandoffError("SMOKE_STARTED_RECEIPT_STATUS_CHANGED")
        if terminal.get("terminal_status") != "ACCEPTED":
            raise HandoffError("SMOKE_TERMINAL_RECEIPT_NOT_ACCEPTED")
        if terminal.get("model_training_executed") is not False:
            raise HandoffError("SMOKE_TERMINAL_RECEIPT_CLAIMS_TRAINING")
        if terminal.get("model_training_execution_status") != "NOT_EXECUTED":
            raise HandoffError("SMOKE_TERMINAL_TRAINING_STATUS_CHANGED")
        if terminal.get("started_from_receipt_sha256") != (
            started.get("stage_receipt_sha256")
        ):
            raise HandoffError("SMOKE_RECEIPT_CHAIN_BROKEN")
        if terminal.get("output_artifact_index_sha256") != (
            output_index.get("artifact_index_sha256")
        ):
            raise HandoffError("SMOKE_OUTPUT_INDEX_BINDING_BROKEN")
        if review.get("terminal_stage_receipt_sha256") != (
            terminal.get("stage_receipt_sha256")
        ):
            raise HandoffError("SMOKE_REVIEW_TERMINAL_RECEIPT_BINDING_BROKEN")
        if review.get("smoke_result_domain_sha256") != (
            result.get("result_sha256")
        ):
            raise HandoffError("SMOKE_REVIEW_RESULT_BINDING_BROKEN")

        return {
            "bundle_sha256": sha256_file(bundle_path),
            "review_manifest": review,
            "binding": binding,
            "authorization": authorization,
            "input_index": input_index,
            "output_index": output_index,
            "smoke_result": result,
            "started_receipt": started,
            "terminal_receipt": terminal,
            "member_names": sorted(names),
        }
