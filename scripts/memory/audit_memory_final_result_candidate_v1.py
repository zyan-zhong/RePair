#!/usr/bin/env python3
"""Build a deterministic post-result audit candidate before human seal approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.scientific_authority import load_scientific_result_authority_v2
from pchsi.memory.scientific_decision import STAGE_1B, STAGE_2, STAGE_3


def object_value(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise SystemExit("STOP=AUDIT_CANDIDATE_OBJECT_NOT_CANONICAL:" + str(path))
    return value


def write_new(path: Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=AUDIT_CANDIDATE_OUTPUT_EXISTS")
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def validate_paper_evidence_manifest_v1(
    *,
    paper_manifest_path: Path,
    paper: dict[str, object],
    expected_fixed_head: str,
    expected_scientific_program_sha256: str,
) -> int:
    expected_fields = {
        "schema_id",
        "schema_version",
        "fixed_code_head",
        "scientific_program_sha256",
        "source_authorities",
        "generated_artifacts",
        "claim_statuses",
        "paper_evidence_manifest_sha256",
    }
    if set(paper) != expected_fields:
        raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_MANIFEST_FIELDS")
    if (
        paper.get("schema_id")
        != "FAILURE_MEMORY_PAPER_EVIDENCE_MANIFEST_V1"
        or paper.get("schema_version") != 1
    ):
        raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_MANIFEST_SCHEMA")
    if paper.get("fixed_code_head") != expected_fixed_head:
        raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_FIXED_HEAD")
    if (
        paper.get("scientific_program_sha256")
        != expected_scientific_program_sha256
    ):
        raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_PROGRAM")

    observed = paper.get("paper_evidence_manifest_sha256")
    if not isinstance(observed, str):
        raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_MANIFEST_SHA")
    expected = hashlib.sha256(
        b"FAILURE_MEMORY_PAPER_EVIDENCE_MANIFEST_V1\0"
        + canonical_json_bytes(
            {
                key: value
                for key, value in paper.items()
                if key != "paper_evidence_manifest_sha256"
            }
        )
    ).hexdigest()
    if observed != expected:
        raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_MANIFEST_SELF_HASH")

    artifacts = paper.get("generated_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_ARTIFACTS_EMPTY")

    root = paper_manifest_path.parent.resolve()
    seen: set[str] = set()
    for row in artifacts:
        if not isinstance(row, dict) or set(row) != {
            "path",
            "sha256",
            "size_bytes",
        }:
            raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_ARTIFACT_ROW")
        rel = row.get("path")
        if (
            not isinstance(rel, str)
            or not rel
            or rel in seen
            or Path(rel).is_absolute()
            or ".." in Path(rel).parts
        ):
            raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_ARTIFACT_PATH")
        seen.add(rel)
        target = root / rel
        if target.is_symlink() or not target.is_file():
            raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_ARTIFACT_MISSING")
        if target.resolve().parent != (root / rel).resolve().parent:
            raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_ARTIFACT_PATH")
        if sha256_file(target) != row.get("sha256"):
            raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_ARTIFACT_SHA")
        if target.stat().st_size != row.get("size_bytes"):
            raise SystemExit("STOP=AUDIT_CANDIDATE_PAPER_ARTIFACT_SIZE")

    return len(artifacts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closure-root", required=True)
    parser.add_argument("--expected-fixed-head", required=True)
    parser.add_argument("--expected-scientific-program-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    root = Path(args.closure_root)
    out = Path(args.output_dir)
    if out.exists() or out.is_symlink():
        raise SystemExit("STOP=AUDIT_CANDIDATE_OUTPUT_DIR_EXISTS")
    out.mkdir(parents=True)

    matrix_path = root / "FAILURE_MEMORY_Q1_Q5_MATRIX_V1.json"
    paper_manifest = root / "paper_evidence/PAPER_EVIDENCE_MANIFEST_V1.json"
    closure_path = (
        root
        / "handoff_and_closure/FAILURE_MEMORY_MODULE_CLOSURE_V1.json"
    )
    for path in (matrix_path, paper_manifest, closure_path):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("STOP=AUDIT_CANDIDATE_ARTIFACT_MISSING:" + str(path))

    authorities = {}
    for name, stage in (
        ("stage1b", STAGE_1B),
        ("stage2", STAGE_2),
        ("stage3", STAGE_3),
    ):
        path = root / "stage_authorities" / name / "RESULT_AUTHORITY_V2.json"
        authorities[name] = load_scientific_result_authority_v2(
            path=path,
            expected_stage=stage,
            expected_fixed_code_head=args.expected_fixed_head,
            expected_scientific_program_sha256=(
                args.expected_scientific_program_sha256
            ),
        )

    matrix = object_value(matrix_path)
    rows = matrix.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("STOP=AUDIT_CANDIDATE_MATRIX_ROWS")
    statuses = {
        str(row["question_id"]): str(row["status"])
        for row in rows
    }
    if set(statuses) != {"Q1", "Q2", "Q3", "Q4", "Q5"}:
        raise SystemExit("STOP=AUDIT_CANDIDATE_MATRIX_QUESTION_SET")
    if statuses["Q4"] not in {"OPEN", "READY_FOR_ANALYZER_VERIFIER_STAGE"}:
        raise SystemExit("STOP=AUDIT_CANDIDATE_Q4_OVERCLAIM")
    if statuses["Q5"] not in {
        "DEFERRED_OPTIONAL_EXTENSION",
        "READY_FOR_VERIFIED_TRAINING_STAGE",
    }:
        raise SystemExit("STOP=AUDIT_CANDIDATE_Q5_OVERCLAIM")

    closure = object_value(closure_path)
    closure_text = json.dumps(closure, sort_keys=True)
    for forbidden in (
        '"analyzer_implemented":true',
        '"researcher_implemented":true',
        '"policy_training_performed":true',
    ):
        if forbidden in closure_text.replace(" ", "").lower():
            raise SystemExit("STOP=AUDIT_CANDIDATE_FUTURE_COMPONENT_OVERCLAIM")

    stage_rows = {}
    for name, authority in authorities.items():
        payload = dict(authority.result_payload)
        stage_rows[name] = {
            "authority_file_sha256": authority.file_sha256,
            "result_authority_sha256": authority.result_authority_sha256,
            "question_decisions": {
                key: dict(value)
                for key, value in authority.question_decisions.items()
            },
            "effect_estimates": dict(authority.effect_estimates),
            "scientific_stage": authority.stage,
        }

    paper = object_value(paper_manifest)
    paper_artifact_count = validate_paper_evidence_manifest_v1(
        paper_manifest_path=paper_manifest,
        paper=paper,
        expected_fixed_head=args.expected_fixed_head,
        expected_scientific_program_sha256=(
            args.expected_scientific_program_sha256
        ),
    )
    payload = {
        "schema_id": "FAILURE_MEMORY_FINAL_RESULT_AUDIT_CANDIDATE_V1",
        "schema_version": 1,
        "audit_candidate_sha256": "0" * 64,
        "fixed_head": args.expected_fixed_head,
        "scientific_program_sha256": (
            args.expected_scientific_program_sha256
        ),
        "stage_authorities": stage_rows,
        "q1_q5_statuses": statuses,
        "paper_evidence_manifest_sha256": sha256_file(paper_manifest),
        "paper_evidence_artifact_count": paper_artifact_count,
        "memory_implementation_complete": True,
        "memory_owned_scientific_stages_complete": True,
        "analyzer_implemented": False,
        "researcher_implemented": False,
        "policy_training_performed": False,
        "q4_handoff_only": True,
        "q5_handoff_only": True,
        "result_audit_approved": False,
        "required_human_gate": (
            "RESULT_AUDIT_APPROVED_FAILURE_MEMORY_V1_MEMORY_OWNED_CLOSURE_V2"
        ),
    }
    payload["audit_candidate_sha256"] = hashlib.sha256(
        b"FAILURE_MEMORY_FINAL_RESULT_AUDIT_CANDIDATE_V1\0"
        + canonical_json_bytes({
            key: value
            for key, value in payload.items()
            if key != "audit_candidate_sha256"
        })
    ).hexdigest()
    write_new(out / "MEMORY_FINAL_RESULT_AUDIT_CANDIDATE_V1.json", payload)

    lines = [
        "# Failure Memory V1 Final Result Audit Candidate",
        "",
        f"- Fixed head: `{args.expected_fixed_head}`",
        f"- Audit candidate SHA-256: `{payload['audit_candidate_sha256']}`",
        "- Memory-owned Stage 1B / 2 / 3 authorities: validated",
        "- Analyzer implemented: no",
        "- Researcher implemented: no",
        "- Policy training performed: no",
        "",
        "## Q1-Q5 matrix",
        "",
    ]
    for question in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        lines.append(f"- {question}: `{statuses[question]}`")
    lines.extend([
        "",
        "## Required decision",
        "",
        "Review the generated paper tables, negative results, adverse cases,",
        "Q1-Q5 matrix and all three result authorities. Only after that review",
        "may the frozen result-audit approval token be supplied to the seal script.",
        "",
    ])
    (out / "MEMORY_FINAL_RESULT_AUDIT_CANDIDATE_V1.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("FAILURE_MEMORY_FINAL_RESULT_AUDIT_CANDIDATE_V1_PASS")
    print("AUDIT_CANDIDATE_SHA256=" + payload["audit_candidate_sha256"])
    print("Q1=" + statuses["Q1"])
    print("Q2=" + statuses["Q2"])
    print("Q3=" + statuses["Q3"])
    print("Q4=" + statuses["Q4"])
    print("Q5=" + statuses["Q5"])
    print("RESULT_AUDIT_APPROVED=false")
    print(
        "NEXT=REVIEW_RESULTS_THEN_RUN_"
        "MEMORY_FINAL_SEAL_AFTER_RESULT_AUDIT"
    )


if __name__ == "__main__":
    main()
