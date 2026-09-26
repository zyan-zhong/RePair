from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .common import finalize_hash, write_json_new


def freeze_reference_round_manifest(
    value: Mapping[str, object],
    output: Path,
) -> dict[str, object]:
    required = {
        "round_id",
        "policy_lineage_sha256",
        "round_evidence_package_sha256",
        "human_pre_record_sha256",
        "strong_pre_shadow_sha256",
        "pre_adjudication_sha256",
        "environment_result_package_sha256",
        "human_post_record_sha256",
        "strong_post_shadow_sha256",
        "post_adjudication_sha256",
        "verified_training_evidence_sha256",
        "policy_evaluation_result_sha256",
        "promotion_result",
        "go_nogo_status",
        "access_class",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"reference round manifest missing fields: {missing}")
    if value["access_class"] not in {
        "TRAIN_REFERENCE_ROUND",
        "TRAIN_RESEARCH_INTELLIGENCE",
    }:
        raise ValueError("reference round must be train-side")
    if value["promotion_result"] not in {"PROMOTE", "ROLLBACK", "HOLD"}:
        raise ValueError("invalid promotion_result")
    if value["go_nogo_status"] not in {"GO", "NO_GO", "HOLD"}:
        raise ValueError("invalid go_nogo_status")
    out = {
        "schema_id": "RESEARCH_PLANNER_REFERENCE_ROUND_MANIFEST_V1",
        "schema_version": 1,
        **dict(value),
        "reference_round_manifest_sha256": "0" * 64,
    }
    out = finalize_hash(
        domain="RESEARCH_PLANNER_REFERENCE_ROUND_MANIFEST_V1",
        field="reference_round_manifest_sha256",
        value=out,
    )
    write_json_new(output, out)
    return out
