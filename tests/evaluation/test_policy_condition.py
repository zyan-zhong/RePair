from dataclasses import FrozenInstanceError

import pytest

from pchsi.evaluation.policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
    TrainingMethod,
)
from pchsi.evaluation.schema_contract import load_schema


def pi0():
    return PolicyConditionManifestV1(
        schema_id=PolicyConditionManifestV1.SCHEMA_ID,
        schema_version=1,
        policy_condition_id="P4-R0-PI0",
        base_model_repository="Qwen/Qwen2.5-3B-Instruct",
        base_model_revision="a" * 40,
        checkpoint_kind=CheckpointKind.BASE_MODEL,
        checkpoint_path=None,
        checkpoint_sha256=None,
        training_method=TrainingMethod.NONE,
        training_run_id=None,
        training_config_sha256=None,
        policy_runtime_manifest_sha256="b" * 64,
        tokenizer_identity_manifest_sha256="c" * 64,
        chat_template_sha256="d" * 64,
        served_model_name="Qwen2.5-3B-Instruct-E1",
        policy_version="pi0",
        memory_version="MEMORY_M0_V1",
        raw_protocol_sha256="e" * 64,
        runtime_core_commit="f" * 40,
        evaluator_commit="1" * 40,
    )


def test_schema_is_registered():
    assert load_schema(
        "POLICY_CONDITION_MANIFEST_V1"
    )["$id"] == "POLICY_CONDITION_MANIFEST_V1"


def test_pi0_round_trip():
    condition = pi0()
    assert PolicyConditionManifestV1.from_json(
        condition.to_json()
    ) == condition


def test_condition_is_frozen():
    condition = pi0()
    with pytest.raises(FrozenInstanceError):
        condition.policy_version = "x"  # type: ignore[misc]


def test_base_model_forbids_training_artifacts():
    payload = pi0().to_dict()
    payload["training_run_id"] = "unexpected"
    with pytest.raises(ValueError, match="BASE_MODEL"):
        PolicyConditionManifestV1.from_dict(payload)


def test_sft_requires_checkpoint_and_training_identity():
    payload = pi0().to_dict()
    payload.update(
        {
            "policy_condition_id": "P4-R1-Q2-BAD-TRAIN17",
            "checkpoint_kind": "LORA_ADAPTER",
            "training_method": "SFT",
            "policy_version": "pi1-bad",
            "served_model_name": "P4-R1-Q2-BAD-TRAIN17",
        }
    )
    with pytest.raises(ValueError, match="SFT"):
        PolicyConditionManifestV1.from_dict(payload)


def test_trained_condition_cannot_reuse_pi0_name():
    payload = pi0().to_dict()
    payload.update(
        {
            "policy_condition_id": "P4-R1-Q2-BAD-TRAIN17",
            "checkpoint_kind": "LORA_ADAPTER",
            "checkpoint_path": "/models/pi1/adapter",
            "checkpoint_sha256": "2" * 64,
            "training_method": "SFT",
            "training_run_id": "train17",
            "training_config_sha256": "3" * 64,
            "policy_version": "pi1-bad",
        }
    )
    with pytest.raises(ValueError, match="served_model_name"):
        PolicyConditionManifestV1.from_dict(payload)


def test_valid_trained_condition_round_trip():
    payload = pi0().to_dict()
    payload.update(
        {
            "policy_condition_id": "P4-R1-Q2-BAD-TRAIN17",
            "checkpoint_kind": "LORA_ADAPTER",
            "checkpoint_path": "/models/pi1/adapter",
            "checkpoint_sha256": "2" * 64,
            "training_method": "SFT",
            "training_run_id": "train17",
            "training_config_sha256": "3" * 64,
            "policy_version": "pi1-bad",
            "served_model_name": "P4-R1-Q2-BAD-TRAIN17",
        }
    )
    observed = PolicyConditionManifestV1.from_dict(payload)
    assert PolicyConditionManifestV1.from_json(
        observed.to_json()
    ) == observed



def test_pi0_condition_rejects_trained_checkpoint_identity_reuse() -> None:
    payload = pi0().to_dict()
    payload.update(
        {
            "checkpoint_kind": "LORA_ADAPTER",
            "checkpoint_path": "/models/pi1/adapter",
            "checkpoint_sha256": "2" * 64,
            "training_method": "SFT",
            "training_run_id": "train17",
            "training_config_sha256": "3" * 64,
            "policy_version": "pi1-bad",
            "served_model_name": "P4-R1-Q2-BAD-TRAIN17",
        }
    )

    with pytest.raises(ValueError, match="P4-R0-PI0"):
        PolicyConditionManifestV1.from_dict(payload)


def test_pi0_condition_requires_frozen_m0_identity() -> None:
    payload = pi0().to_dict()
    payload["memory_version"] = "MEMORY_M1_EXPERIMENTAL"

    with pytest.raises(ValueError, match="MEMORY_M0_V1"):
        PolicyConditionManifestV1.from_dict(payload)



def test_pi0_condition_requires_policy_version_pi0() -> None:
    payload = pi0().to_dict()
    payload["policy_version"] = "pi0-mutated"

    with pytest.raises(ValueError, match="policy_version pi0"):
        PolicyConditionManifestV1.from_dict(payload)


def test_pi0_condition_requires_canonical_served_model_name() -> None:
    payload = pi0().to_dict()
    payload["served_model_name"] = "wrong-pi0-service"

    with pytest.raises(ValueError, match="frozen pi0 served_model_name"):
        PolicyConditionManifestV1.from_dict(payload)
