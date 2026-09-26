from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


QUARANTINE_SOURCE_CONTINUE_UNRELATED = (
    "QUARANTINE_SOURCE_CONTINUE_UNRELATED"
)
GLOBAL_INFRASTRUCTURE_FAIL_CLOSED = (
    "GLOBAL_INFRASTRUCTURE_FAIL_CLOSED"
)
UNREGISTERED_HARD_STOP_FAIL_CLOSED = (
    "UNREGISTERED_HARD_STOP_FAIL_CLOSED"
)


def _obj(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def _attempt_path(call_dir: Path, logical: Mapping[str, object]) -> Path:
    contributing = logical.get("contributing_attempt_id")
    if not isinstance(contributing, str) or ":" not in contributing:
        raise ValueError("logical call lacks contributing attempt identity")
    try:
        index = int(contributing.rsplit(":", 1)[1])
    except ValueError as error:
        raise ValueError("invalid contributing attempt identity") from error
    path = call_dir / f"attempt_{index:03d}.json"
    if not path.is_file():
        raise ValueError("contributing attempt receipt missing")
    return path


def load_terminal_receipts(
    call_dir: Path,
) -> dict[str, object]:
    logical_path = call_dir / "logical_call.json"
    method_path = call_dir / "method_result.json"
    if not logical_path.is_file() or not method_path.is_file():
        raise ValueError("terminal logical call receipts incomplete")
    logical = _obj(logical_path)
    method = _obj(method_path)
    attempt = _obj(_attempt_path(call_dir, logical))
    return {
        "logical": logical,
        "method": method,
        "attempt": attempt,
        "raw_response_exists": (call_dir / "raw_response.json").exists(),
        "validated_artifact_exists": (
            call_dir / "validated_artifact.json"
        ).exists(),
    }


def classify_hard_stop(
    *,
    row: Mapping[str, object],
    call_dir: Path,
) -> dict[str, object]:
    if row.get("hard_stop") is not True:
        raise ValueError("classify_hard_stop requires hard_stop=true")
    receipts = load_terminal_receipts(call_dir)
    logical = receipts["logical"]
    method = receipts["method"]
    attempt = receipts["attempt"]

    ambiguous = (
        row.get("status") == "AMBIGUOUS_POST_SEND"
        and logical.get("terminal_method_status")
        == "AMBIGUOUS_POST_SEND"
        and attempt.get("terminal_attempt_status")
        == "AMBIGUOUS_POST_SEND"
        and attempt.get("bytes_transmission_state")
        == "MAY_HAVE_BEEN_SENT"
        and attempt.get("retry_class") == "NO_RETRY"
        and attempt.get("retry_authority")
        == "FROZEN_RUNTIME_POLICY"
        and attempt.get("provider_response_id") is None
        and method.get("status") == "AMBIGUOUS_POST_SEND"
        and method.get("hard_stop") is True
        and not receipts["raw_response_exists"]
        and not receipts["validated_artifact_exists"]
    )
    if ambiguous:
        return {
            "route": QUARANTINE_SOURCE_CONTINUE_UNRELATED,
            "failure_class": method.get("failure_class"),
            "same_logical_call_resend_authorized": False,
            "human_scientific_decision_required": False,
        }

    failure_class = str(method.get("failure_class") or "")
    global_infra = {
        "AUTH_OR_CONFIGURATION_INVALID",
        "RUNTIME_ADAPTER_DEFECT",
        "PRE_SEND_INFRASTRUCTURE_UNAVAILABLE",
        "PROVIDER_TRANSIENT_UNAVAILABLE",
    }
    if failure_class in global_infra:
        return {
            "route": GLOBAL_INFRASTRUCTURE_FAIL_CLOSED,
            "failure_class": failure_class,
            "same_logical_call_resend_authorized": False,
            "human_scientific_decision_required": False,
        }

    return {
        "route": UNREGISTERED_HARD_STOP_FAIL_CLOSED,
        "failure_class": failure_class,
        "same_logical_call_resend_authorized": False,
        "human_scientific_decision_required": False,
    }
