from __future__ import annotations

from pchsi.reference_loop.identity_review import (
    _path_candidate_slots,
    _scalar_candidate_slots,
)


def test_identity_review_classifies_frozen_authority_paths() -> None:
    assert "base_model_artifact" in _path_candidate_slots(
        "$.runtime.base_model_path"
    )
    assert "tokenizer_artifact" in _path_candidate_slots(
        "$.runtime.tokenizer_path"
    )
    assert "chat_template" in _path_candidate_slots(
        "$.runtime.chat_template_path"
    )
    assert "decoding_contract" in _path_candidate_slots(
        "$.runtime.decoding_contract_path"
    )
    assert "raw_policy_prompt_protocol" in _path_candidate_slots(
        "$.runtime.raw_policy_prompt_protocol_path"
    )
    assert "training_config" in _path_candidate_slots(
        "$.training.execution_spec_path"
    )
    assert "training_data_manifest" in _path_candidate_slots(
        "$.training.training_data_manifest_path"
    )
    assert "reference_evaluation_manifest" in _path_candidate_slots(
        "$.evaluation.reference_evaluation_manifest_path"
    )


def test_identity_review_classifies_scalar_identity_fields() -> None:
    assert "base_model_id" in _scalar_candidate_slots(
        "$.runtime.base_model_id"
    )
    assert "adapter_id" in _scalar_candidate_slots(
        "$.lora.adapter_id"
    )
    assert "tokenizer_identity" in _scalar_candidate_slots(
        "$.runtime.tokenizer_identity"
    )
