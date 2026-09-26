from pathlib import Path

import pytest

import pchsi.cognitive_runtime.orchestrator as orchestrator
from pchsi.cognitive_runtime.p2_bridge import (
    P2TransportError,
    P2TransportResult,
)


def _prepare(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "validate_task_access",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "render_stage_request",
        lambda **kwargs: {
            "provider_request": {"model": "test"},
            "request_body_sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "load_runtime_manifest",
        lambda: {"runtime_manifest_sha256": "b" * 64},
    )
    monkeypatch.setattr(
        orchestrator,
        "parse_provider_response",
        lambda raw: {"ok": True},
    )
    monkeypatch.setattr(
        orchestrator,
        "usage_summary",
        lambda response: {
            "provider_response_id": "resp",
            "returned_model": "test",
            "response_created_at": 1,
            "status": "completed",
            "service_tier": "default",
            "input_tokens": 1,
            "output_tokens": 1,
            "reasoning_tokens": 0,
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "extract_output_text",
        lambda response: "{}",
    )
    monkeypatch.setattr(
        orchestrator,
        "validate_stage_output",
        lambda **kwargs: {"ok": True},
    )
    monkeypatch.setattr(
        orchestrator,
        "validated_artifact_identity",
        lambda **kwargs: "c" * 64,
    )


def _infra_error():
    return P2TransportError(
        "temporary",
        failure_class="PRE_SEND_INFRASTRUCTURE_UNAVAILABLE",
        bytes_transmission_state="NOT_SENT",
        retry_class="SAFE_PRE_SEND",
        retry_authority="FROZEN_RUNTIME_POLICY",
        terminal_attempt_status="INFRASTRUCTURE_ERROR",
        logical_method_status="INFRASTRUCTURE_UNAVAILABLE",
        counts_as_method_failure=False,
        hard_stop=False,
    )


def test_safe_pre_send_retry_succeeds_without_new_logical_call(
    monkeypatch, tmp_path: Path
):
    _prepare(monkeypatch)
    calls = {"n": 0}

    def fake(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _infra_error()
        return P2TransportResult(
            http_status=200,
            response_headers={"x-request-id": "req"},
            raw_response=b"{}",
            provider_http_request_id="req",
        )

    monkeypatch.setattr(
        orchestrator,
        "execute_via_existing_p2",
        fake,
    )
    result = orchestrator.execute_one(
        output_root=tmp_path,
        unit_identity={
            "identity_sha256": "d" * 64,
            "scientific_unit_id": "u",
        },
        stage_id="L-A0",
        condition_id="A0",
        round_id="r",
        policy_version="p",
        projection={},
        task_access={},
        max_infrastructure_attempt_restarts=1,
    )
    assert result["status"] == "ACCEPTED"
    assert result["transport_attempt_count"] == 2
    call = Path(result["call_dir"])
    assert (call / "attempt_000.json").is_file()
    assert (call / "attempt_001.json").is_file()
    assert (call / "logical_call.json").is_file()


def test_retry_budget_exhaustion_becomes_global_hard_stop(
    monkeypatch, tmp_path: Path
):
    _prepare(monkeypatch)
    monkeypatch.setattr(
        orchestrator,
        "execute_via_existing_p2",
        lambda *args, **kwargs: (_ for _ in ()).throw(_infra_error()),
    )
    result = orchestrator.execute_one(
        output_root=tmp_path,
        unit_identity={
            "identity_sha256": "e" * 64,
            "scientific_unit_id": "u",
        },
        stage_id="L-A0",
        condition_id="A0",
        round_id="r",
        policy_version="p",
        projection={},
        task_access={},
        max_infrastructure_attempt_restarts=1,
    )
    assert result["status"] == "INFRASTRUCTURE_UNAVAILABLE"
    assert result["hard_stop"] is True
    assert result["transport_attempt_count"] == 2
