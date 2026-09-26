"""Deterministic common Analyzer Evidence Pack V1 builder."""
from __future__ import annotations

from pathlib import Path

from .canonical import domain_hash, write_new_json
from .types import ValidatedAttemptBundle


def _transition_by_model_call(
    bundle: ValidatedAttemptBundle,
) -> dict[int, object]:
    out = {}
    for transition in bundle.transitions:
        if transition.model_call_index in out:
            raise ValueError("multiple public transitions for one model call")
        out[transition.model_call_index] = transition
    return out


def build_analyzer_evidence_pack(
    *,
    bundle: ValidatedAttemptBundle,
    pi1_identity: dict[str, object],
    rebinding_manifest: dict[str, object],
    mechanical_evidence: dict[str, object],
    lineage_bridge: dict[str, object],
) -> dict[str, object]:
    if pi1_identity.get("schema_id") != "PI1_REFERENCE_IDENTITY_V1":
        raise ValueError("π1 identity schema mismatch")
    if (
        rebinding_manifest.get("source_attempt_bundle_sha256")
        != bundle.attempt_bundle_sha256
    ):
        raise ValueError("rebinding source bundle differs from validated bundle")
    if (
        rebinding_manifest.get("policy_identity_sha256")
        != pi1_identity.get("identity_sha256")
    ):
        raise ValueError("rebinding policy identity differs from π1 identity")
    if (
        mechanical_evidence.get("source_attempt_bundle_sha256")
        != bundle.attempt_bundle_sha256
    ):
        raise ValueError("mechanical evidence source differs from bundle")
    if mechanical_evidence.get("authority") != "DETERMINISTIC_FACTS_ONLY":
        raise ValueError("mechanical evidence authority mismatch")

    rows = lineage_bridge.get("rows")
    if not isinstance(rows, list):
        raise TypeError("lineage bridge rows must be array")
    lineage_matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("attempt_bundle_sha256")
        == bundle.attempt_bundle_sha256
    ]
    if len(lineage_matches) != 1:
        raise ValueError("Analyzer pack requires unique historical lineage row")
    lineage = lineage_matches[0]

    transitions = _transition_by_model_call(bundle)
    trajectory_rows = []

    for call, trace in zip(bundle.policy_calls, bundle.traces):
        if call.model_call_index != trace.model_call_index:
            raise ValueError("call/trace index mismatch during pack build")
        transition = transitions.get(call.model_call_index)
        trajectory_rows.append(
            {
                "model_call_index": call.model_call_index,
                "environment_step_count_before": (
                    call.environment_step_count_before
                ),
                "public_task_goal": call.public_task_goal,
                "observation_before": call.observation,
                "admissible_commands": list(call.admissible_commands),
                "executed_history": [
                    {
                        "action": action,
                        "resulting_observation": observation,
                    }
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
                "submitted_environment_action": (
                    trace.submitted_environment_action
                ),
                "final_executed_action": trace.final_executed_action,
                "resulting_observation": (
                    None
                    if transition is None
                    else transition.resulting_observation
                ),
                "resulting_admissible_commands": (
                    None
                    if transition is None
                    else list(transition.resulting_menu)
                ),
                "environment_done": (
                    None if transition is None else transition.done
                ),
                "environment_won": (
                    None if transition is None else transition.won
                ),
                "environment_score": (
                    None if transition is None else transition.score
                ),
                "budget_before": call.budget_before.to_dict(),
                "budget_after": trace.budget_after.to_dict(),
            }
        )

    task_goal = (
        bundle.policy_calls[0].public_task_goal
        if bundle.policy_calls
        else ""
    )

    pack = {
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
            "logical_policy_id": pi1_identity["logical_policy_id"],
            "checkpoint_instance_id": pi1_identity[
                "checkpoint_instance_id"
            ],
            "identity_sha256": pi1_identity["identity_sha256"],
        },
        "trajectory_identity": {
            "source_attempt_bundle_sha256": (
                bundle.attempt_bundle_sha256
            ),
            "source_episode_semantic_sha256": (
                bundle.episode_semantic_sha256
            ),
            "trajectory_rebinding_manifest_sha256": (
                rebinding_manifest["manifest_sha256"]
            ),
            "historical_lineage_bridge_sha256": (
                lineage_bridge["bridge_sha256"]
            ),
            "historical_lineage_row_sha256": lineage["row_sha256"],
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


def write_analyzer_evidence_pack(
    *,
    bundle: ValidatedAttemptBundle,
    pi1_identity: dict[str, object],
    rebinding_manifest: dict[str, object],
    mechanical_evidence: dict[str, object],
    lineage_bridge: dict[str, object],
    output_path: Path,
) -> dict[str, object]:
    value = build_analyzer_evidence_pack(
        bundle=bundle,
        pi1_identity=pi1_identity,
        rebinding_manifest=rebinding_manifest,
        mechanical_evidence=mechanical_evidence,
        lineage_bridge=lineage_bridge,
    )
    write_new_json(output_path, value)
    return value
