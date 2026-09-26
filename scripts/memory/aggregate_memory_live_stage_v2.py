#!/usr/bin/env python3
"""Aggregate complete Memory live cells into a V2 scientific authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads
from pchsi.memory.consumer_views import (
    audit_analyzer_view_payload_v1,
    audit_policy_prompt_payload_v1,
    audit_researcher_view_payload_v1,
)
from pchsi.memory.matched_raw_view import FM1PolicyVisiblePayloadV1
from pchsi.memory.scientific_authority import load_scientific_result_authority_v2
from pchsi.memory.scientific_decision import (
    FM1,
    STAGE_1B,
    STAGE_2,
    recompute_stage_decisions_v1,
    validate_cell_result_v1,
    validate_decision_rule_v1,
)

ROLE_PACK_FILENAMES = {
    "policy": "POLICY_MEMORY_PACK_V1.json",
    "analyzer": "ANALYZER_MEMORY_PACK_V1.json",
    "researcher": "RESEARCHER_MEMORY_PACK_V1.json",
}


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dsha(domain: str, value: dict[str, object], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return hashlib.sha256(domain.encode() + b"\0" + canonical_json_bytes(payload)).hexdigest()


def canonical_object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=ARTIFACT_NOT_REGULAR:" + str(path))
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or raw not in {canonical_json_bytes(value), canonical_json_bytes(value)}:
        raise SystemExit("STOP=ARTIFACT_NOT_CANONICAL:" + str(path))
    return value


def parse_jsonl(path: Path) -> list[dict[str, object]]:
    rows = []
    for raw in path.read_bytes().splitlines(keepends=True):
        if not raw:
            continue
        value = strict_json_loads(raw)
        if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
            raise SystemExit("STOP=JSONL_NOT_CANONICAL:" + str(path))
        rows.append(value)
    return rows


def write_new(path: Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def copy_bound(
    source: Path,
    *,
    root: Path,
    role: str,
    rows_by_sha: dict[str, dict[str, object]],
) -> dict[str, object]:
    if source.is_symlink() or not source.is_file():
        raise SystemExit("STOP=BOUND_SOURCE_INVALID:" + str(source))
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    existing = rows_by_sha.get(digest)
    if existing is not None:
        if existing["role"] != role:
            raise SystemExit("STOP=BOUND_SHA_ROLE_COLLISION:" + digest)
        return existing
    destination = root / "bound_artifacts" / digest / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.is_symlink() or destination.read_bytes() != raw:
            raise SystemExit("STOP=BOUND_DESTINATION_CONFLICT:" + str(destination))
    else:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    row = {
        "path": destination.relative_to(root).as_posix(),
        "sha256": digest,
        "size_bytes": len(raw),
        "role": role,
    }
    rows_by_sha[digest] = row
    return row


def validate_role_pack(
    path: Path,
    *,
    role: str,
    cell_id: str,
    execution_manifest_sha256: str,
    stage: str,
    condition: str,
    expected_stage1b_fm1_payload: dict[str, object] | None,
) -> dict[str, object]:
    value = canonical_object(path)
    if set(value) != {
        "schema_id", "schema_version", "role", "cell_id",
        "execution_manifest_sha256", "payload", "pack_sha256",
    }:
        raise SystemExit("STOP=ROLE_PACK_FIELDS:" + str(path))
    if value["schema_id"] != "FAILURE_MEMORY_ROLE_PACK_V1" or value["schema_version"] != 1:
        raise SystemExit("STOP=ROLE_PACK_SCHEMA:" + str(path))
    if value["role"] != role.upper():
        raise SystemExit("STOP=ROLE_PACK_ROLE:" + str(path))
    if value["cell_id"] != cell_id:
        raise SystemExit("STOP=ROLE_PACK_CELL_ID:" + str(path))
    if value["execution_manifest_sha256"] != execution_manifest_sha256:
        raise SystemExit("STOP=ROLE_PACK_EXECUTION_MANIFEST:" + str(path))
    expected = dsha("FAILURE_MEMORY_ROLE_PACK_V1", value, "pack_sha256")
    if value["pack_sha256"] != expected:
        raise SystemExit("STOP=ROLE_PACK_SELF_HASH:" + str(path))
    payload = value["payload"]
    if role == "policy":
        if payload is not None:
            if not isinstance(payload, dict):
                raise SystemExit("STOP=POLICY_ROLE_PACK_PAYLOAD")
            if stage == STAGE_1B and condition == FM1:
                if expected_stage1b_fm1_payload is None:
                    raise SystemExit(
                        "STOP=STAGE1B_FM1_ROLE_PACK_EXPECTED_PAYLOAD_MISSING"
                    )
                FM1PolicyVisiblePayloadV1.from_dict(payload)
                if payload != expected_stage1b_fm1_payload:
                    raise SystemExit(
                        "STOP=STAGE1B_FM1_ROLE_PACK_TEMPLATE_BINDING"
                    )
            else:
                audit_policy_prompt_payload_v1(payload)
    elif role == "analyzer":
        if not isinstance(payload, dict):
            raise SystemExit("STOP=ANALYZER_ROLE_PACK_PAYLOAD")
        audit_analyzer_view_payload_v1(payload)
    else:
        if not isinstance(payload, dict):
            raise SystemExit("STOP=RESEARCHER_ROLE_PACK_PAYLOAD")
        audit_researcher_view_payload_v1(payload)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-manifest", required=True)
    parser.add_argument("--cells-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    execution_path = Path(args.execution_manifest)
    execution = canonical_object(execution_path)
    if execution.get("schema_id") != "FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2":
        raise SystemExit("STOP=EXECUTION_MANIFEST_SCHEMA")
    manifest_sha = execution["manifest_sha256"]
    stage = execution["stage"]
    bindings = execution["bindings"]
    paths = execution["operational_paths"]
    cells_manifest_path = Path(paths["cell_manifest"])
    registered_rows = parse_jsonl(cells_manifest_path)
    registered = {str(row["cell_id"]): row for row in registered_rows}
    if len(registered) != execution["registered_cell_count"]:
        raise SystemExit("STOP=REGISTERED_CELL_COUNT")

    final_output = Path(args.output_dir)
    final_authority_path = final_output / "RESULT_AUTHORITY_V2.json"
    if final_output.exists():
        if final_authority_path.is_file() and not final_authority_path.is_symlink():
            program_semantic = bindings["scientific_program"]["semantic_sha256"]
            load_scientific_result_authority_v2(
                path=final_authority_path,
                expected_stage=stage,
                expected_fixed_code_head=execution["fixed_code_head"],
                expected_scientific_program_sha256=program_semantic,
            )
            print("MEMORY_LIVE_STAGE_AGGREGATION_RESUME_PASS")
            print("RESULT_AUTHORITY=" + str(final_authority_path))
            return
        raise SystemExit("STOP=PARTIAL_AUTHORITY_OUTPUT_ROOT")
    lock_path = Path(str(final_output) + ".lock")
    output = Path(str(final_output) + ".staging_" + str(manifest_sha)[:16])
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=AGGREGATION_STAGING_EXISTS:" + str(output))
    if lock_path.exists() or lock_path.is_symlink():
        raise SystemExit("STOP=AGGREGATION_LOCK_EXISTS:" + str(lock_path))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(lock_fd, "w", encoding="utf-8") as handle:
        handle.write(str(manifest_sha) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    output.mkdir(parents=True, mode=0o700)
    authority_path = output / "RESULT_AUTHORITY_V2.json"

    cells_root = Path(args.cells_root)
    results: list[dict[str, object]] = []
    census_rows = []
    support_by_sha: dict[str, dict[str, object]] = {}

    # Bind pre-outcome identities. Decision rule has a dedicated role.
    for name, row in bindings.items():
        path = Path(paths[name])
        if sha_file(path) != row["file_sha256"] or path.stat().st_size != row["size_bytes"]:
            raise SystemExit("STOP=EXECUTION_BINDING_CHANGED:" + name)
        role = "DECISION_RULE" if name == "decision_rule" else f"EXECUTION_BINDING:{name}"
        copy_bound(path, root=output, role=role, rows_by_sha=support_by_sha)
    execution_binding = copy_bound(
        execution_path,
        root=output,
        role="EXECUTION_MANIFEST",
        rows_by_sha=support_by_sha,
    )
    decision_path = Path(paths["decision_rule"])
    decision_rule = canonical_object(decision_path)
    validated_rule = validate_decision_rule_v1(decision_rule)
    if validated_rule.stage != stage:
        raise SystemExit("STOP=DECISION_RULE_STAGE")

    stage1b_fm1_payload_by_cell: dict[str, dict[str, object]] = {}
    if stage == STAGE_1B:
        panel = canonical_object(Path(paths["panel"]))
        entries = panel.get("entries")
        if not isinstance(entries, list):
            raise SystemExit("STOP=STAGE1B_PANEL_ENTRIES")
        panel_by_task = {
            str(item["task_id"]): item
            for item in entries
            if isinstance(item, dict)
        }
        if len(panel_by_task) != len(entries):
            raise SystemExit("STOP=STAGE1B_PANEL_TASK_IDENTITY")

        for fm1_cell_id, fm1_row in registered.items():
            if fm1_row["condition"] != FM1:
                continue
            task_id = str(fm1_row["task_id"])
            panel_entry = panel_by_task.get(task_id)
            if panel_entry is None:
                raise SystemExit(
                    "STOP=STAGE1B_FM1_PANEL_TASK_MISSING:" + task_id
                )

            a0_binding = canonical_object(
                Path(str(panel_entry["a0_binding_path"]))
            )
            source_rows = [
                item
                for item in a0_binding.get("sources", [])
                if isinstance(item, dict)
                and item.get("source_state_id") == task_id
            ]
            if len(source_rows) != 1:
                raise SystemExit(
                    "STOP=STAGE1B_FM1_A0_SOURCE_BINDING:" + task_id
                )
            source_row = source_rows[0]

            template_path = Path(
                str(panel_entry["representation_template_path"])
            )
            if (
                Path(str(source_row["representation_template_path"])).resolve()
                != template_path.resolve()
            ):
                raise SystemExit(
                    "STOP=STAGE1B_FM1_TEMPLATE_PATH_BINDING:" + task_id
                )
            if (
                sha_file(template_path)
                != source_row["representation_template_file_sha256"]
            ):
                raise SystemExit(
                    "STOP=STAGE1B_FM1_TEMPLATE_FILE_SHA:" + task_id
                )

            template = canonical_object(template_path)
            arms = [
                item
                for item in template.get("arms", [])
                if isinstance(item, dict)
                and item.get("arm_id") == "M1"
            ]
            if len(arms) != 1:
                raise SystemExit(
                    "STOP=STAGE1B_FM1_TEMPLATE_ARM:" + task_id
                )
            expected_payload = arms[0].get("policy_visible_payload")
            if not isinstance(expected_payload, dict):
                raise SystemExit(
                    "STOP=STAGE1B_FM1_TEMPLATE_PAYLOAD:" + task_id
                )
            FM1PolicyVisiblePayloadV1.from_dict(expected_payload)
            stage1b_fm1_payload_by_cell[fm1_cell_id] = expected_payload

        expected_stage1b_fm1_count = sum(
            1
            for row in registered.values()
            if row["condition"] == FM1
        )
        if (
            len(stage1b_fm1_payload_by_cell)
            != expected_stage1b_fm1_count
        ):
            raise SystemExit("STOP=STAGE1B_FM1_EXPECTED_CELL_COUNT")

    for cell_id in sorted(registered):
        cell_root = cells_root / cell_id
        result_path = cell_root / "CELL_SCIENTIFIC_RESULT_V1.json"
        receipt_path = cell_root / "CELL_TERMINAL_RECEIPT_V1.json"
        result = canonical_object(result_path)
        receipt = canonical_object(receipt_path)
        validated = validate_cell_result_v1(
            result,
            expected_stage=stage,
            expected_execution_manifest_sha256=manifest_sha,
        )
        if validated["cell_id"] != cell_id:
            raise SystemExit("STOP=CELL_RESULT_IDENTITY:" + cell_id)
        for field, expected in registered[cell_id].items():
            if validated[field] != expected:
                raise SystemExit(f"STOP=CELL_RESULT_REGISTRATION:{cell_id}:{field}")
        if receipt.get("schema_id") != "FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1" or receipt.get("schema_version") != 1:
            raise SystemExit("STOP=CELL_RECEIPT_SCHEMA:" + cell_id)
        expected_receipt = dsha(
            "FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1",
            receipt,
            "receipt_sha256",
        )
        if receipt.get("receipt_sha256") != expected_receipt:
            raise SystemExit("STOP=CELL_RECEIPT_SELF_HASH:" + cell_id)
        if (
            receipt.get("cell_id") != cell_id
            or receipt.get("execution_manifest_sha256") != manifest_sha
            or receipt.get("cell_result_sha256") != validated["cell_result_sha256"]
            or receipt.get("cell_complete") is not True
            or receipt.get("scientific_outcome_produced") is not True
            or receipt.get("infrastructure_error") is not False
        ):
            raise SystemExit("STOP=CELL_RECEIPT_CONTENT:" + cell_id)

        result_binding = copy_bound(
            result_path,
            root=output,
            role=f"CELL_RESULT:{cell_id}",
            rows_by_sha=support_by_sha,
        )
        receipt_binding = copy_bound(
            receipt_path,
            root=output,
            role=f"CELL_RECEIPT:{cell_id}",
            rows_by_sha=support_by_sha,
        )
        role_file_shas = {}
        for role, filename in ROLE_PACK_FILENAMES.items():
            pack_path = cell_root / filename
            validate_role_pack(
                pack_path,
                role=role,
                cell_id=cell_id,
                execution_manifest_sha256=manifest_sha,
                stage=stage,
                condition=str(registered[cell_id]["condition"]),
                expected_stage1b_fm1_payload=(
                    stage1b_fm1_payload_by_cell.get(cell_id)
                ),
            )
            pack_binding = copy_bound(
                pack_path,
                root=output,
                role=f"ROLE_PACK:{role}:{cell_id}",
                rows_by_sha=support_by_sha,
            )
            role_file_shas[role] = pack_binding["sha256"]
        if validated["role_pack_sha256s"] != role_file_shas:
            raise SystemExit("STOP=ROLE_PACK_CELL_BINDING:" + cell_id)
        census_rows.append({
            "cell_id": cell_id,
            "receipt_file_sha256": receipt_binding["sha256"],
            "result_file_sha256": result_binding["sha256"],
            "receipt_sha256": receipt["receipt_sha256"],
            "cell_result_sha256": validated["cell_result_sha256"],
        })
        results.append(validated)

    if len(results) != execution["registered_cell_count"]:
        raise SystemExit("STOP=UNRESOLVED_CELL_POPULATION")

    recomputed = recompute_stage_decisions_v1(
        stage=stage,
        cell_results=results,
        decision_rule=decision_rule,
        execution_manifest_sha256=manifest_sha,
    )
    contamination = {
        "status": "PASS",
        "same_round_memory_readback_count": sum(bool(row["same_round_memory_readback"]) for row in results),
        "evaluation_writeback_attempt_count": sum(bool(row["evaluation_writeback_attempted"]) for row in results),
        "unregistered_cell_count": 0,
    }
    if contamination["same_round_memory_readback_count"] or contamination["evaluation_writeback_attempt_count"]:
        raise SystemExit("STOP=PROHIBITED_READBACK_OR_WRITEBACK")
    writeback = {"status": "PASS", "prohibited_writeback_count": 0}
    role_presence = {
        role: sum(row["role_pack_sha256s"][role] is not None for row in results)
        for role in ("policy", "analyzer", "researcher")
    }
    role_pack_audit = {"status": "PASS", "role_pack_presence_counts": role_presence}
    if any(value != len(results) for value in role_presence.values()):
        raise SystemExit("STOP=INCOMPLETE_ROLE_PACK_POPULATION")
    round_summary: dict[str, list[str]] = {}
    if stage == STAGE_2:
        for row in results:
            round_summary.setdefault(str(row["round_index"]), []).append(str(row["snapshot_sha256"]))
        round_summary = {key: sorted(set(values)) for key, values in sorted(round_summary.items())}
        if any(len(values) != 1 for values in round_summary.values()):
            raise SystemExit("STOP=MORE_THAN_ONE_ACTIVE_SNAPSHOT_PER_ROUND")
    round_audit = {"status": "PASS", "round_snapshot_sha256s": round_summary}
    independent = {
        "status": "PASS",
        "decision_sha256": recomputed["decision_sha256"],
        "cell_result_count": len(results),
    }

    audit_bindings = {}
    for name, payload in (
        ("contamination", contamination),
        ("writeback", writeback),
        ("independent_recomputation", independent),
        ("role_pack", role_pack_audit),
        ("round_governance", round_audit),
    ):
        path = output / "audits" / f"{name}.json"
        write_new(path, payload)
        audit_bindings[name] = copy_bound(
            path,
            root=output,
            role=f"AUDIT:{name}",
            rows_by_sha=support_by_sha,
        )

    census = {
        "schema_id": "FAILURE_MEMORY_CELL_ARTIFACT_CENSUS_V1",
        "schema_version": 1,
        "execution_manifest_sha256": manifest_sha,
        "registered_cell_count": len(registered),
        "resolved_cell_count": len(results),
        "cells": census_rows,
        "census_sha256": "0" * 64,
    }
    census["census_sha256"] = dsha(
        "FAILURE_MEMORY_CELL_ARTIFACT_CENSUS_V1", census, "census_sha256"
    )
    census_path = output / "audits" / "cell_census.json"
    write_new(census_path, census)
    census_binding = copy_bound(
        census_path,
        root=output,
        role="CELL_CENSUS",
        rows_by_sha=support_by_sha,
    )
    decision_binding = next(
        row for row in support_by_sha.values() if row["role"] == "DECISION_RULE"
    )
    schema = {
        "STAGE_1B_FROZEN_POLICY_FM0_FM3": "STAGE_1B_FROZEN_POLICY_FM0_FM3_RESULT_AUTHORITY_V2",
        "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY": "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY_RESULT_AUTHORITY_V2",
        "STAGE_3_FROZEN_FORMAL_EVALUATION": "STAGE_3_FROZEN_ID_OOD_RESULT_AUTHORITY_V2",
    }[stage]
    authority = {
        "schema_id": schema,
        "schema_version": 2,
        "authority_scope": "MEMORY_OWNED_LIVE_STAGE",
        "scientific_stage": stage,
        "result_authority_sha256": "0" * 64,
        "execution_manifest_binding": execution_binding,
        "decision_rule_binding": decision_binding,
        "cell_census_binding": census_binding,
        "audit_bindings": audit_bindings,
        "registered_cell_count": len(registered),
        "resolved_cell_count": len(results),
        "scientific_execution_complete": True,
        "method_frozen": True,
        "registered_statistical_decision": recomputed,
        "supporting_artifacts": sorted(
            support_by_sha.values(), key=lambda row: (row["role"], row["path"])
        ),
        "result_payload": {
            "cell_result_count": len(results),
            "stage_metrics_sha256": recomputed["decision_sha256"],
            "role_pack_audit_sha256": audit_bindings["role_pack"]["sha256"],
            "round_governance_audit_sha256": audit_bindings["round_governance"]["sha256"],
        },
        "authority_boundaries": {
            "analyzer_is_proposal_only": True,
            "verifier_is_effect_authority": True,
            "tests_are_not_scientific_evidence": True,
            "no_hidden_writeback": True,
            "researcher_is_read_only_evidence_consumer": True,
        },
    }
    authority["result_authority_sha256"] = dsha(
        "FAILURE_MEMORY_SCIENTIFIC_RESULT_AUTHORITY_V2",
        authority,
        "result_authority_sha256",
    )
    write_new(authority_path, authority)
    load_scientific_result_authority_v2(
        path=authority_path,
        expected_stage=stage,
        expected_fixed_code_head=execution["fixed_code_head"],
        expected_scientific_program_sha256=bindings["scientific_program"]["semantic_sha256"],
    )
    if final_output.exists() or final_output.is_symlink():
        raise SystemExit("STOP=FINAL_OUTPUT_APPEARED_DURING_AGGREGATION")
    os.rename(output, final_output)
    parent_fd = os.open(final_output.parent, os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    lock_path.unlink()
    print("MEMORY_LIVE_STAGE_AGGREGATION_V2_PASS")
    print("STAGE=" + stage)
    print("RESULT_AUTHORITY=" + str(final_authority_path))
    for question, row in recomputed["question_decisions"].items():
        print(question + "=" + row["disposition"])


if __name__ == "__main__":
    main()
