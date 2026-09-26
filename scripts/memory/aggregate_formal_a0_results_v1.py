#!/usr/bin/env python3
"""Aggregate exactly twelve resolved Formal-A cells into local paired effects.

Every selected result is revalidated cryptographically and against the frozen manifest
before it enters the scientific aggregation.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    strict_json_loads,
)
from pchsi.memory.a0_formal_execution import (
    A0CellResultV1,
    validate_cell_result_against_frozen_cell_v1,
)
from pchsi.memory.scientific_validation import (
    classify_local_paired_effect_v1,
)


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--cells-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    manifest = strict_json_loads(Path(args.manifest).read_bytes())
    if not isinstance(manifest, dict):
        raise SystemExit("STOP=A0_MANIFEST_NOT_OBJECT")
    cells = manifest.get("cells")
    if not isinstance(cells, list) or len(cells) != 12:
        raise SystemExit("STOP=A0_MANIFEST_NOT_12_CELLS")

    root = Path(args.cells_root)
    if root.is_symlink() or not root.is_dir():
        raise SystemExit("STOP=A0_CELLS_ROOT_INVALID")

    results = {}
    rows = []
    selected_attempts = []

    for index, cell in enumerate(cells):
        cell_root = root / f"cell_{index:02d}"
        result_path = cell_root / "cell_result.json"
        selected_path = cell_root / "resolved_attempt.json"

        if (
            not result_path.is_file()
            or result_path.is_symlink()
            or not selected_path.is_file()
            or selected_path.is_symlink()
        ):
            raise SystemExit(f"STOP=MISSING_RESOLVED_CELL_{index:02d}")

        selected = strict_json_loads(selected_path.read_bytes())
        expected_selected_keys = {
            "schema_id",
            "schema_version",
            "cell_index",
            "attempt_index",
            "attempt_relative_directory",
            "cell_result_file_sha256",
        }
        if (
            not isinstance(selected, dict)
            or set(selected) != expected_selected_keys
            or selected["schema_id"] != "FORMAL_A0_RESOLVED_ATTEMPT_V1"
            or selected["schema_version"] != 1
            or selected["cell_index"] != index
            or type(selected["attempt_index"]) is not int
            or selected["attempt_index"] < 0
        ):
            raise SystemExit("STOP=RESOLVED_ATTEMPT_BINDING_INVALID")

        expected_rel = "attempt_" + str(selected["attempt_index"]).zfill(3)
        if selected["attempt_relative_directory"] != expected_rel:
            raise SystemExit("STOP=RESOLVED_ATTEMPT_DIRECTORY_IDENTITY_MISMATCH")
        if selected["cell_result_file_sha256"] != _sha(result_path):
            raise SystemExit("STOP=RESOLVED_CELL_RESULT_FILE_SHA_MISMATCH")

        attempt_root = cell_root / expected_rel
        attempt_result = attempt_root / "cell_result.json"
        attempt_evidence = attempt_root / "cell_evidence.json"
        if (
            not attempt_result.is_file()
            or attempt_result.is_symlink()
            or not attempt_evidence.is_file()
            or attempt_evidence.is_symlink()
        ):
            raise SystemExit("STOP=RESOLVED_ATTEMPT_EVIDENCE_MISSING")
        if attempt_result.read_bytes() != result_path.read_bytes():
            raise SystemExit("STOP=RESOLVED_RESULT_COPY_DIFFERS_FROM_ATTEMPT")

        payload = strict_json_loads(result_path.read_bytes())
        result = A0CellResultV1.from_dict(payload)
        validate_cell_result_against_frozen_cell_v1(
            result=result,
            cell=cell,
        )
        if not result.scientific_outcome_produced or result.terminal_success is None:
            raise SystemExit("STOP=UNRESOLVED_CELL_NOT_AGGREGATABLE")

        evidence = strict_json_loads(attempt_evidence.read_bytes())
        if (
            not isinstance(evidence, dict)
            or evidence.get("schema_id") != "FORMAL_A0_CELL_EVIDENCE_V1"
            or evidence.get("cell_index") != index
            or evidence.get("attempt_index") != selected["attempt_index"]
            or evidence.get("cell") != cell
            or evidence.get("result") != result.to_dict()
        ):
            raise SystemExit("STOP=RESOLVED_ATTEMPT_EVIDENCE_BINDING_MISMATCH")

        transitions = evidence.get("continuation_transitions")
        if not isinstance(transitions, list):
            raise SystemExit("STOP=CONTINUATION_TRANSITION_LEDGER_MISSING")
        if len(transitions) != result.environment_step_count_from_source:
            raise SystemExit("STOP=CONTINUATION_TRANSITION_COUNT_MISMATCH")

        results[cell["cell_id"]] = result
        rows.append(result.to_dict())
        selected_attempts.append(selected)

    effects = []
    by_source = {}
    for cell in cells:
        by_source.setdefault(cell["source_state_id"], {})[
            cell["arm"]["arm_id"]
        ] = cell

    for source_id, arms in by_source.items():
        if set(arms) != {"M0", "M1", "M2", "M3"}:
            raise SystemExit("STOP=SOURCE_ARM_SET_MISMATCH")
        m0 = results[arms["M0"]["cell_id"]]
        for arm_id in ("M1", "M2", "M3"):
            other = results[arms[arm_id]["cell_id"]]
            effect = classify_local_paired_effect_v1(
                f0_success=m0.terminal_success,
                f1_success=other.terminal_success,
                scientific_execution_started=True,
                pre_result_infrastructure_failure=False,
                identity_resolved=True,
                evidence_complete=True,
            )
            effects.append(
                {
                    "source_state_id": source_id,
                    "baseline_arm": "M0",
                    "comparison_arm": arm_id,
                    **effect.to_dict(),
                }
            )

    arm_summary = {}
    for arm_id in ("M0", "M1", "M2", "M3"):
        values = [
            row.terminal_success
            for row in results.values()
            if row.arm_id == arm_id
        ]
        arm_summary[arm_id] = {
            "source_count": len(values),
            "task_success_count": sum(bool(x) for x in values),
            "authority": "DESCRIPTIVE_SOURCE_STATE_LOCAL_ONLY",
        }

    summary = {
        "schema_id": "FORMAL_A0_RESULT_SUMMARY_V1",
        "schema_version": 1,
        "cell_count": 12,
        "paired_effect_count": 9,
        "effect_scope": "SOURCE_STATE_LOCAL_PAIRED",
        "authority": "LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY",
        "paper_main_representation_claim_authorized": False,
        "a1_expanded_representation": "OPTIONAL_CONDITIONAL",
        "mechanism_effect_status": "NOT_EVALUATED_PENDING_REGISTERED_RULE",
        "arm_summary": arm_summary,
    }

    out = Path(args.output_root)
    if out.exists() or out.is_symlink():
        raise SystemExit("STOP=A0_AGGREGATE_OUTPUT_EXISTS")
    out.mkdir(parents=True, mode=0o700)

    _write_once(
        out / "A0_CELL_RESULTS_V1.jsonl",
        b"".join(canonical_json_bytes(x) for x in rows),
    )
    _write_once(
        out / "A0_SELECTED_ATTEMPTS_V1.jsonl",
        b"".join(canonical_json_bytes(x) for x in selected_attempts),
    )
    _write_once(
        out / "A0_EFFECT_LEDGER_V1.jsonl",
        b"".join(canonical_json_bytes(x) for x in effects),
    )
    _write_once(
        out / "A0_RESULT_SUMMARY_V1.json",
        canonical_json_bytes(summary),
    )

    audit = (
        "# Formal Package A Result Audit\n\n"
        "- 12/12 resolved cells required.\n"
        "- Each result SHA is reconstructed and verified.\n"
        "- Each result is rebound to manifest source/arm/seed identity.\n"
        "- Each selected attempt is bound to exact result bytes and cell evidence.\n"
        "- Continuation transition ledger count must equal post-source env-step count.\n"
        "- 9 within-source M0→M1/M2/M3 paired terminal effects.\n"
        "- Mechanism effect remains NOT_EVALUATED until a separate registered rule.\n"
        "- Authority: SOURCE_STATE_LOCAL_PAIRED only.\n"
        "- General structured-representation superiority claim: NOT AUTHORIZED.\n"
        "- A1 expanded representation: OPTIONAL_CONDITIONAL.\n"
    )
    _write_once(
        out / "A0_RESULT_AUDIT_V1.md",
        audit.encode("utf-8"),
    )

    print("FORMAL_A0_AGGREGATION_PASS")
    print("CELL_COUNT=12")
    print("PAIRED_EFFECT_COUNT=9")
    print("EFFECT_SCOPE=SOURCE_STATE_LOCAL_PAIRED")
    print("RESULT_INTEGRITY_REVALIDATION=PASS")
    print("MECHANISM_EFFECT_STATUS=NOT_EVALUATED_PENDING_REGISTERED_RULE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
