#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.cognitive_runtime.output_validation import validate_stage_output
from pchsi.reference_loop.canonical import (
    domain_hash,
    sha256_file,
    strict_json_loads,
    write_new_json,
)

ANALYZER_STAGE_IDS = ("L-A0", "L-A1", "G-A2", "G-A3", "C", "X")


def _require_sha256(name: str, value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def freeze_human_analyzer_primary(
    *,
    stage_id: str,
    round_id: str,
    policy_version: str,
    unit_identity_sha256: str,
    projection_path: Path,
    human_draft_path: Path,
    output_result_path: Path,
    output_receipt_path: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    if stage_id not in ANALYZER_STAGE_IDS:
        raise ValueError("unsupported Human Analyzer stage")
    if not round_id or not policy_version:
        raise ValueError("round_id and policy_version are required")
    _require_sha256("unit_identity_sha256", unit_identity_sha256)

    projection_path = Path(projection_path)
    human_draft_path = Path(human_draft_path)
    if projection_path.is_symlink() or not projection_path.is_file():
        raise ValueError("projection must be a regular non-symlink file")
    if human_draft_path.is_symlink() or not human_draft_path.is_file():
        raise ValueError("human draft must be a regular non-symlink file")

    projection = strict_json_loads(projection_path.read_bytes())
    if not isinstance(projection, dict):
        raise ValueError("projection must be one JSON object")
    draft_text = human_draft_path.read_text(encoding="utf-8")
    draft_sha = sha256_file(human_draft_path)
    projection_sha = sha256_file(projection_path)

    finalized = validate_stage_output(
        stage_id=stage_id,
        text=draft_text,
        raw_response_sha256=draft_sha,
        projection=projection,
    )
    write_new_json(Path(output_result_path), finalized)
    result_file_sha = sha256_file(Path(output_result_path))

    receipt: dict[str, object] = {
        "schema_id": "HUMAN_ANALYZER_PRIMARY_FREEZE_RECEIPT_V1",
        "schema_version": 1,
        "round_id": round_id,
        "policy_version": policy_version,
        "logical_role": "ANALYZER",
        "actor": "HUMAN",
        "authority": "PRIMARY",
        "stage_id": stage_id,
        "unit_identity_sha256": unit_identity_sha256,
        "projection_file_sha256": projection_sha,
        "human_draft_file_sha256": draft_sha,
        "finalized_result_file_sha256": result_file_sha,
        "strong_shadow_human_content_visible": False,
        "strong_shadow_human_hash_visible": False,
        "benchmark_result_values_consumed": False,
        "historical_semantic_artifact_consumed": False,
        "provider_call_count": 0,
        "environment_execution_count": 0,
        "training_execution_count": 0,
        "receipt_sha256": "0" * 64,
    }
    receipt["receipt_sha256"] = domain_hash(
        "HUMAN_ANALYZER_PRIMARY_FREEZE_RECEIPT_V1",
        receipt,
        excluded_field="receipt_sha256",
    )
    write_new_json(Path(output_receipt_path), receipt)
    return finalized, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-id", required=True, choices=ANALYZER_STAGE_IDS)
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--policy-version", required=True)
    parser.add_argument("--unit-identity-sha256", required=True)
    parser.add_argument("--projection", required=True)
    parser.add_argument("--human-draft", required=True)
    parser.add_argument("--output-result", required=True)
    parser.add_argument("--output-receipt", required=True)
    args = parser.parse_args()

    _, receipt = freeze_human_analyzer_primary(
        stage_id=args.stage_id,
        round_id=args.round_id,
        policy_version=args.policy_version,
        unit_identity_sha256=args.unit_identity_sha256,
        projection_path=Path(args.projection),
        human_draft_path=Path(args.human_draft),
        output_result_path=Path(args.output_result),
        output_receipt_path=Path(args.output_receipt),
    )
    print("HUMAN_ANALYZER_PRIMARY_FREEZE_PASS")
    print("STAGE_ID=" + args.stage_id)
    print("RECEIPT_SHA256=" + str(receipt["receipt_sha256"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
