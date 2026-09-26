from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import round_training.stage_runner as stage_runner


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        binding={
            "round_id": "R7",
            "stage_id": "TRAINING_EXECUTION",
            "profile_id": "P7",
            "previous_stage_receipt_sha256": None,
        },
        training_contract={
            "execution": {
                "ambient_environment_variables_forbidden": [],
            },
        },
    )


def _authorization(output_dir: Path, attempt_root: Path) -> dict:
    return {
        "authorized_output_dir": str(output_dir),
        "stage_attempt_root": str(attempt_root),
        "execution_attempt_id": "attempt-001",
        "authorization_sha256": "1" * 64,
    }


def _install_common_monkeypatches(
    monkeypatch,
    *,
    context,
    output_dir: Path,
    attempt_root: Path,
) -> None:
    monkeypatch.setattr(
        stage_runner,
        "load_stage_context",
        lambda path: context,
    )
    monkeypatch.setattr(
        stage_runner,
        "reject_ambient_environment",
        lambda value: None,
    )
    monkeypatch.setattr(
        stage_runner,
        "load_execution_authorization",
        lambda *args, **kwargs: _authorization(
            output_dir,
            attempt_root,
        ),
    )


def test_input_ref_preflight_failure_leaves_no_attempt_root(
    tmp_path,
    monkeypatch,
) -> None:
    attempt_root = tmp_path / "attempts" / "attempt-001"
    output_dir = tmp_path / "outputs" / "attempt-001"
    context = _context()
    _install_common_monkeypatches(
        monkeypatch,
        context=context,
        output_dir=output_dir,
        attempt_root=attempt_root,
    )

    def fail_input_refs(value, adapter):
        raise RuntimeError("input-ref preflight failed")

    class Adapter:
        @staticmethod
        def validate_profile_without_model_load(value):
            return {"status": "PASS"}

        @staticmethod
        def input_artifact_refs(value):
            return []

        @staticmethod
        def execute_training_stage(**kwargs):
            raise AssertionError("execute should not be reached")

    monkeypatch.setattr(
        stage_runner,
        "_load_runtime_adapter",
        lambda value: Adapter,
    )
    monkeypatch.setattr(
        stage_runner,
        "_input_refs",
        fail_input_refs,
    )

    with pytest.raises(
        RuntimeError,
        match="input-ref preflight failed",
    ):
        stage_runner.run_training_stage(
            binding_path=tmp_path / "binding.json",
            authorization_path=tmp_path / "authorization.json",
            runner_freeze_root_sha256="2" * 64,
        )

    assert not attempt_root.exists()
    assert not output_dir.exists()


def test_adapter_preflight_failure_leaves_no_attempt_root(
    tmp_path,
    monkeypatch,
) -> None:
    attempt_root = tmp_path / "attempts" / "attempt-001"
    output_dir = tmp_path / "outputs" / "attempt-001"
    context = _context()
    _install_common_monkeypatches(
        monkeypatch,
        context=context,
        output_dir=output_dir,
        attempt_root=attempt_root,
    )
    monkeypatch.setattr(
        stage_runner,
        "_input_refs",
        lambda value, adapter: [],
    )

    class Adapter:
        @staticmethod
        def validate_profile_without_model_load(value):
            raise RuntimeError("adapter preflight failed")

    monkeypatch.setattr(
        stage_runner,
        "_load_runtime_adapter",
        lambda value: Adapter,
    )

    with pytest.raises(
        RuntimeError,
        match="adapter preflight failed",
    ):
        stage_runner.run_training_stage(
            binding_path=tmp_path / "binding.json",
            authorization_path=tmp_path / "authorization.json",
            runner_freeze_root_sha256="2" * 64,
        )

    assert not attempt_root.exists()
    assert not output_dir.exists()


def test_runtime_failure_closes_started_receipt_chain(
    tmp_path,
    monkeypatch,
) -> None:
    attempt_root = tmp_path / "attempts" / "attempt-001"
    output_dir = tmp_path / "outputs" / "attempt-001"
    context = _context()
    _install_common_monkeypatches(
        monkeypatch,
        context=context,
        output_dir=output_dir,
        attempt_root=attempt_root,
    )
    monkeypatch.setattr(
        stage_runner,
        "_input_refs",
        lambda value, adapter: [],
    )

    class Adapter:
        @staticmethod
        def validate_profile_without_model_load(value):
            return {"status": "PASS"}

        @staticmethod
        def execute_training_stage(**kwargs):
            raise RuntimeError("runtime failure")

    monkeypatch.setattr(
        stage_runner,
        "_load_runtime_adapter",
        lambda value: Adapter,
    )

    with pytest.raises(RuntimeError, match="runtime failure"):
        stage_runner.run_training_stage(
            binding_path=tmp_path / "binding.json",
            authorization_path=tmp_path / "authorization.json",
            runner_freeze_root_sha256="2" * 64,
        )

    started = json.loads(
        (attempt_root / "started_stage_receipt.json").read_text()
    )
    terminal = json.loads(
        (attempt_root / "terminal_stage_receipt.json").read_text()
    )
    assert terminal["started_from_receipt_sha256"] == started[
        "stage_receipt_sha256"
    ]
    assert terminal["scientific_missingness_class"] == (
        "UNRESOLVED_RUNTIME_FAILURE"
    )
    assert terminal["model_training_executed"] is None
    assert terminal["model_training_execution_status"] == (
        "AMBIGUOUS_AFTER_RUNTIME_ADAPTER_ENTRY"
    )
