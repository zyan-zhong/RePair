#!/usr/bin/env python3
"""Export paper-ready Failure Memory tables and bounded narrative artifacts.

All claims are derived from sealed authorities and the truthful Q1--Q5 matrix.
The exporter never upgrades a claim and never treats an interface smoke/test as
scientific evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Iterable

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads
from pchsi.memory.scientific_authority import load_scientific_result_authority_v2
from pchsi.memory.scientific_decision import FM0, FM3, STAGE_1B, STAGE_2, STAGE_3


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


def canonical_object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=INPUT_NOT_REGULAR:" + str(path))
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or raw not in {canonical_json_bytes(value), canonical_json_bytes(value)}:
        raise SystemExit("STOP=INPUT_NOT_CANONICAL:" + str(path))
    return value


def write_bytes_new(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=PAPER_OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=PAPER_OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())


def supporting_path(authority_path: Path, row: dict[str, object]) -> Path:
    pure = PurePosixPath(str(row["path"]))
    if pure.is_absolute() or any(part in {".", ".."} for part in pure.parts):
        raise SystemExit("STOP=SUPPORT_PATH_INVALID")
    path = authority_path.parent.joinpath(*pure.parts)
    if path.is_symlink() or not path.is_file() or sha_file(path) != row["sha256"]:
        raise SystemExit("STOP=SUPPORT_ARTIFACT_INVALID:" + str(path))
    return path


def cell_results(authority_path: Path) -> list[dict[str, object]]:
    authority = canonical_object(authority_path)
    rows = []
    for binding in authority["supporting_artifacts"]:
        role = str(binding["role"])
        if not role.startswith("CELL_RESULT:"):
            continue
        rows.append(canonical_object(supporting_path(authority_path, binding)))
    return sorted(rows, key=lambda row: str(row["cell_id"]))


def decision_rows(stage: str, authority: dict[str, object]) -> list[dict[str, object]]:
    decision = authority["registered_statistical_decision"]
    rows = []
    for question, row in sorted(decision["question_decisions"].items()):
        rows.append({
            "stage": stage,
            "question": question,
            "disposition": row["disposition"],
            "scope": row["scope"],
            "summary": row["summary"],
            "decision_sha256": decision["decision_sha256"],
        })
    return rows


def paired_harm_cell_ids(
    stage_key: str,
    rows: list[dict[str, object]],
) -> set[str]:
    harmful: set[str] = set()
    if stage_key in {"stage1b", "stage3"}:
        groups: dict[
            tuple[str, str], dict[str, dict[str, object]]
        ] = defaultdict(dict)
        for row in rows:
            key = (str(row["split"]), str(row["comparison_group_id"]))
            groups[key][str(row["condition"])] = row
        for members in groups.values():
            if FM0 not in members or FM3 not in members:
                continue
            if bool(members[FM0]["success"]) and not bool(members[FM3]["success"]):
                harmful.add(str(members[FM3]["cell_id"]))
        return harmful

    if stage_key != "stage2":
        raise ValueError("unknown stage key")

    groups: dict[str, dict[int, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        groups[str(row["comparison_group_id"])][int(row["round_index"])] = row
    for members in groups.values():
        rounds = sorted(members)
        if not rounds or rounds[0] != 0:
            continue
        baseline = members[0]
        for round_index in rounds[1:]:
            treatment = members[round_index]
            if bool(baseline["success"]) and not bool(treatment["success"]):
                harmful.add(str(treatment["cell_id"]))
    return harmful


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage0-result", required=True)
    parser.add_argument("--a0-result", required=True)
    parser.add_argument("--b-result", required=True)
    parser.add_argument("--stage1b-authority", required=True)
    parser.add_argument("--stage2-authority", required=True)
    parser.add_argument("--stage3-authority", required=True)
    parser.add_argument("--q1-q5-matrix", required=True)
    parser.add_argument("--expected-fixed-head", required=True)
    parser.add_argument("--expected-scientific-program-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output = Path(args.output_dir)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=PAPER_OUTPUT_ROOT_EXISTS")
    output.mkdir(parents=True, mode=0o700)

    source_paths = {
        "stage0": Path(args.stage0_result),
        "a0": Path(args.a0_result),
        "b": Path(args.b_result),
        "stage1b": Path(args.stage1b_authority),
        "stage2": Path(args.stage2_authority),
        "stage3": Path(args.stage3_authority),
        "q1_q5": Path(args.q1_q5_matrix),
    }
    for path in source_paths.values():
        canonical_object(path)

    for stage, key in ((STAGE_1B, "stage1b"), (STAGE_2, "stage2"), (STAGE_3, "stage3")):
        load_scientific_result_authority_v2(
            path=source_paths[key],
            expected_stage=stage,
            expected_fixed_code_head=args.expected_fixed_head,
            expected_scientific_program_sha256=args.expected_scientific_program_sha256,
        )

    stage0 = canonical_object(source_paths["stage0"])
    a0 = canonical_object(source_paths["a0"])
    b = canonical_object(source_paths["b"])
    matrix = canonical_object(source_paths["q1_q5"])
    validate_matrix(matrix)
    authorities = {key: canonical_object(source_paths[key]) for key in ("stage1b", "stage2", "stage3")}
    cells = {key: cell_results(source_paths[key]) for key in ("stage1b", "stage2", "stage3")}
    paired_harm_ids = {
        key: paired_harm_cell_ids(key, rows)
        for key, rows in cells.items()
    }

    table_dir = output / "paper_tables"
    narrative_dir = output / "paper_narrative"

    representation_rows = []
    for row in cells["stage1b"] + cells["stage3"]:
        key = "stage1b" if row["stage"] == STAGE_1B else "stage3"
        direct_gold = key == "stage1b"
        representation_rows.append({
            "stage": row["stage"], "split": row["split"],
            "comparison_group_id": row["comparison_group_id"], "task_id": row["task_id"],
            "task_family": row["task_family"], "condition": row["condition"],
            "success": int(bool(row["success"])), "memory_exposed": int(bool(row["memory_exposed"])),
            "correct_memory_exposure": (
                int(bool(row["correct_memory_exposure"])) if direct_gold else None
            ),
            "harm_observed": int(str(row["cell_id"]) in paired_harm_ids[key]),
            "exposure_label_authority": (
                "REGISTERED_DIRECT_GOLD_V1"
                if direct_gold
                else "NOT_EVALUATED_NO_REGISTERED_GOLD_V1"
            ),
            "harm_authority": "PAIRED_TASK_SUCCESS_V1",
            "memory_tokens": row["memory_tokens"], "prompt_tokens": row["prompt_tokens"],
            "model_calls": row["model_calls"], "environment_steps": row["environment_steps"],
            "latency_ms": row["latency_ms"],
        })
    write_csv(table_dir / "memory_representation_ablation.csv", list(representation_rows[0]), representation_rows)

    retrieval_rows = [{
        "source": "FORMAL_B",
        "row_count": b.get("registered_safety_stress_metrics", {}).get("row_count"),
        "coverage_count": b.get("registered_safety_stress_metrics", {}).get("coverage", {}).get("numerator"),
        "correct_exposure_count": b.get("registered_safety_stress_metrics", {}).get("correct_exposure_count"),
        "wrong_exposure_count": b.get("registered_safety_stress_metrics", {}).get("wrong_exposure_count"),
        "unsafe_exposure_count": b.get("registered_safety_stress_metrics", {}).get("unsafe_exposure_count"),
        "harm_count": None,
        "abstention_count": b.get("registered_safety_stress_metrics", {}).get("abstention_count"),
        "exposure_label_authority": "FORMAL_B_REGISTERED_GOLD_V1",
        "harm_authority": "NOT_APPLICABLE_OFFLINE_RETRIEVAL",
        "note": "sealed pre-live retrieval authority",
    }]
    for key in ("stage1b", "stage2", "stage3"):
        metrics = authorities[key]["registered_statistical_decision"]["effect_estimates"]
        safety = metrics.get("q3_safety_utility") or metrics.get("last_round_safety_utility")
        if safety:
            retrieval_rows.append({
                "source": key.upper(), "row_count": safety["row_count"],
                "coverage_count": safety["coverage_count"],
                "correct_exposure_count": safety["correct_exposure_count"],
                "wrong_exposure_count": safety["wrong_exposure_count"],
                "unsafe_exposure_count": safety["unsafe_exposure_count"],
                "harm_count": safety["harm_count"],
                "abstention_count": safety["abstention_count"],
                "exposure_label_authority": safety["exposure_label_authority"],
                "harm_authority": safety["harm_authority"],
                "note": "live registered stage",
            })
    write_csv(table_dir / "retrieval_applicability_safety.csv", list(retrieval_rows[0]), retrieval_rows)

    system_rows = []
    for key in ("stage1b", "stage2", "stage3"):
        system_rows.extend(decision_rows(key.upper(), authorities[key]))
    write_csv(table_dir / "memory_system_effect.csv", list(system_rows[0]), system_rows)

    round_rows = []
    for round_index, row in authorities["stage2"]["registered_statistical_decision"]["effect_estimates"]["per_round"].items():
        round_rows.append({"round_index": round_index, **row})
    write_csv(table_dir / "multi_round_memory_curve.csv", [
        "round_index", "row_count", "success_count", "old_failure_repeated_count",
        "correct_exposure_count", "wrong_memory_count", "unsafe_memory_count",
        "harm_count", "exposure_label_authority", "harm_authority",
        "snapshot_sha256s",
    ], [{**r, "snapshot_sha256s": "|".join(r["snapshot_sha256s"])} for r in round_rows])

    family_rows = []
    for key, stage_rows in cells.items():
        grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
        for row in stage_rows:
            grouped[(str(row["task_family"]), str(row["condition"]), str(row["split"]))].append(row)
        for (family, condition, split), group in sorted(grouped.items()):
            direct_gold = key == "stage1b"
            family_rows.append({
                "stage": key.upper(), "task_family": family, "condition": condition, "split": split,
                "cell_count": len(group), "success_count": sum(bool(x["success"]) for x in group),
                "harm_count": sum(
                    str(x["cell_id"]) in paired_harm_ids[key] for x in group
                ),
                "wrong_memory_count": (
                    sum(bool(x["wrong_memory_exposure"]) for x in group)
                    if direct_gold else None
                ),
                "unsafe_memory_count": (
                    sum(bool(x["unsafe_memory_exposure"]) for x in group)
                    if direct_gold else None
                ),
                "exposure_label_authority": (
                    "REGISTERED_DIRECT_GOLD_V1"
                    if direct_gold
                    else "NOT_EVALUATED_NO_REGISTERED_GOLD_V1"
                ),
                "harm_authority": "PAIRED_TASK_SUCCESS_V1",
            })
    write_csv(table_dir / "task_family_breakdown.csv", list(family_rows[0]), family_rows)

    old_rows = []
    for key, stage_rows in cells.items():
        counts = Counter(str(row["old_failure_disposition"]) for row in stage_rows)
        for disposition, count in sorted(counts.items()):
            old_rows.append({"stage": key.upper(), "old_failure_disposition": disposition, "count": count})
    write_csv(table_dir / "old_failure_recurrence.csv", list(old_rows[0]), old_rows)

    adverse_rows = []
    for key, stage_rows in cells.items():
        direct_gold = key == "stage1b"
        for row in stage_rows:
            paired_harm = str(row["cell_id"]) in paired_harm_ids[key]
            wrong = bool(row["wrong_memory_exposure"]) if direct_gold else False
            unsafe = bool(row["unsafe_memory_exposure"]) if direct_gold else False
            if paired_harm or wrong or unsafe:
                adverse_rows.append({
                    "stage": key.upper(), "cell_id": row["cell_id"], "task_id": row["task_id"],
                    "task_family": row["task_family"], "condition": row["condition"],
                    "harm_observed": int(paired_harm),
                    "wrong_memory_exposure": int(wrong) if direct_gold else None,
                    "unsafe_memory_exposure": int(unsafe) if direct_gold else None,
                    "exposure_label_authority": (
                        "REGISTERED_DIRECT_GOLD_V1"
                        if direct_gold
                        else "NOT_EVALUATED_NO_REGISTERED_GOLD_V1"
                    ),
                    "harm_authority": "PAIRED_TASK_SUCCESS_V1",
                    "old_failure_disposition": row["old_failure_disposition"],
                })
    write_csv(table_dir / "adverse_and_wrong_memory_cases.csv", [
        "stage", "cell_id", "task_id", "task_family", "condition", "harm_observed",
        "wrong_memory_exposure", "unsafe_memory_exposure",
        "exposure_label_authority", "harm_authority",
        "old_failure_disposition",
    ], adverse_rows)

    cost_rows = []
    for key, stage_rows in cells.items():
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in stage_rows:
            grouped[str(row["condition"])].append(row)
        for condition, group in sorted(grouped.items()):
            cost_rows.append({
                "stage": key.upper(), "condition": condition, "cell_count": len(group),
                "model_calls": sum(int(x["model_calls"]) for x in group),
                "environment_steps": sum(int(x["environment_steps"]) for x in group),
                "memory_tokens": sum(int(x["memory_tokens"]) for x in group),
                "prompt_tokens": sum(int(x["prompt_tokens"]) for x in group),
                "latency_ms": sum(int(x["latency_ms"]) for x in group),
            })
    write_csv(table_dir / "memory_cost_and_efficiency.csv", list(cost_rows[0]), cost_rows)

    q_rows = []
    for row in matrix["rows"]:
        q_rows.append({
            "question_id": row["question_id"], "status": row["status"],
            "authorized_summary": row["authorized_summary"],
            "evidence_sha256s": "|".join(row["evidence_sha256s"]),
            "required_next_authorities": "|".join(row["required_next_authorities"]),
            "forbidden_claims": "|".join(row["forbidden_claims"]),
        })
    write_csv(table_dir / "q1_q5_claim_matrix.csv", list(q_rows[0]), q_rows)

    role_rows = []
    for key, stage_rows in cells.items():
        for role in ("policy", "analyzer", "researcher"):
            role_rows.append({
                "stage": key.upper(), "role": role,
                "cell_count": len(stage_rows),
                "pack_present_count": sum(row["role_pack_sha256s"][role] is not None for row in stage_rows),
            })
    role_rows.extend([
        {"stage": "STAGE0", "role": "policy", "cell_count": stage0.get("row_count", 0), "pack_present_count": stage0.get("policy_exposure_count", 0)},
        {"stage": "STAGE0", "role": "analyzer", "cell_count": stage0.get("analyzer_reference_positive_count", 0), "pack_present_count": stage0.get("analyzer_recall_at_3", {}).get("numerator", 0)},
        {"stage": "STAGE0", "role": "researcher", "cell_count": stage0.get("researcher_train_record_count", 0), "pack_present_count": stage0.get("researcher_train_record_count", 0)},
    ])
    write_csv(table_dir / "three_role_memory_access_audit.csv", list(role_rows[0]), role_rows)

    governance_rows = []
    for round_index, row in authorities["stage2"]["registered_statistical_decision"]["effect_estimates"]["per_round"].items():
        governance_rows.append({
            "round_index": round_index,
            "snapshot_sha256s": "|".join(row["snapshot_sha256s"]),
            "single_snapshot_within_round": int(len(row["snapshot_sha256s"]) == 1),
            "same_round_readback_count": sum(
                bool(cell["same_round_memory_readback"])
                for cell in cells["stage2"] if str(cell["round_index"]) == round_index
            ),
            "evaluation_writeback_attempt_count": sum(
                bool(cell["evaluation_writeback_attempted"])
                for cell in cells["stage2"] if str(cell["round_index"]) == round_index
            ),
        })
    write_csv(table_dir / "round_snapshot_governance.csv", list(governance_rows[0]), governance_rows)

    statuses = {row["question_id"]: row["status"] for row in matrix["rows"]}
    summary_lines = [
        "# Failure Memory V1 Results Summary",
        "",
        "This document is mechanically generated from sealed authorities.",
        "",
        "## Question status",
        "",
    ] + [f"- {qid}: `{statuses[qid]}`" for qid in ("Q1", "Q2", "Q3", "Q4", "Q5")]
    summary_lines += [
        "", "## Existing sealed negative results", "",
        f"- Formal A0 authority: `{a0.get('authority')}`; effect counts `{a0.get('effect_counts')}`.",
        f"- Formal B authority: `{b.get('authority')}`; coverage remains bounded by the sealed result.",
        "", "## Role separation", "",
        "Policy, Analyzer, and Researcher packs are separately bound for every live cell.",
        "Analyzer/Researcher access does not grant environment action or Benefit/Harm authority.",
    ]
    write_bytes_new(narrative_dir / "FAILURE_MEMORY_RESULTS_SUMMARY.md", ("\n".join(summary_lines) + "\n").encode())
    write_bytes_new(narrative_dir / "MEMORY_CLAIM_BOUNDARIES.md", (
        "# Memory Claim Boundaries\n\n"
        "- Q1--Q3 may change only through validated Memory-owned authorities.\n"
        "- Q4 requires a separately implemented Analyzer plus same-state verifier experiment.\n"
        "- Q5 requires real training and Memory-OFF/Harness-OFF evaluation.\n"
        "- Unit tests and role-view smokes are engineering evidence, not scientific outcomes.\n"
    ).encode())
    write_bytes_new(narrative_dir / "MEMORY_NEGATIVE_RESULTS.md", (
        "# Memory Negative Results\n\n"
        f"Formal A0: `{json.dumps(a0.get('effect_counts'), sort_keys=True)}`.\n\n"
        f"Formal B selected coverage: `{json.dumps(b.get('registered_safety_stress_metrics', {}).get('coverage'), sort_keys=True)}`.\n"
    ).encode())
    write_bytes_new(narrative_dir / "MEMORY_CASE_STUDIES.md", (
        "# Memory Case Studies\n\n"
        "See `adverse_and_wrong_memory_cases.csv` and the bound cell-result artifacts. "
        "No free-form causal explanation is invented by this exporter.\n"
    ).encode())
    write_bytes_new(narrative_dir / "MEMORY_LIMITATIONS.md", (
        "# Memory Limitations\n\n"
        "- valid_unseen remains a standard OOD benchmark with historical project exposure.\n"
        "- Q4 and Q5 remain outside Memory-only authority.\n"
        "- Any inconclusive registered decision remains inconclusive.\n"
    ).encode())
    write_bytes_new(narrative_dir / "ANALYZER_RESEARCHER_HANDOFF.md", (
        "# Analyzer and Training Researcher Handoff\n\n"
        "Memory supplies governed, content-addressed evidence packs. The Hierarchical Analyzer "
        "may diagnose and propose repairs; the Training Researcher may consume round evidence "
        "and plan later experiments. Neither may overwrite verifier outcomes or formal evaluation evidence.\n"
    ).encode())

    generated = []
    for path in sorted(p for p in output.rglob("*") if p.is_file()):
        generated.append({
            "path": path.relative_to(output).as_posix(), "sha256": sha_file(path),
            "size_bytes": path.stat().st_size,
        })
    manifest = {
        "schema_id": "FAILURE_MEMORY_PAPER_EVIDENCE_MANIFEST_V1",
        "schema_version": 1,
        "fixed_code_head": args.expected_fixed_head,
        "scientific_program_sha256": args.expected_scientific_program_sha256,
        "source_authorities": {
            name: {"path": str(path), "sha256": sha_file(path)} for name, path in source_paths.items()
        },
        "generated_artifacts": generated,
        "claim_statuses": statuses,
        "paper_evidence_manifest_sha256": "0" * 64,
    }
    manifest["paper_evidence_manifest_sha256"] = hashlib.sha256(
        b"FAILURE_MEMORY_PAPER_EVIDENCE_MANIFEST_V1\0"
        + canonical_json_bytes({k: v for k, v in manifest.items() if k != "paper_evidence_manifest_sha256"})
    ).hexdigest()
    write_bytes_new(output / "PAPER_EVIDENCE_MANIFEST_V1.json", canonical_json_bytes(manifest))
    print("FAILURE_MEMORY_PAPER_EVIDENCE_EXPORT_V2_PASS")
    print("OUTPUT_DIR=" + str(output))
    print("PAPER_EVIDENCE_MANIFEST_SHA256=" + manifest["paper_evidence_manifest_sha256"])


if __name__ == "__main__":
    main()
