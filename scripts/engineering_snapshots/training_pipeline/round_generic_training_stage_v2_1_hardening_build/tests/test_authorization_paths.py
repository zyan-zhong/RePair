from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from round_training.common import ContractError, domain_sha256
from round_training.contracts import load_execution_authorization


def write_authorization(
    path: Path,
    *,
    output_dir: Path,
    attempt_root: Path,
    attempt_id: str = "attempt-001",
) -> None:
    value = {
        "schema_id": "ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1",
        "schema_version": 1,
        "authorization_status": "APPROVED",
        "round_id": "R7",
        "stage_id": "TRAINING_EXECUTION",
        "profile_id": "P7",
        "stage_binding_sha256": "3" * 64,
        "runner_freeze_root_sha256": "4" * 64,
        "execution_attempt_id": attempt_id,
        "authorized_output_dir": str(output_dir),
        "stage_attempt_root": str(attempt_root),
        "authorized_optimizer_steps": 3,
        "authorized_target_loss_tokens": 151,
        "diagnostic_only": True,
        "promotion_eligible": False,
        "training_execution_count_before": 0,
        "authorization_sha256": "",
    }
    value["authorization_sha256"] = domain_sha256(
        value["schema_id"],
        value,
        sha_field="authorization_sha256",
    )
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def context(tmp_path: Path):
    return SimpleNamespace(
        binding={
            "round_id": "R7",
            "stage_id": "TRAINING_EXECUTION",
            "profile_id": "P7",
            "stage_binding_sha256": "3" * 64,
            "output_policy": {
                "require_direct_child": True,
                "require_basename_equals_execution_attempt_id": True,
                "training_output_parent": str(tmp_path / "outputs"),
                "stage_attempt_parent": str(tmp_path / "attempts"),
            },
        },
        training_contract={
            "budget": {
                "optimizer_steps": 3,
                "target_loss_token_budget": 151,
            },
            "diagnostic_only": True,
            "promotion_eligible": False,
        },
    )


def test_authorized_paths_must_match_round_derived_policy(
    tmp_path,
) -> None:
    authorization_path = tmp_path / "authorization.json"
    write_authorization(
        authorization_path,
        output_dir=tmp_path / "outputs" / "attempt-001",
        attempt_root=tmp_path / "attempts" / "attempt-001",
    )
    value = load_execution_authorization(
        authorization_path,
        context=context(tmp_path),
        runner_freeze_root_sha256="4" * 64,
    )
    assert value["execution_attempt_id"] == "attempt-001"


def test_authorized_output_parent_mismatch_is_rejected(
    tmp_path,
) -> None:
    authorization_path = tmp_path / "authorization.json"
    write_authorization(
        authorization_path,
        output_dir=tmp_path / "wrong" / "attempt-001",
        attempt_root=tmp_path / "attempts" / "attempt-001",
    )
    with pytest.raises(
        ContractError,
        match="AUTHORIZED_OUTPUT_PARENT_MISMATCH",
    ):
        load_execution_authorization(
            authorization_path,
            context=context(tmp_path),
            runner_freeze_root_sha256="4" * 64,
        )


def test_authorized_attempt_basename_mismatch_is_rejected(
    tmp_path,
) -> None:
    authorization_path = tmp_path / "authorization.json"
    write_authorization(
        authorization_path,
        output_dir=tmp_path / "outputs" / "wrong-name",
        attempt_root=tmp_path / "attempts" / "wrong-name",
        attempt_id="attempt-001",
    )
    with pytest.raises(
        ContractError,
        match="AUTHORIZED_OUTPUT_BASENAME_MISMATCH",
    ):
        load_execution_authorization(
            authorization_path,
            context=context(tmp_path),
            runner_freeze_root_sha256="4" * 64,
        )
