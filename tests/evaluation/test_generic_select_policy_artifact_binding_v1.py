from __future__ import annotations

import pytest

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes
from pchsi.evaluation.condition_run_schedule import condition_cell_id
from pchsi.evaluation.select_execution_identity import (
    P4_SELECT_EVALUATION_CONTEXT,
    SelectExecutionIdentityV1,
    build_select_execution_profile,
)
from pchsi.evaluation.select_policy_runtime import (
    PI1_LOGICAL_CONDITION_ID,
    SelectPolicyRuntimeManifestV1,
    SelectServerRuntimeManifestV1,
    SelectStaticLoRARegistrationV1,
)

PARENT_LOGICAL = PI1_LOGICAL_CONDITION_ID
PARENT_CHECKPOINT = "P4-R1-Q2-BAD-TRAIN17"
PARENT_ADAPTER = "b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace"

CANDIDATE_LOGICAL = "P4-R2-HUMAN-T2-DIAGNOSTIC"
CANDIDATE_CHECKPOINT = "P4-R2-HUMAN-T2-DIAGNOSTIC-TRAIN17"
CANDIDATE_ADAPTER = "908acf081e80008800284653c3340c397353eef0de08ee044f06810cab2a251e"


def _registration(*, logical: str, checkpoint: str, adapter: str, seed: int = 17):
    return SelectStaticLoRARegistrationV1(
        logical_condition_id=logical,
        checkpoint_instance_id=checkpoint,
        training_seed=seed,
        served_model_name=checkpoint,
        adapter_path="/tmp/" + checkpoint,
        adapter_bundle_sha256=adapter,
        adapter_rank=16,
    )


def _server(registrations, *, max_cpu_loras: int | None = None):
    items = tuple(registrations)
    return SelectServerRuntimeManifestV1(
        schema_id="SELECT_SERVER_RUNTIME_MANIFEST_V1",
        schema_version=1,
        manifest_id="GENERIC_SELECT_SERVER_TEST",
        vllm_version="0.11.0",
        base_model_repository="Qwen/Qwen2.5-3B-Instruct",
        base_model_revision="aa8e72537993ba99e69dfaafa59ed015b17504d1",
        tokenizer_identity_manifest_sha256="d" * 64,
        chat_template_sha256="e" * 64,
        dtype="bfloat16",
        tensor_parallel_size=1,
        generation_config_mode="vllm",
        chat_template_content_format="string",
        enable_lora=True,
        max_lora_rank=16,
        max_loras=1,
        max_cpu_loras=len(items) if max_cpu_loras is None else max_cpu_loras,
        lora_dtype="auto",
        runtime_dynamic_lora_updates=False,
        static_lora_registry=items,
    )


def _candidate_identity():
    cell_id = condition_cell_id(
        policy_condition_id=CANDIDATE_CHECKPOINT,
        manifest_index=2,
        seed=17,
    )
    return SelectExecutionIdentityV1(
        evaluation_context=P4_SELECT_EVALUATION_CONTEXT,
        logical_condition_id=CANDIDATE_LOGICAL,
        checkpoint_instance_id=CANDIDATE_CHECKPOINT,
        training_seed=17,
        served_model_name=CANDIDATE_CHECKPOINT,
        adapter_bundle_sha256=CANDIDATE_ADAPTER,
        access_class="SELECT_SUMMARY_ONLY",
        policy_condition_id=CANDIDATE_CHECKPOINT,
        condition_cell_id=cell_id,
        task_access_manifest_sha256="1" * 64,
        policy_condition_manifest_sha256="2" * 64,
        condition_run_schedule_sha256="3" * 64,
        select_policy_runtime_manifest_sha256="4" * 64,
    )


def test_registry_accepts_parent_and_candidate_with_same_training_seed():
    parent = _registration(logical=PARENT_LOGICAL, checkpoint=PARENT_CHECKPOINT, adapter=PARENT_ADAPTER)
    candidate = _registration(logical=CANDIDATE_LOGICAL, checkpoint=CANDIDATE_CHECKPOINT, adapter=CANDIDATE_ADAPTER)
    server = _server((parent, candidate))
    assert len(server.static_lora_registry) == 2
    assert [x.training_seed for x in server.static_lora_registry] == [17, 17]


def test_registry_rejects_duplicate_logical_condition_and_seed():
    first = _registration(logical=CANDIDATE_LOGICAL, checkpoint=CANDIDATE_CHECKPOINT, adapter=CANDIDATE_ADAPTER)
    second = _registration(logical=CANDIDATE_LOGICAL, checkpoint=CANDIDATE_CHECKPOINT + "-ALT", adapter="9" * 64)
    with pytest.raises(ValueError, match="logical-condition/training-seed"):
        _server((first, second))


def test_server_requires_cpu_lora_capacity_for_static_registry():
    parent = _registration(logical=PARENT_LOGICAL, checkpoint=PARENT_CHECKPOINT, adapter=PARENT_ADAPTER)
    candidate = _registration(logical=CANDIDATE_LOGICAL, checkpoint=CANDIDATE_CHECKPOINT, adapter=CANDIDATE_ADAPTER)
    with pytest.raises(ValueError, match="max_cpu_loras"):
        _server((parent, candidate), max_cpu_loras=1)


def test_candidate_policy_runtime_accepts_generic_trained_logical_condition():
    parent = _registration(logical=PARENT_LOGICAL, checkpoint=PARENT_CHECKPOINT, adapter=PARENT_ADAPTER)
    candidate = _registration(logical=CANDIDATE_LOGICAL, checkpoint=CANDIDATE_CHECKPOINT, adapter=CANDIDATE_ADAPTER)
    server = _server((parent, candidate))
    server_sha = sha256_bytes(canonical_json_bytes(server.to_dict()))
    runtime = SelectPolicyRuntimeManifestV1(
        schema_id="SELECT_POLICY_RUNTIME_MANIFEST_V1",
        schema_version=1,
        manifest_id="SELECT_RUNTIME_CANDIDATE",
        server_runtime_manifest_sha256=server_sha,
        policy_condition_id=CANDIDATE_CHECKPOINT,
        logical_condition_id=CANDIDATE_LOGICAL,
        checkpoint_instance_id=CANDIDATE_CHECKPOINT,
        training_seed=17,
        served_model_name=CANDIDATE_CHECKPOINT,
        adapter_path="/tmp/" + CANDIDATE_CHECKPOINT,
        adapter_bundle_sha256=CANDIDATE_ADAPTER,
        adapter_rank=16,
    )
    assert runtime.logical_condition_id == CANDIDATE_LOGICAL
    assert runtime.adapter_bundle_sha256 == CANDIDATE_ADAPTER


def test_candidate_select_identity_builds_non_pi1_profile_version():
    identity = _candidate_identity()
    profile = build_select_execution_profile(identity)
    assert profile.arm_id == CANDIDATE_LOGICAL
    assert profile.policy_version == CANDIDATE_LOGICAL
    assert profile.policy_version != "PI1_BAD"
    assert profile.served_model_name == CANDIDATE_CHECKPOINT


def test_legacy_pi1_profile_version_remains_unchanged():
    cell_id = condition_cell_id(
        policy_condition_id=PARENT_CHECKPOINT,
        manifest_index=2,
        seed=17,
    )
    identity = SelectExecutionIdentityV1(
        evaluation_context=P4_SELECT_EVALUATION_CONTEXT,
        logical_condition_id=PARENT_LOGICAL,
        checkpoint_instance_id=PARENT_CHECKPOINT,
        training_seed=17,
        served_model_name=PARENT_CHECKPOINT,
        adapter_bundle_sha256=PARENT_ADAPTER,
        access_class="SELECT_SUMMARY_ONLY",
        policy_condition_id=PARENT_CHECKPOINT,
        condition_cell_id=cell_id,
        task_access_manifest_sha256="1" * 64,
        policy_condition_manifest_sha256="2" * 64,
        condition_run_schedule_sha256="3" * 64,
        select_policy_runtime_manifest_sha256="4" * 64,
    )
    profile = build_select_execution_profile(identity)
    assert profile.policy_version == "PI1_BAD"
