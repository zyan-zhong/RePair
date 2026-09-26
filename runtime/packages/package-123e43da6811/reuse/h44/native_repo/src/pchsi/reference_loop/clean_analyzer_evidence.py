"""Clean current-round Analyzer evidence binding for PI0 + I1 TRAIN_UPDATE."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .analyzer_evidence_pack import _transition_by_model_call
from .canonical import domain_hash, write_new_json
from .types import ValidatedAttemptBundle


def _require_sha256(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _require_schema(value: dict[str, Any], schema_id: str, name: str) -> None:
    if value.get("schema_id") != schema_id:
        raise ValueError(f"{name} schema mismatch")


def build_pi0_i1_analyzer_policy_identity(
    *,
    pi0_artifact: dict[str, Any],
    runtime_binding: dict[str, Any],
    evidence_cutoff: dict[str, Any],
) -> dict[str, object]:
    _require_schema(pi0_artifact, "PI0_CLEAN_MODEL_ARTIFACT_V1", "pi0 artifact")
    _require_schema(runtime_binding, "PI0_CLEAN_RUNTIME_BINDING_V1", "runtime binding")
    _require_schema(
        evidence_cutoff,
        "PI0_I1_TRAIN_UPDATE_EVIDENCE_CUTOFF_V1",
        "evidence cutoff",
    )
    artifact_sha = _require_sha256(
        "pi0_artifact_sha256", pi0_artifact.get("pi0_artifact_sha256")
    )
    runtime_sha = _require_sha256(
        "runtime_binding_sha256", runtime_binding.get("runtime_binding_sha256")
    )
    source_campaign_sha = _require_sha256(
        "source_campaign_sha256", evidence_cutoff.get("source_campaign_sha256")
    )
    if runtime_binding.get("pi0_artifact_sha256") != artifact_sha:
        raise ValueError("runtime binding does not bind the frozen PI0 artifact")
    if pi0_artifact.get("artifact_role") != "PI0_CLEAN_PROJECT_UNADAPTED_POLICY":
        raise ValueError("PI0 artifact role mismatch")
    if any(
        pi0_artifact.get(field) is not expected
        for field, expected in (
            ("project_lora_present", False),
            ("project_adapter_present", False),
            ("project_memory_present", False),
        )
    ):
        raise ValueError("PI0 project adaptation state must be empty")
    if pi0_artifact.get("contaminated_trace_dependency_count") != 0:
        raise ValueError("PI0 artifact has contaminated trace dependency")
    if runtime_binding.get("lora_modules") != []:
        raise ValueError("PI0 runtime must not bind LoRA modules")
    if runtime_binding.get("project_adapter") is not None:
        raise ValueError("PI0 runtime must not bind a project adapter")
    if runtime_binding.get("memory") != "OFF" or runtime_binding.get("harness") != "OFF":
        raise ValueError("PI0 Analyzer source policy must be Memory OFF / Harness OFF")
    if evidence_cutoff.get("parent_policy_id") != "PI0_CLEAN":
        raise ValueError("evidence cutoff parent policy mismatch")
    if evidence_cutoff.get("policy_interface_profile_id") != "I1_EXECUTION_PROFILE_V1":
        raise ValueError("evidence cutoff is not the frozen I1 profile")
    if evidence_cutoff.get("source_split") != "ALFWORLD_TRAIN":
        raise ValueError("clean Analyzer evidence must come from ALFWorld train")
    if evidence_cutoff.get("source_train_pool") != "TRAIN_UPDATE":
        raise ValueError("clean Analyzer evidence must come from TRAIN_UPDATE")
    if evidence_cutoff.get("evidence_cutoff_frozen") is not True:
        raise ValueError("clean Analyzer evidence cutoff is not frozen")
    if evidence_cutoff.get("benchmark_results_visible") is not False:
        raise ValueError("benchmark result values must remain sealed")
    if evidence_cutoff.get("benchmark_feedback_authorized") is not False:
        raise ValueError("benchmark feedback must remain forbidden")

    revision = str(pi0_artifact.get("model_revision"))
    repository = str(pi0_artifact.get("model_repository"))
    if not revision or not repository:
        raise ValueError("PI0 model identity fields are missing")
    identity: dict[str, object] = {
        "schema_id": "PI0_I1_ANALYZER_POLICY_IDENTITY_V1",
        "schema_version": 1,
        "logical_policy_id": "PI0_CLEAN",
        "checkpoint_instance_id": f"PI0_CLEAN::{revision}::I1",
        "model_repository": repository,
        "model_revision": revision,
        "pi0_artifact_sha256": artifact_sha,
        "runtime_binding_sha256": runtime_sha,
        "policy_interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "source_campaign_sha256": source_campaign_sha,
        "memory": "OFF",
        "harness": "OFF",
        "identity_sha256": "0" * 64,
    }
    identity["identity_sha256"] = domain_hash(
        "PI0_I1_ANALYZER_POLICY_IDENTITY_V1",
        identity,
        excluded_field="identity_sha256",
    )
    return identity


def build_clean_current_trajectory_binding(
    *,
    bundle: ValidatedAttemptBundle,
    evidence_row: dict[str, Any],
    evidence_cutoff: dict[str, Any],
    analyzer_readiness: dict[str, Any],
    policy_identity: dict[str, object],
    source_campaign_root: Path,
) -> dict[str, object]:
    _require_schema(
        evidence_cutoff,
        "PI0_I1_TRAIN_UPDATE_EVIDENCE_CUTOFF_V1",
        "evidence cutoff",
    )
    _require_schema(
        analyzer_readiness,
        "PI0_I1_ANALYZER_INPUT_READINESS_V1",
        "Analyzer readiness",
    )
    _require_schema(
        policy_identity,
        "PI0_I1_ANALYZER_POLICY_IDENTITY_V1",
        "policy identity",
    )
    if analyzer_readiness.get("clean_inputs_pass") is not True:
        raise ValueError("clean Analyzer input readiness did not pass")
    if analyzer_readiness.get("benchmark_results_visible") is not False:
        raise ValueError("Analyzer readiness exposes sealed benchmark results")
    grants = analyzer_readiness.get("clean_access_grants")
    if not isinstance(grants, dict):
        raise ValueError("clean access grants missing")
    analyzer_access_sha = _require_sha256(
        "HIERARCHICAL_ANALYZER clean access SHA",
        grants.get("HIERARCHICAL_ANALYZER"),
    )

    classification = evidence_row.get("classification")
    if classification not in {"TASK_FAILURE", "SUCCESS"}:
        raise ValueError("clean Analyzer row must be scientifically eligible")
    if evidence_row.get("source_campaign_sha256") != evidence_cutoff.get(
        "source_campaign_sha256"
    ):
        raise ValueError("evidence row source campaign mismatch")
    if evidence_row.get("policy_interface_profile_id") != "I1_EXECUTION_PROFILE_V1":
        raise ValueError("evidence row is not I1")
    if evidence_row.get("task_id") != bundle.task_id:
        raise ValueError("evidence row task identity mismatch")
    if evidence_row.get("attempt_bundle_sha256") != bundle.attempt_bundle_sha256:
        raise ValueError("evidence row attempt bundle SHA mismatch")
    if evidence_row.get("episode_semantic_sha256") != bundle.episode_semantic_sha256:
        raise ValueError("evidence row episode semantic SHA mismatch")

    root = Path(source_campaign_root).resolve()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("source campaign root must be a regular directory")
    rel = evidence_row.get("attempt_bundle_relpath")
    if not isinstance(rel, str) or not rel:
        raise ValueError("attempt bundle relative path missing")
    rel_path = Path(rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise ValueError("attempt bundle relative path escapes campaign root")
    expected_bundle_root = (root / rel_path).resolve()
    if expected_bundle_root != bundle.bundle_root.resolve():
        raise ValueError("validated bundle path differs from frozen evidence row")

    row_sha = domain_hash(
        "PI0_I1_TRAIN_UPDATE_EVIDENCE_INDEX_ROW_V1",
        evidence_row,
    )
    source_file_bindings = [
        {
            "filename": name,
            "sha256": digest,
            "path": str(bundle.bundle_root / name),
        }
        for name, digest in bundle.source_file_sha256s
    ]
    binding: dict[str, object] = {
        "schema_id": "CLEAN_CURRENT_TRAJECTORY_BINDING_V1",
        "schema_version": 1,
        "binding_mode": "CLEAN_CURRENT_ROUND_TRAIN_UPDATE_V1",
        "logical_policy_id": policy_identity["logical_policy_id"],
        "policy_identity_sha256": policy_identity["identity_sha256"],
        "policy_interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "source_campaign_root": str(root),
        "source_campaign_sha256": evidence_cutoff["source_campaign_sha256"],
        "evidence_cutoff_sha256": evidence_cutoff["evidence_cutoff_sha256"],
        "clean_analyzer_access_sha256": analyzer_access_sha,
        "evidence_index_row_sha256": row_sha,
        "scientific_cell_id": evidence_row["scientific_cell_id"],
        "execution_attempt_id": evidence_row["execution_attempt_id"],
        "task_id": bundle.task_id,
        "gamefile_sha256": bundle.gamefile_sha256,
        "classification": classification,
        "source_attempt_bundle_path": str(bundle.bundle_root),
        "source_attempt_bundle_sha256": bundle.attempt_bundle_sha256,
        "source_episode_semantic_sha256": bundle.episode_semantic_sha256,
        "source_file_bindings": source_file_bindings,
        "per_task_full_view_relpath": evidence_row["per_task_full_view_relpath"],
        "per_task_full_view_sha256": evidence_row["per_task_full_view_sha256"],
        "benchmark_reference_count": 0,
        "historical_adaptive_reference_count": 0,
        "pilot_semantic_reference_count": 0,
        "binding_sha256": "0" * 64,
    }
    binding["binding_sha256"] = domain_hash(
        "CLEAN_CURRENT_TRAJECTORY_BINDING_V1",
        binding,
        excluded_field="binding_sha256",
    )
    return binding


def build_clean_analyzer_evidence_pack(
    *,
    bundle: ValidatedAttemptBundle,
    policy_identity: dict[str, object],
    trajectory_binding: dict[str, object],
    mechanical_evidence: dict[str, object],
) -> dict[str, object]:
    _require_schema(
        policy_identity,
        "PI0_I1_ANALYZER_POLICY_IDENTITY_V1",
        "policy identity",
    )
    _require_schema(
        trajectory_binding,
        "CLEAN_CURRENT_TRAJECTORY_BINDING_V1",
        "trajectory binding",
    )
    if trajectory_binding.get("source_attempt_bundle_sha256") != bundle.attempt_bundle_sha256:
        raise ValueError("clean trajectory binding differs from validated bundle")
    if trajectory_binding.get("source_episode_semantic_sha256") != bundle.episode_semantic_sha256:
        raise ValueError("clean trajectory semantic identity mismatch")
    if trajectory_binding.get("policy_identity_sha256") != policy_identity.get(
        "identity_sha256"
    ):
        raise ValueError("clean trajectory binding policy identity mismatch")
    if mechanical_evidence.get("source_attempt_bundle_sha256") != bundle.attempt_bundle_sha256:
        raise ValueError("mechanical evidence source differs from bundle")
    if mechanical_evidence.get("authority") != "DETERMINISTIC_FACTS_ONLY":
        raise ValueError("mechanical evidence authority mismatch")

    transitions = _transition_by_model_call(bundle)
    trajectory_rows: list[dict[str, object]] = []
    for call, trace in zip(bundle.policy_calls, bundle.traces):
        if call.model_call_index != trace.model_call_index:
            raise ValueError("call/trace index mismatch during pack build")
        transition = transitions.get(call.model_call_index)
        trajectory_rows.append(
            {
                "model_call_index": call.model_call_index,
                "environment_step_count_before": call.environment_step_count_before,
                "public_task_goal": call.public_task_goal,
                "observation_before": call.observation,
                "admissible_commands": list(call.admissible_commands),
                "executed_history": [
                    {"action": action, "resulting_observation": observation}
                    for action, observation in call.executed_history
                ],
                "policy_prompt_text": call.prompt_text,
                "raw_model_response": call.raw_response_text,
                "literal_action": trace.literal_action,
                "normalized_action": trace.normalized_action,
                "parser_status": trace.parser_status,
                "parser_error": trace.parser_error,
                "attempt_outcome": trace.attempt_outcome,
                "execution_status": trace.execution_status,
                "submitted_environment_action": trace.submitted_environment_action,
                "final_executed_action": trace.final_executed_action,
                "resulting_observation": None if transition is None else transition.resulting_observation,
                "resulting_admissible_commands": None if transition is None else list(transition.resulting_menu),
                "environment_done": None if transition is None else transition.done,
                "environment_won": None if transition is None else transition.won,
                "environment_score": None if transition is None else transition.score,
                "budget_before": call.budget_before.to_dict(),
                "budget_after": trace.budget_after.to_dict(),
            }
        )

    task_goal = bundle.policy_calls[0].public_task_goal if bundle.policy_calls else ""
    pack: dict[str, object] = {
        "schema_id": "ANALYZER_EVIDENCE_PACK_V1",
        "schema_version": 1,
        "pack_role": "COMMON_EVIDENCE_IDENTICAL_ACROSS_A0_A1_A2_A3",
        "task_identity": {
            "task_id": bundle.task_id,
            "task_type": bundle.episode.get("task_type"),
            "gamefile_sha256": bundle.gamefile_sha256,
            "seed": bundle.episode.get("seed"),
            "public_task_goal": task_goal,
        },
        "policy_identity": {
            "logical_policy_id": policy_identity["logical_policy_id"],
            "checkpoint_instance_id": policy_identity["checkpoint_instance_id"],
            "identity_sha256": policy_identity["identity_sha256"],
        },
        "trajectory_identity": {
            "source_attempt_bundle_sha256": bundle.attempt_bundle_sha256,
            "source_episode_semantic_sha256": bundle.episode_semantic_sha256,
            "clean_current_trajectory_binding_sha256": trajectory_binding["binding_sha256"],
            "evidence_cutoff_sha256": trajectory_binding["evidence_cutoff_sha256"],
            "source_campaign_sha256": trajectory_binding["source_campaign_sha256"],
            "evidence_index_row_sha256": trajectory_binding["evidence_index_row_sha256"],
            "scientific_cell_id": trajectory_binding["scientific_cell_id"],
            "execution_attempt_id": trajectory_binding["execution_attempt_id"],
            "policy_interface_profile_id": trajectory_binding["policy_interface_profile_id"],
        },
        "trajectory": trajectory_rows,
        "mechanical_evidence": mechanical_evidence,
        "memory_support_port": {
            "schema_id": "ANALYZER_MEMORY_SUPPORT_PORT_V1",
            "base_pack_exposes_memory": False,
            "memory_packet": None,
            "a3_extension_rule": (
                "A3_MAY_ATTACH_ONE_FROZEN_ANALYZER_MEMORY_PACKET_"
                "WITHOUT_CHANGING_COMMON_TRAJECTORY_EVIDENCE"
            ),
        },
        "analyzer_output_authority": {
            "failure_window_is_proposal": True,
            "mechanism_is_semantic_hypothesis": True,
            "candidate_repair_is_proposal": True,
            "benefit_harm_authority": False,
            "training_label_authority": False,
            "promotion_authority": False,
        },
        "requires_environment_verification": True,
        "evidence_pack_sha256": "0" * 64,
    }
    pack["evidence_pack_sha256"] = domain_hash(
        "ANALYZER_EVIDENCE_PACK_V1",
        pack,
        excluded_field="evidence_pack_sha256",
    )
    return pack


def write_clean_analyzer_evidence_pack(
    *,
    bundle: ValidatedAttemptBundle,
    policy_identity: dict[str, object],
    trajectory_binding: dict[str, object],
    mechanical_evidence: dict[str, object],
    output_path: Path,
) -> dict[str, object]:
    pack = build_clean_analyzer_evidence_pack(
        bundle=bundle,
        policy_identity=policy_identity,
        trajectory_binding=trajectory_binding,
        mechanical_evidence=mechanical_evidence,
    )
    write_new_json(output_path, pack)
    return pack
