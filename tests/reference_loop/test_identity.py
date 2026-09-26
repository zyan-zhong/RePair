from __future__ import annotations

from pathlib import Path

import pytest

from pchsi.reference_loop.canonical import (
    canonical_json_bytes,
    directory_manifest_sha256,
    sha256_file,
)
from pchsi.reference_loop.identity import (
    Pi1IdentitySourceRegistrationV1,
    build_registration_payload,
    materialize_pi1_reference_identity,
)


def _identity_fixture(tmp_path: Path):
    base = tmp_path / "base"
    adapter = tmp_path / "adapter"
    tokenizer = tmp_path / "tokenizer"
    for root, name in (
        (base, "model.bin"),
        (adapter, "adapter.bin"),
        (tokenizer, "tokenizer.json"),
    ):
        root.mkdir()
        (root / name).write_text(name, encoding="utf-8")

    adapter_sha = directory_manifest_sha256(adapter)
    runtime = tmp_path / "runtime.json"
    runtime.write_bytes(
        canonical_json_bytes(
            {
                "schema_id": "SELECT_SERVER_RUNTIME_MANIFEST_V1",
                "lora_registrations": [
                    {
                        "logical_condition_id": "P4-R1-Q2-BAD",
                        "checkpoint_instance_id": "P4-R1-Q2-BAD-TRAIN17",
                        "training_seed": 17,
                        "adapter_bundle_sha256": adapter_sha,
                    }
                ],
            }
        )
    )

    files = {}
    for name in (
        "chat_template",
        "decoding_contract",
        "raw_policy_prompt_protocol",
        "training_config",
        "training_data_manifest",
        "reference_evaluation_manifest",
    ):
        path = tmp_path / f"{name}.json"
        path.write_bytes(canonical_json_bytes({"name": name}))
        files[name] = path

    registrations = [
        {
            "name": "base_model_artifact",
            "kind": "DIRECTORY_MANIFEST",
            "path": str(base),
            "expected_sha256": directory_manifest_sha256(base),
        },
        {
            "name": "adapter_artifact",
            "kind": "DIRECTORY_MANIFEST",
            "path": str(adapter),
            "expected_sha256": adapter_sha,
        },
        {
            "name": "tokenizer_artifact",
            "kind": "DIRECTORY_MANIFEST",
            "path": str(tokenizer),
            "expected_sha256": directory_manifest_sha256(tokenizer),
        },
        {
            "name": "chat_template",
            "kind": "FILE",
            "path": str(files["chat_template"]),
            "expected_sha256": sha256_file(files["chat_template"]),
        },
        {
            "name": "policy_runtime_manifest",
            "kind": "FILE",
            "path": str(runtime),
            "expected_sha256": sha256_file(runtime),
        },
        {
            "name": "decoding_contract",
            "kind": "FILE",
            "path": str(files["decoding_contract"]),
            "expected_sha256": sha256_file(files["decoding_contract"]),
        },
        {
            "name": "raw_policy_prompt_protocol",
            "kind": "FILE",
            "path": str(files["raw_policy_prompt_protocol"]),
            "expected_sha256": sha256_file(
                files["raw_policy_prompt_protocol"]
            ),
        },
        {
            "name": "training_config",
            "kind": "FILE",
            "path": str(files["training_config"]),
            "expected_sha256": sha256_file(files["training_config"]),
        },
        {
            "name": "training_data_manifest",
            "kind": "FILE",
            "path": str(files["training_data_manifest"]),
            "expected_sha256": sha256_file(
                files["training_data_manifest"]
            ),
        },
        {
            "name": "reference_evaluation_manifest",
            "kind": "FILE",
            "path": str(files["reference_evaluation_manifest"]),
            "expected_sha256": sha256_file(
                files["reference_evaluation_manifest"]
            ),
        },
    ]
    payload = build_registration_payload(
        logical_policy_id="P4-R1-Q2-BAD",
        checkpoint_instance_id="P4-R1-Q2-BAD-TRAIN17",
        base_model_id="Qwen/Qwen2.5-3B-Instruct@revision",
        adapter_id="train17-lora",
        tokenizer_identity="qwen-tokenizer",
        runtime_core_commit="runtime",
        evaluator_commit="evaluator",
        training_seed=17,
        artifact_registrations=registrations,
    )
    return Pi1IdentitySourceRegistrationV1.from_dict(payload), adapter


def test_identity_materialization_binds_exact_artifacts(tmp_path: Path) -> None:
    registration, _ = _identity_fixture(tmp_path)
    identity = materialize_pi1_reference_identity(registration)

    assert identity["logical_policy_id"] == "P4-R1-Q2-BAD"
    assert identity["checkpoint_instance_id"] == "P4-R1-Q2-BAD-TRAIN17"
    assert identity["training_seed"] == 17
    assert len(identity["identity_sha256"]) == 64


def test_identity_materialization_rejects_artifact_tampering(
    tmp_path: Path,
) -> None:
    registration, adapter = _identity_fixture(tmp_path)
    (adapter / "adapter.bin").write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA mismatch"):
        materialize_pi1_reference_identity(registration)


def test_identity_materialization_rejects_symlinked_artifact(
    tmp_path: Path,
) -> None:
    registration, adapter = _identity_fixture(tmp_path)
    original = adapter / "adapter.bin"
    target = tmp_path / "target.bin"
    target.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")
    original.unlink()
    original.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        materialize_pi1_reference_identity(registration)
