from pchsi.evaluation.policy_condition import (
    CheckpointKind,
    PolicyConditionManifestV1,
    TrainingMethod,
)

def test_pi0_condition_accepts_frozen_e1_served_model_name() -> None:
    condition = PolicyConditionManifestV1(
        schema_id="POLICY_CONDITION_MANIFEST_V1",
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
    assert condition.served_model_name == "Qwen2.5-3B-Instruct-E1"
