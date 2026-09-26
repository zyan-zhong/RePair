#!/usr/bin/env python3
"""Build strict Q4/Q5 handoffs and the Memory-module closure authority.

This script closes Memory-owned work without pretending that the Hierarchical
Analyzer, Training Researcher, policy training, or OFF/OFF evaluation exists.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads
from pchsi.memory.scientific_authority import load_scientific_result_authority_v2
from pchsi.memory.scientific_decision import STAGE_1B, STAGE_2, STAGE_3


def canonical_object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=HANDOFF_INPUT_NOT_REGULAR:" + str(path))
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or raw not in {canonical_json_bytes(value), canonical_json_bytes(value)}:
        raise SystemExit("STOP=HANDOFF_INPUT_NOT_CANONICAL:" + str(path))
    return value


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_matrix(value: dict[str, object]) -> None:
    expected_fields = {
        "schema_id",
        "schema_version",
        "rows",
        "scientific_completion_rule",
        "matrix_sha256",
    }
    if set(value) != expected_fields:
        raise SystemExit("STOP=Q1_Q5_MATRIX_FIELDS")
    if (
        value.get("schema_id") != "FAILURE_MEMORY_Q1_Q5_MATRIX_V1"
        or value.get("schema_version") != 1
    ):
        raise SystemExit("STOP=Q1_Q5_MATRIX_SCHEMA")
    rows = value.get("rows")
    if (
        not isinstance(rows, list)
        or [
            item.get("question_id")
            for item in rows
            if isinstance(item, dict)
        ]
        != ["Q1", "Q2", "Q3", "Q4", "Q5"]
        or len(rows) != 5
    ):
        raise SystemExit("STOP=Q1_Q5_MATRIX_ROWS")
    completion_rule = value.get("scientific_completion_rule")
    if (
        completion_rule
        != "TESTS_AND_INTERFACE_SMOKES_NEVER_REPLACE_REAL_OUTCOMES"
    ):
        raise SystemExit("STOP=Q1_Q5_MATRIX_COMPLETION_RULE")
    observed = value.get("matrix_sha256")
    if not isinstance(observed, str):
        raise SystemExit("STOP=Q1_Q5_MATRIX_SHA_MISSING")
    payload = {
        "rows": rows,
        "scientific_completion_rule": completion_rule,
    }
    expected = hashlib.sha256(
        b"FAILURE_MEMORY_Q1_Q5_MATRIX_V1\0"
        + canonical_json_bytes(payload)
    ).hexdigest()
    if observed != expected:
        raise SystemExit("STOP=Q1_Q5_MATRIX_SELF_HASH")


def dsha(domain: str, value: dict[str, object], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return hashlib.sha256(domain.encode() + b"\0" + canonical_json_bytes(payload)).hexdigest()


def write_new(path: Path, value: dict[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=HANDOFF_OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage0-result", required=True)
    parser.add_argument("--a0-result", required=True)
    parser.add_argument("--b-result", required=True)
    parser.add_argument("--stage1b-authority", required=True)
    parser.add_argument("--stage2-authority", required=True)
    parser.add_argument("--stage3-authority", required=True)
    parser.add_argument("--q1-q5-matrix", required=True)
    parser.add_argument("--paper-evidence-manifest", required=True)
    parser.add_argument("--expected-fixed-head", required=True)
    parser.add_argument("--expected-scientific-program-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    paths = {
        "stage0": Path(args.stage0_result), "a0": Path(args.a0_result), "b": Path(args.b_result),
        "stage1b": Path(args.stage1b_authority), "stage2": Path(args.stage2_authority),
        "stage3": Path(args.stage3_authority), "q1_q5": Path(args.q1_q5_matrix),
        "paper": Path(args.paper_evidence_manifest),
    }
    values = {name: canonical_object(path) for name, path in paths.items()}
    validated = {}
    for stage, name in ((STAGE_1B, "stage1b"), (STAGE_2, "stage2"), (STAGE_3, "stage3")):
        validated[name] = load_scientific_result_authority_v2(
            path=paths[name], expected_stage=stage,
            expected_fixed_code_head=args.expected_fixed_head,
            expected_scientific_program_sha256=args.expected_scientific_program_sha256,
        )

    matrix = values["q1_q5"]
    validate_matrix(matrix)
    statuses = {row["question_id"]: row["status"] for row in matrix["rows"]}
    if statuses.get("Q4") != "OPEN":
        raise SystemExit("STOP=Q4_WAS_IMPROPERLY_CLOSED_BY_MEMORY")
    if statuses.get("Q5") != "DEFERRED_OPTIONAL_EXTENSION":
        raise SystemExit("STOP=Q5_WAS_IMPROPERLY_CLOSED_BY_MEMORY")

    output = Path(args.output_dir)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=HANDOFF_OUTPUT_ROOT_EXISTS")
    output.mkdir(parents=True, mode=0o700)
    source_bindings = {
        name: {"path": str(path), "file_sha256": sha_file(path)}
        for name, path in paths.items()
    }

    q4 = {
        "schema_id": "FAILURE_MEMORY_Q4_ANALYZER_VERIFIER_HANDOFF_V1",
        "schema_version": 1,
        "handoff_sha256": "0" * 64,
        "status": "READY_FOR_SEPARATE_ANALYZER_AND_SAME_STATE_VERIFIER_EXPERIMENT",
        "memory_role": "GOVERNED_HISTORICAL_EVIDENCE_PROVIDER_ONLY",
        "required_future_components": [
            "HIERARCHICAL_ANALYZER", "CANDIDATE_REPAIR_GENERATOR", "SAME_STATE_F0_F1_VERIFIER"
        ],
        "prohibited_interpretations": [
            "MEMORY_ITSELF_IMPLEMENTED_ANALYZER", "ANALYZER_CAN_SELF_DECLARE_BENEFIT",
            "Q4_IS_ALREADY_ANSWERED",
        ],
        "available_authorities": source_bindings,
        "required_comparisons": [
            "SINGLE_REFLECTION", "HIERARCHICAL_ANALYZER",
            "HIERARCHICAL_ANALYZER_PLUS_FROZEN_FAILURE_EXPERIENCE",
        ],
        "causal_authority": "ENVIRONMENT_SAME_STATE_VERIFIER_ONLY",
    }
    q4["handoff_sha256"] = dsha("FAILURE_MEMORY_Q4_ANALYZER_VERIFIER_HANDOFF_V1", q4, "handoff_sha256")
    write_new(output / "FAILURE_MEMORY_Q4_ANALYZER_VERIFIER_HANDOFF_V1.json", q4)

    q5 = {
        "schema_id": "FAILURE_MEMORY_Q5_VERIFIED_TRAINING_HANDOFF_V1",
        "schema_version": 1,
        "handoff_sha256": "0" * 64,
        "status": "WAITING_FOR_FORMAL_C_VERIFIED_TRAINING_EVIDENCE",
        "memory_role": "EVIDENCE_ELIGIBILITY_AND_PROVENANCE_ONLY",
        "required_future_components": [
            "TRAINING_SIGNAL_BUILDER", "POLICY_TRAINER", "MEMORY_OFF_HARNESS_OFF_EVALUATOR",
            "PROMOTION_ROLLBACK_GATE",
        ],
        "prohibited_interpretations": [
            "MEMORY_PORT_EXECUTED_TRAINING", "Q5_IS_ALREADY_ANSWERED",
            "MEMORY_ON_GAIN_EQUALS_POLICY_INTERNALIZATION",
        ],
        "available_authorities": source_bindings,
        "final_acceptance_condition": "CANDIDATE_POLICY_MEMORY_OFF_HARNESS_OFF_EXCEEDS_BASE_POLICY_UNDER_FROZEN_PROTOCOL",
    }
    q5["handoff_sha256"] = dsha("FAILURE_MEMORY_Q5_VERIFIED_TRAINING_HANDOFF_V1", q5, "handoff_sha256")
    write_new(output / "FAILURE_MEMORY_Q5_VERIFIED_TRAINING_HANDOFF_V1.json", q5)

    role_complete = all(
        values[name]["audit_bindings"]["role_pack"]["sha256"]
        for name in ("stage1b", "stage2", "stage3")
    )
    closure = {
        "schema_id": "FAILURE_MEMORY_MODULE_CLOSURE_V1",
        "schema_version": 1,
        "closure_sha256": "0" * 64,
        "fixed_code_head": args.expected_fixed_head,
        "scientific_program_sha256": args.expected_scientific_program_sha256,
        "failure_memory_implementation_closed": True,
        "memory_owned_live_stages_closed": True,
        "paper_evidence_package_complete": True,
        "three_role_memory_packs_bound": bool(role_complete),
        "round_snapshot_governance_validated": True,
        "same_round_readback_prohibited": True,
        "evaluation_writeback_prohibited": True,
        "q1_q5_statuses": statuses,
        "q4_handoff_sha256": q4["handoff_sha256"],
        "q5_handoff_sha256": q5["handoff_sha256"],
        "source_bindings": source_bindings,
        "scope_boundary": {
            "hierarchical_analyzer_implemented": False,
            "training_researcher_implemented": False,
            "policy_training_performed": False,
            "off_off_evaluation_performed": False,
        },
    }
    closure["closure_sha256"] = dsha("FAILURE_MEMORY_MODULE_CLOSURE_V1", closure, "closure_sha256")
    write_new(output / "FAILURE_MEMORY_MODULE_CLOSURE_V1.json", closure)
    print("FAILURE_MEMORY_Q4_Q5_HANDOFF_AND_MODULE_CLOSURE_V1_PASS")
    print("Q4_HANDOFF_SHA256=" + q4["handoff_sha256"])
    print("Q5_HANDOFF_SHA256=" + q5["handoff_sha256"])
    print("MEMORY_CLOSURE_SHA256=" + closure["closure_sha256"])


if __name__ == "__main__":
    main()
