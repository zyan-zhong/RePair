from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.identity_review import (
    _is_sha256_text,
    _historical_training_identity_candidates,
)


def test_sha256_field_is_not_chat_template_content() -> None:
    value = "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"
    assert _is_sha256_text(value) is True


def test_historical_training_authority_recovers_model_tokenizer_and_chat(
    tmp_path: Path,
) -> None:
    root = tmp_path / "materialization"
    provenance = root / "provenance"
    provenance.mkdir(parents=True)

    chat = provenance / "chat_template.jinja"
    chat.write_text("{{ messages }}", encoding="utf-8")

    import hashlib
    chat_sha = hashlib.sha256(chat.read_bytes()).hexdigest()

    model_manifest = provenance / "model_artifact_manifest.json"
    model_manifest.write_text(
        (
            '{"repository_id":"Qwen/Qwen2.5-3B-Instruct",'
            '"snapshot_revision":"aa8e72537993ba99e69dfaafa59ed015b17504d1",'
            '"tokenizer_bundle_sha256":"' + "8" * 64 + '",'
            '"weights_bundle_sha256":"' + "9" * 64 + '",'
            '"files":{"tokenizer.json":{"sha256":"' + "1" * 64 + '"}}}\n'
        ),
        encoding="utf-8",
    )

    final = root / "final_materialization_manifest.json"
    final.write_text(
        (
            '{"base_model_repository":"Qwen/Qwen2.5-3B-Instruct",'
            '"base_model_revision":"aa8e72537993ba99e69dfaafa59ed015b17504d1",'
            '"tokenizer_bundle_sha256":"' + "8" * 64 + '",'
            '"chat_template_sha256":"' + chat_sha + '"}\n'
        ),
        encoding="utf-8",
    )

    artifacts = {
        name: []
        for name in (
            "base_model_artifact",
            "adapter_artifact",
            "tokenizer_artifact",
            "chat_template",
            "policy_runtime_manifest",
            "decoding_contract",
            "raw_policy_prompt_protocol",
            "training_config",
            "training_data_manifest",
            "reference_evaluation_manifest",
        )
    }
    scalars = {
        name: set()
        for name in (
            "base_model_id",
            "adapter_id",
            "tokenizer_identity",
            "runtime_core_commit",
            "evaluator_commit",
            "training_seed",
        )
    }

    _historical_training_identity_candidates(
        training_materialization_root=root,
        artifact_candidates=artifacts,
        scalar_candidates=scalars,
    )

    assert len(artifacts["base_model_artifact"]) == 1
    assert len(artifacts["tokenizer_artifact"]) == 1
    assert len(artifacts["chat_template"]) == 1
    assert scalars["base_model_id"] == {
        "Qwen/Qwen2.5-3B-Instruct@aa8e72537993ba99e69dfaafa59ed015b17504d1"
    }
    assert scalars["tokenizer_identity"] == {
        "Qwen/Qwen2.5-3B-Instruct@aa8e72537993ba99e69dfaafa59ed015b17504d1"
        "#tokenizer_bundle_sha256=" + "8" * 64
    }
