from __future__ import annotations

import json
from pathlib import Path

import pchsi.cognitive_runtime.registry_runner as runner


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _registry(tmp_path: Path, count: int = 4) -> Path:
    units = []
    for i in range(count):
        _write(
            tmp_path / f"id{i}.json",
            {
                "scientific_unit_id": f"unit:{i}",
                "identity_sha256": f"{i+1:064x}",
            },
        )
        _write(tmp_path / f"projection{i}.json", {})
        _write(tmp_path / f"access{i}.json", {})
        units.append(
            {
                "source_unit_id": "source-1" if i < 2 else "source-2",
                "scientific_unit_identity_path": f"id{i}.json",
                "stage_id": "L-A0" if i % 2 == 0 else "L-A1",
                "condition_id": "A0" if i % 2 == 0 else "A1",
                "input_projection_path": f"projection{i}.json",
                "task_access_record_path": f"access{i}.json",
                "expected_common_evidence_sha256": None,
                "expected_a1_local_result_sha256": None,
                "expected_memory_pack_sha256": None,
            }
        )
    path = tmp_path / "registry.json"
    _write(
        path,
        {
            "schema_id": "RUNTIME_INPUT_REGISTRY_V1",
            "schema_version": 1,
            "registry_role": "ACT2_LOCAL_PILOT",
            "round_id": "r",
            "policy_version": "p",
            "task_access_manifest_sha256": "a" * 64,
            "units": units,
            "registry_sha256": "b" * 64,
        },
    )
    return path


def test_quarantined_source_does_not_block_unrelated_units(
    monkeypatch, tmp_path: Path
):
    registry = _registry(tmp_path)
    monkeypatch.setattr(runner, "validate_artifact", lambda *args: None)
    monkeypatch.setattr(
        runner,
        "_logical_id",
        lambda **kwargs: kwargs["identity"]["scientific_unit_id"],
    )
    calls = []

    def fake_execute_one(**kwargs):
        calls.append(kwargs["unit_identity"]["scientific_unit_id"])
        if len(calls) == 1:
            call = kwargs["output_root"] / calls[-1]
            call.mkdir()
            _write(
                call / "logical_call.json",
                {
                    "terminal_method_status": "AMBIGUOUS_POST_SEND",
                    "contributing_attempt_id": calls[-1] + ":0",
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
            return {
                "logical_call_id": calls[-1],
                "call_dir": str(call),
                "status": "AMBIGUOUS_POST_SEND",
                "method_failure_reason": "AMBIGUOUS_POST_SEND",
                "hard_stop": True,
            }
        call = kwargs["output_root"] / calls[-1]
        call.mkdir()
        _write(
            call / "logical_call.json",
            {
                "terminal_method_status": "ACCEPTED",
                "contributing_attempt_id": calls[-1] + ":0",
            },
        )
        _write(call / "attempt_000.json", {"transport_attempt_id": calls[-1]+":0"})
        _write(
            call / "method_result.json",
            {"status": "ACCEPTED", "failure_class": None, "hard_stop": False},
        )
        return {
            "logical_call_id": calls[-1],
            "call_dir": str(call),
            "status": "ACCEPTED",
            "method_failure_reason": None,
            "hard_stop": False,
        }

    monkeypatch.setattr(runner, "execute_one", fake_execute_one)
    manifest, rc = runner.run_registry(
        registry_path=registry,
        output_root=tmp_path / "out",
    )
    assert rc == 0
    assert calls == ["unit:0", "unit:2", "unit:3"]
    assert manifest["quarantined_source_ids"] == ["source-1"]
    skipped = [
        row for row in manifest["rows"]
        if row["status"] == "QUARANTINED_SOURCE_SKIPPED"
    ]
    assert len(skipped) == 1


def test_existing_terminal_is_adopted_and_not_resent(monkeypatch, tmp_path: Path):
    registry = _registry(tmp_path, count=1)
    monkeypatch.setattr(runner, "validate_artifact", lambda *args: None)
    monkeypatch.setattr(
        runner,
        "_logical_id",
        lambda **kwargs: "terminal-call",
    )
    out = tmp_path / "out"
    call = out / "terminal-call"
    call.mkdir(parents=True)
    _write(
        call / "logical_call.json",
        {
            "logical_call_id": "terminal-call",
            "terminal_method_status": "ACCEPTED",
            "contributing_attempt_id": "terminal-call:0",
        },
    )
    _write(
        call / "method_result.json",
        {"status": "ACCEPTED", "failure_class": None, "hard_stop": False},
    )
    _write(
        call / "attempt_000.json",
        {"transport_attempt_id": "terminal-call:0"},
    )
    monkeypatch.setattr(
        runner,
        "execute_one",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("terminal call must not be resent")
        ),
    )
    manifest, rc = runner.run_registry(
        registry_path=registry,
        output_root=out,
    )
    assert rc == 0
    assert manifest["rows"][0]["reused_terminal"] is True


def test_partial_logical_call_fails_closed(monkeypatch, tmp_path: Path):
    registry = _registry(tmp_path, count=1)
    monkeypatch.setattr(runner, "validate_artifact", lambda *args: None)
    monkeypatch.setattr(
        runner,
        "_logical_id",
        lambda **kwargs: "partial-call",
    )
    out = tmp_path / "out"
    call = out / "partial-call"
    call.mkdir(parents=True)
    _write(call / "attempt_000.json", {"x": 1})
    import pytest
    with pytest.raises(RuntimeError, match="PARTIAL_LOGICAL_CALL_FAIL_CLOSED"):
        runner.run_registry(
            registry_path=registry,
            output_root=out,
        )
