#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from pchsi.reference_loop.canonical import (
    canonical_json_bytes,
    domain_hash,
)
from pchsi.research_intelligence.human_planner_adjudication import (
    compile_human_planner_artifacts_v1,
)
from pchsi.research_intelligence.human_reference_round import (
    freeze_pre,
    validate_evidence_binding,
)
from pchsi.research_intelligence.repair_portfolio import (
    ResearchRepairPortfolioV1,
    freeze_repair_portfolio,
)


def load(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular JSON file required: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def write_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    data = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adjudication-candidate", required=True)
    parser.add_argument("--dossier", required=True)
    parser.add_argument("--shared-input", required=True)
    parser.add_argument("--evidence-binding", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--approval-timestamp-utc", required=True)
    parser.add_argument("--approval-note", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    candidate = load(
        Path(args.adjudication_candidate).resolve()
    )
    approval = candidate.get("human_approval")
    if not isinstance(approval, dict):
        raise SystemExit("STOP=HUMAN_APPROVAL_RECORD_MISSING")
    if approval.get("status") != (
        "ASSISTANT_PREPARED_REQUIRES_USER_APPROVAL"
    ):
        raise SystemExit(
            "STOP=ADJUDICATION_CANDIDATE_NOT_PENDING_APPROVAL"
        )

    approved = dict(candidate)
    approved["human_approval"] = {
        "status": "APPROVED",
        "reviewer": args.reviewer,
        "approval_timestamp": args.approval_timestamp_utc,
        "approval_note": args.approval_note,
    }

    dossier = load(Path(args.dossier).resolve())
    shared = load(Path(args.shared_input).resolve())
    binding = load(Path(args.evidence_binding).resolve())
    validate_evidence_binding(binding)

    artifacts = compile_human_planner_artifacts_v1(
        adjudication=approved,
        dossier=dossier,
        shared_input=shared,
    )
    if artifacts["build_report"]["human_approval_status"] != "APPROVED":
        raise SystemExit("STOP=COMPILED_APPROVAL_STATUS")

    human_pre = artifacts["human_pre_input"]
    portfolio = ResearchRepairPortfolioV1.from_dict(
        artifacts["repair_portfolio"]
    )
    portfolio.validate()

    if human_pre["evidence_cutoff"] != binding[
        "evidence_cutoff_sha256"
    ]:
        raise SystemExit("STOP=HUMAN_PRE_BINDING_CUTOFF")
    if human_pre["round_evidence_package_sha256"] != binding[
        "round_evidence_package_sha256"
    ]:
        raise SystemExit("STOP=HUMAN_PRE_ROUND_BINDING")

    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)

    write_new(
        output
        / "HUMAN_PLANNER_SCIENTIFIC_ADJUDICATION_V1.json",
        approved,
    )
    write_new(
        output / "RESEARCHER_PRE_DECISION_V1.json",
        artifacts["role_neutral_pre_decision"],
    )
    write_new(
        output / "RESEARCH_PLANNER_REFERENCE_TRACE_V2.json",
        artifacts["reference_trace"],
    )
    write_new(
        output / "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1.json",
        artifacts["strong_blind_input"],
    )

    pre_dir = output / "human_pre"
    frozen_pre = freeze_pre(
        human_pre,
        pre_dir,
        evidence_binding=binding,
    )

    portfolio_dir = output / "repair_portfolio"
    portfolio_path, portfolio_sidecar = (
        freeze_repair_portfolio(
            portfolio,
            portfolio_dir,
        )
    )
    portfolio_file_sha = hashlib.sha256(
        portfolio_path.read_bytes()
    ).hexdigest()

    manifest = {
        "schema_id": (
            "HUMAN_REFERENCE_PLANNER_PRE_FREEZE_MANIFEST_V1"
        ),
        "schema_version": 1,
        "round_id": frozen_pre["round_id"],
        "human_planner_adjudication_sha256": (
            hashlib.sha256(
                canonical_json_bytes(approved)
            ).hexdigest()
        ),
        "human_pre_record_sha256": frozen_pre[
            "pre_record_sha256"
        ],
        "human_pre_freeze_receipt_path": str(
            pre_dir
            / "HUMAN_RESEARCHER_PRE_FREEZE_RECEIPT_V1.json"
        ),
        "repair_portfolio_file_sha256": portfolio_file_sha,
        "repair_portfolio_sidecar_path": str(
            portfolio_sidecar
        ),
        "strong_blind_input_sha256": artifacts[
            "strong_blind_input"
        ]["blind_input_sha256"],
        "reference_trace_sha256": artifacts[
            "reference_trace"
        ]["trace_sha256"],
        "selected_state_count": 12,
        "selected_candidate_count": 12,
        "selected_unique_group_count": 12,
        "paired_repetitions_per_state": 5,
        "total_branch_run_budget": 120,
        "human_pre_frozen": True,
        "strong_researcher_shadow_executed": False,
        "f0f1_executed": False,
        "training_executed": False,
        "success_trajectory_optimization_active": False,
        "manifest_sha256": "0" * 64,
        "next_gate": (
            "BLIND_STRONG_RESEARCHER_PRE_SHADOW_EXECUTION"
        ),
    }
    manifest["manifest_sha256"] = domain_hash(
        "HUMAN_REFERENCE_PLANNER_PRE_FREEZE_MANIFEST_V1",
        manifest,
        excluded_field="manifest_sha256",
    )
    write_new(
        output
        / "HUMAN_REFERENCE_PLANNER_PRE_FREEZE_MANIFEST_V1.json",
        manifest,
    )

    print(
        "HUMAN_PLANNER_ADJUDICATION_SHA256="
        + manifest["human_planner_adjudication_sha256"]
    )
    print(
        "HUMAN_PRE_RECORD_SHA256="
        + manifest["human_pre_record_sha256"]
    )
    print(
        "REPAIR_PORTFOLIO_FILE_SHA256="
        + portfolio_file_sha
    )
    print(
        "STRONG_RESEARCHER_BLIND_INPUT_SHA256="
        + manifest["strong_blind_input_sha256"]
    )
    print("HUMAN_PRE_FROZEN=true")
    print("STRONG_RESEARCHER_SHADOW_EXECUTED=false")
    print(
        "NEXT_GATE="
        "BLIND_STRONG_RESEARCHER_PRE_SHADOW_EXECUTION"
    )


if __name__ == "__main__":
    main()
