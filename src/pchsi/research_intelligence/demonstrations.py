from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .common import finalize_hash, load_object, write_json_new


def build_demonstration_pack(
    *,
    reference_round_paths: Iterable[Path],
    current_round_id: str,
    output: Path,
) -> dict[str, object]:
    records = []
    seen_rounds = set()
    for path in sorted(reference_round_paths, key=lambda item: str(item)):
        round_record = load_object(path)
        if round_record.get("schema_id") != (
            "RESEARCH_PLANNER_REFERENCE_ROUND_MANIFEST_V1"
        ):
            raise ValueError(f"not a reference-round manifest: {path}")
        round_id = str(round_record["round_id"])
        if round_id == current_round_id:
            raise ValueError("current-round record cannot enter its own demo pack")
        if round_id in seen_rounds:
            raise ValueError(f"duplicate reference round: {round_id}")
        seen_rounds.add(round_id)
        if round_record.get("access_class") not in {
            "TRAIN_REFERENCE_ROUND",
            "TRAIN_RESEARCH_INTELLIGENCE",
        }:
            raise ValueError("non-train reference round cannot enter demos")
        records.append(
            {
                "round_id": round_id,
                "reference_round_manifest_sha256": round_record[
                    "reference_round_manifest_sha256"
                ],
                "human_pre_record_sha256": round_record[
                    "human_pre_record_sha256"
                ],
                "strong_pre_shadow_sha256": round_record[
                    "strong_pre_shadow_sha256"
                ],
                "pre_adjudication_sha256": round_record[
                    "pre_adjudication_sha256"
                ],
                "environment_result_package_sha256": round_record[
                    "environment_result_package_sha256"
                ],
                "human_post_record_sha256": round_record[
                    "human_post_record_sha256"
                ],
                "strong_post_shadow_sha256": round_record[
                    "strong_post_shadow_sha256"
                ],
                "post_adjudication_sha256": round_record[
                    "post_adjudication_sha256"
                ],
                "verified_training_evidence_sha256": round_record[
                    "verified_training_evidence_sha256"
                ],
                "policy_evaluation_result_sha256": round_record[
                    "policy_evaluation_result_sha256"
                ],
                "promotion_result": round_record["promotion_result"],
                "go_nogo_status": round_record["go_nogo_status"],
            }
        )
    if not records:
        raise ValueError("at least one prior completed reference round is required")
    out = {
        "schema_id": "RESEARCH_PLANNER_DEMONSTRATION_PACK_V1",
        "schema_version": 1,
        "current_round_id": current_round_id,
        "records": records,
        "current_round_human_answer_absent": True,
        "sealed_test_details_absent": True,
        "demonstration_pack_sha256": "0" * 64,
    }
    out = finalize_hash(
        domain="RESEARCH_PLANNER_DEMONSTRATION_PACK_V1",
        field="demonstration_pack_sha256",
        value=out,
    )
    write_json_new(output, out)
    return out
