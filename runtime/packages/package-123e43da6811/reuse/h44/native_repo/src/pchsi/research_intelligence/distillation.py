from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .common import finalize_hash, load_object, write_json_new


_ALLOWED_ROLES = {
    "ANALYZER",
    "RESEARCH_PLANNER_PRE",
    "RESEARCH_PLANNER_POST",
}


def _example_from_round(
    round_record: dict[str, object],
    *,
    phase: str,
) -> dict[str, object]:
    round_id = str(round_record["round_id"])
    if phase == "PRE":
        role = "RESEARCH_PLANNER_PRE"
        input_sha = round_record["round_evidence_package_sha256"]
        teacher_sha = round_record["strong_pre_shadow_sha256"]
        human_sha = round_record["human_pre_record_sha256"]
        adjudication_sha = round_record["pre_adjudication_sha256"]
        outcome_sha = None
    elif phase == "POST":
        role = "RESEARCH_PLANNER_POST"
        input_sha = round_record["environment_result_package_sha256"]
        teacher_sha = round_record["strong_post_shadow_sha256"]
        human_sha = round_record["human_post_record_sha256"]
        adjudication_sha = round_record["post_adjudication_sha256"]
        outcome_sha = round_record["policy_evaluation_result_sha256"]
    else:
        raise ValueError(f"unsupported phase: {phase}")
    value = {
        "schema_id": "LOCAL_ROLE_SUPERVISION_EXAMPLE_V1",
        "schema_version": 1,
        "example_id": f"{round_id}:{phase}",
        "round_id": round_id,
        "role": role,
        "input_artifact_sha256": input_sha,
        "strong_teacher_record_sha256": teacher_sha,
        "human_reference_record_sha256": human_sha,
        "field_adjudication_sha256": adjudication_sha,
        "environment_or_policy_outcome_sha256": outcome_sha,
        "go_nogo_status": round_record["go_nogo_status"],
        "promotion_result": round_record["promotion_result"],
        "provider_reasoning_artifact_required": False,
        "structured_evidence_and_decision_target_required": True,
        "future_outcome_leakage_absent": True,
        "example_sha256": "0" * 64,
    }
    return finalize_hash(
        domain="LOCAL_ROLE_SUPERVISION_EXAMPLE_V1",
        field="example_sha256",
        value=value,
    )


def build_local_role_supervision_dataset(
    *,
    reference_round_paths: Iterable[Path],
    output: Path,
) -> dict[str, object]:
    examples = []
    round_ids = set()
    for path in sorted(reference_round_paths, key=lambda item: str(item)):
        round_record = load_object(path)
        if round_record.get("schema_id") != (
            "RESEARCH_PLANNER_REFERENCE_ROUND_MANIFEST_V1"
        ):
            raise ValueError(f"not a reference-round manifest: {path}")
        round_id = str(round_record["round_id"])
        if round_id in round_ids:
            raise ValueError(f"duplicate round in dataset: {round_id}")
        round_ids.add(round_id)
        if round_record.get("access_class") not in {
            "TRAIN_REFERENCE_ROUND",
            "TRAIN_RESEARCH_INTELLIGENCE",
        }:
            raise ValueError("only train-side rounds may enter distillation")
        examples.append(_example_from_round(round_record, phase="PRE"))
        examples.append(_example_from_round(round_record, phase="POST"))
    if not examples:
        raise ValueError("at least one completed round is required")
    if any(example["role"] not in _ALLOWED_ROLES for example in examples):
        raise ValueError("dataset contains unsupported role")
    out = {
        "schema_id": "LOCAL_ROLE_SUPERVISION_DATASET_V1",
        "schema_version": 1,
        "base_model_lineage": "Qwen2.5-3B-Instruct",
        "split_unit": "ROUND_ID_PLUS_POLICY_LINEAGE_PLUS_TASK_SET",
        "examples": examples,
        "go_and_no_go_preserved": True,
        "provider_reasoning_artifact_required": False,
        "local_training_executed": False,
        "local_primary_authorized": False,
        "dataset_sha256": "0" * 64,
    }
    out = finalize_hash(
        domain="LOCAL_ROLE_SUPERVISION_DATASET_V1",
        field="dataset_sha256",
        value=out,
    )
    write_json_new(output, out)
    return out
