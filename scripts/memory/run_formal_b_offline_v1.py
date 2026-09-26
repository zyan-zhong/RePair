#!/usr/bin/env python3
"""Offline Formal Package-B three-stage evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
from pchsi.memory.formal_b_retrieval import (
    FormalBCandidateV1,
    FormalBGoldPanelV1,
    FormalBIndependentGoldAuthorityV1,
    run_formal_b_three_stage_protocol_v1,
    validate_panel_against_independent_gold_authority_v1,
)


APPROVAL = "PACKAGE_B_RETRIEVAL_SAFETY_EXECUTION_APPROVED"


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_new(path: Path, value: object) -> None:
    data = _canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def run(args: argparse.Namespace) -> None:
    if (
        os.environ.get("PACKAGE_B_SCIENTIFIC_EXECUTION_APPROVAL")
        != APPROVAL
    ):
        raise SystemExit(
            "STOP=FORMAL_B_SCIENTIFIC_EXECUTION_APPROVAL_MISSING"
        )

    panel_path = Path(args.panel)
    gold_authority_path = Path(args.gold_authority)
    snapshot_dir = Path(args.snapshot_directory)
    contract_path = Path(args.token_budget_contract)
    output_root = Path(args.output_root)

    for path, label in (
        (panel_path, "panel"),
        (gold_authority_path, "independent gold authority"),
        (contract_path, "token-budget contract"),
    ):
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"STOP={label.upper().replace(' ', '_')}_PATH_INVALID")
    if output_root.exists() or output_root.is_symlink():
        raise SystemExit("STOP=FORMAL_B_OUTPUT_ROOT_EXISTS")

    panel = FormalBGoldPanelV1.from_json(panel_path.read_bytes())
    gold_authority = FormalBIndependentGoldAuthorityV1.from_json(
        gold_authority_path.read_bytes()
    )
    validate_panel_against_independent_gold_authority_v1(
        panel=panel,
        authority=gold_authority,
    )
    gold_authority_file_sha256 = hashlib.sha256(
        gold_authority_path.read_bytes()
    ).hexdigest()
    if panel.active_snapshot_sha256 != args.snapshot_sha256:
        raise SystemExit("STOP=PANEL_SNAPSHOT_BINDING_MISMATCH")

    loaded = load_calibrated_dev_snapshot_v2(
        snapshot_directory=snapshot_dir,
        expected_snapshot_sha256=args.snapshot_sha256,
        token_budget_contract_path=contract_path,
        expected_token_budget_contract_sha256=(
            args.token_budget_contract_sha256
        ),
    )
    candidates = tuple(
        FormalBCandidateV1(
            record=member.record,
            retrieval_key=member.retrieval_key,
        )
        for member in loaded.members
    )
    result = run_formal_b_three_stage_protocol_v1(
        panel=panel,
        candidates=candidates,
    )

    output_root.mkdir(parents=True, exist_ok=False)

    calibration = {
        "schema_id": "FORMAL_B_CALIBRATION_REPORT_V1",
        "schema_version": 1,
        "panel_sha256": panel.panel_sha256,
        "active_snapshot_sha256": panel.active_snapshot_sha256,
        "threshold_reports": [
            row.to_dict() for row in result.calibration_reports
        ],
        "selected_candidate_threshold_pcts": list(
            result.calibration_candidate_threshold_pcts
        ),
    }
    validation = {
        "schema_id": "FORMAL_B_SELECTION_VALIDATION_REPORT_V1",
        "schema_version": 1,
        "panel_sha256": panel.panel_sha256,
        "active_snapshot_sha256": panel.active_snapshot_sha256,
        "candidate_threshold_pcts": list(
            result.calibration_candidate_threshold_pcts
        ),
        "threshold_reports": [
            row.to_dict() for row in result.validation_reports
        ],
        "selected_config": {
            **result.selected_config.to_dict(),
            "config_sha256": result.selected_config.config_sha256,
        },
    }
    stress = {
        "schema_id": "FORMAL_B_REGISTERED_SAFETY_STRESS_REPORT_V1",
        "schema_version": 1,
        "panel_sha256": panel.panel_sha256,
        "active_snapshot_sha256": panel.active_snapshot_sha256,
        "selected_config": {
            **result.selected_config.to_dict(),
            "config_sha256": result.selected_config.config_sha256,
        },
        "report": result.stress_report.to_dict(),
    }
    selected_config = {
        "schema_id": "FORMAL_B_SELECTED_RETRIEVER_CONFIG_V1",
        "schema_version": 1,
        **result.selected_config.to_dict(),
        "config_sha256": result.selected_config.config_sha256,
        "selection_validation_report_authority": (
            "FROZEN_AFTER_RETRIEVER_SELECTION_VALIDATION"
        ),
        "safety_stress_may_modify_config": False,
    }
    summary = result.to_summary_dict()
    summary.update(
        {
            "panel_sha256": panel.panel_sha256,
            "active_snapshot_sha256": panel.active_snapshot_sha256,
            "independent_gold_authority_sha256": (
                panel.independent_gold_authority_sha256
            ),
            "independent_gold_authority_file_sha256": (
                gold_authority_file_sha256
            ),
            "scientific_execution_approval": APPROVAL,
        }
    )

    outputs = {
        "B_RETRIEVER_CALIBRATION_V1.json": calibration,
        "B_RETRIEVER_SELECTION_VALIDATION_V1.json": validation,
        "B_SELECTED_RETRIEVER_CONFIG_V1.json": selected_config,
        "B_REGISTERED_SAFETY_STRESS_V1.json": stress,
        "B_RESULT_SUMMARY_V1.json": summary,
    }
    for name, payload in outputs.items():
        _write_new(output_root / name, payload)

    checksum_lines = []
    for name in sorted(outputs):
        data = (output_root / name).read_bytes()
        checksum_lines.append(
            hashlib.sha256(data).hexdigest() + "  " + name
        )
    (output_root / "SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )

    print("FORMAL_B_OFFLINE_EXECUTION_COMPLETE")
    print("PANEL_SHA256=" + str(panel.panel_sha256))
    print(
        "SELECTED_THRESHOLD_PCT="
        + str(result.selected_config.threshold_pct)
    )
    print(
        "SELECTED_CONFIG_SHA256="
        + result.selected_config.config_sha256
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--gold-authority", required=True)
    parser.add_argument("--snapshot-directory", required=True)
    parser.add_argument("--snapshot-sha256", required=True)
    parser.add_argument("--token-budget-contract", required=True)
    parser.add_argument(
        "--token-budget-contract-sha256",
        required=True,
    )
    parser.add_argument("--output-root", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
