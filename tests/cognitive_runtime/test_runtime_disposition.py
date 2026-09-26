import json
from pathlib import Path

from pchsi.cognitive_runtime.runtime_disposition import (
    GLOBAL_INFRASTRUCTURE_FAIL_CLOSED,
    QUARANTINE_SOURCE_CONTINUE_UNRELATED,
    classify_hard_stop,
)


def _write(path: Path, value: dict):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_ambiguous_post_send_is_source_local_quarantine(tmp_path: Path):
    call = tmp_path / "call"
    call.mkdir()
    _write(
        call / "logical_call.json",
        {
            "terminal_method_status": "AMBIGUOUS_POST_SEND",
            "contributing_attempt_id": "logical:0",
        },
    )
    _write(
        call / "attempt_000.json",
        {
            "terminal_attempt_status": "AMBIGUOUS_POST_SEND",
            "bytes_transmission_state": "MAY_HAVE_BEEN_SENT",
            "retry_class": "NO_RETRY",
            "retry_authority": "FROZEN_RUNTIME_POLICY",
            "provider_response_id": None,
        },
    )
    _write(
        call / "method_result.json",
        {
            "status": "AMBIGUOUS_POST_SEND",
            "failure_class": "AMBIGUOUS_POST_SEND",
            "hard_stop": True,
        },
    )
    route = classify_hard_stop(
        row={"status": "AMBIGUOUS_POST_SEND", "hard_stop": True},
        call_dir=call,
    )
    assert route["route"] == QUARANTINE_SOURCE_CONTINUE_UNRELATED
    assert route["same_logical_call_resend_authorized"] is False


def test_exhausted_safe_infrastructure_is_global_terminal(tmp_path: Path):
    call = tmp_path / "call"
    call.mkdir()
    _write(
        call / "logical_call.json",
        {
            "terminal_method_status": "INFRASTRUCTURE_UNAVAILABLE",
            "contributing_attempt_id": "logical:1",
        },
    )
    _write(
        call / "attempt_001.json",
        {
            "terminal_attempt_status": "INFRASTRUCTURE_ERROR",
            "bytes_transmission_state": "NOT_SENT",
            "retry_class": "SAFE_PRE_SEND",
            "retry_authority": "FROZEN_RUNTIME_POLICY",
            "provider_response_id": None,
        },
    )
    _write(
        call / "method_result.json",
        {
            "status": "INFRASTRUCTURE_UNAVAILABLE",
            "failure_class": "PRE_SEND_INFRASTRUCTURE_UNAVAILABLE",
            "hard_stop": True,
        },
    )
    route = classify_hard_stop(
        row={"status": "INFRASTRUCTURE_UNAVAILABLE", "hard_stop": True},
        call_dir=call,
    )
    assert route["route"] == GLOBAL_INFRASTRUCTURE_FAIL_CLOSED
