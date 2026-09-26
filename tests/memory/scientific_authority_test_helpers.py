from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.memory.scientific_decision import (
    FM0, FM1, FM2, FM3, ROUND_ACTIVE,
    STAGE_1B, STAGE_2, STAGE_3,
    recompute_stage_decisions_v1,
)


def dsha(domain: str, value: dict, field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return hashlib.sha256(domain.encode() + b"\0" + canonical_json_bytes(payload)).hexdigest()


def write_json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def write_bytes(path: Path, raw: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def binding(path: Path, root: Path, role: str) -> dict:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "role": role,
    }


def rule(stage: str, primary_split: str | None = None) -> dict:
    value = {
        "schema_id": "FAILURE_MEMORY_REGISTERED_DECISION_RULE_V1",
        "schema_version": 1,
        "rule_sha256": "0" * 64,
        "stage": stage,
        "primary_endpoint": "TASK_SUCCESS",
        "primary_split": primary_split,
        "minimum_complete_pairs": 1,
        "minimum_absolute_success_gain": 1,
        "minimum_coverage_count": 1,
        "minimum_correct_exposure_count": 1,
        "maximum_harm_count": 0,
        "maximum_wrong_memory_count": 0,
        "maximum_unsafe_memory_count": 0,
        "minimum_round_count": 2 if stage == STAGE_2 else 0,
        "confidence_interval_method": "EXACT_TASK_PAIRED_COUNTS_V1",
        "multiple_comparisons_policy": "REGISTERED_PRIMARY_COMPARISONS_ONLY_V1",
    }
    value["rule_sha256"] = dsha(
        "FAILURE_MEMORY_REGISTERED_DECISION_RULE_V1", value, "rule_sha256"
    )
    return value


def cell_identity_rows(stage: str) -> list[dict]:
    if stage in {STAGE_1B, STAGE_3}:
        split = "VALID_UNSEEN" if stage == STAGE_3 else "TRAIN_RETRIEVAL_DEV"
        return [
            {
                "cell_id": f"g1-{condition}",
                "comparison_group_id": "g1",
                "condition": condition,
                "round_index": None,
                "split": split,
                "task_id": "task-g1",
                "task_family": "pick_and_place_simple",
                "snapshot_sha256": "d" * 64,
            }
            for condition in (FM0, FM1, FM2, FM3)
        ]
    return [
        {
            "cell_id": "r0-g1", "comparison_group_id": "g1",
            "condition": ROUND_ACTIVE, "round_index": 0,
            "split": "TRAIN_MEMORY_SOURCE", "task_id": "task-g1",
            "task_family": "pick_and_place_simple", "snapshot_sha256": "d" * 64,
        },
        {
            "cell_id": "r1-g1", "comparison_group_id": "g1",
            "condition": ROUND_ACTIVE, "round_index": 1,
            "split": "TRAIN_MEMORY_SOURCE", "task_id": "task-g1",
            "task_family": "pick_and_place_simple", "snapshot_sha256": "e" * 64,
        },
    ]


def make_cell_result(
    identity: dict,
    *,
    stage: str,
    manifest_sha: str,
    role_pack_sha256s: dict[str, str] | None = None,
) -> dict:
    condition = identity["condition"]
    if stage == STAGE_2:
        success = identity["round_index"] == 1
    else:
        success = condition != FM0
    exposed = condition != FM0
    value = {
        "schema_id": "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",
        "schema_version": 1,
        "cell_result_sha256": "0" * 64,
        **identity,
        "execution_manifest_sha256": manifest_sha,
        "stage": stage,
        "success": success,
        "memory_exposed": exposed,
        "correct_memory_exposure": exposed,
        "wrong_memory_exposure": False,
        "unsafe_memory_exposure": False,
        "harm_observed": False,
        "abstained": not exposed,
        "old_failure_disposition": "AVOIDED" if success else "REPEATED",
        "model_calls": 1,
        "environment_steps": 1,
        "memory_tokens": 10 if exposed else 0,
        "prompt_tokens": 100,
        "latency_ms": 5,
        "evaluation_writeback_attempted": False,
        "same_round_memory_readback": False,
        "role_pack_sha256s": (
            {
                "policy": "a" * 64,
                "analyzer": "b" * 64,
                "researcher": "c" * 64,
            }
            if role_pack_sha256s is None
            else dict(role_pack_sha256s)
        ),
    }
    value["cell_result_sha256"] = dsha(
        "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1", value, "cell_result_sha256"
    )
    return value


def build_authority(
    root: Path,
    *,
    stage: str = STAGE_1B,
    snapshot_binding_sha: str | None = None,
    stage2_registry_snapshots: list[str] | None = None,
) -> tuple[Path, dict]:
    root.mkdir(parents=True, exist_ok=True)
    fixed_head = "f" * 40
    identities_dir = root / "identities"
    identity_files: dict[str, Path] = {}
    for name in (
        "scientific_protocol", "scientific_program", "runtime_identity",
        "policy_identity", "environment_identity", "panel", "schedule",
        "cell_executor",
    ):
        path = identities_dir / name
        write_bytes(path, (name + "\n").encode())
        identity_files[name] = path
    program_sha = hashlib.sha256(identity_files["scientific_program"].read_bytes()).hexdigest()

    decision_value = rule(stage, "VALID_UNSEEN" if stage == STAGE_3 else None)
    decision_path = identities_dir / "decision_rule.json"
    write_json(decision_path, decision_value)
    identity_files["decision_rule"] = decision_path

    identities = cell_identity_rows(stage)
    cell_manifest_path = identities_dir / "cells.jsonl"
    cell_manifest_path.write_bytes(
        b"".join(canonical_json_bytes(row) for row in identities)
    )
    identity_files["cell_manifest"] = cell_manifest_path
    if stage == STAGE_2:
        snapshot_registry = identities_dir / "snapshot_registry.json"
        registry_snapshots = (
            ["d" * 64, "e" * 64]
            if stage2_registry_snapshots is None
            else list(stage2_registry_snapshots)
        )
        write_json(snapshot_registry, {"rounds": [0, 1], "snapshots": registry_snapshots})
        identity_files["snapshot_registry"] = snapshot_registry
    else:
        snapshot_path = identities_dir / "snapshot.json"
        write_json(snapshot_path, {"snapshot_sha256": "d" * 64})
        identity_files["snapshot"] = snapshot_path

    semantic_fields = {
        "scientific_program": program_sha,
        "decision_rule": decision_value["rule_sha256"],
    }
    if stage != STAGE_2:
        semantic_fields["snapshot"] = (
            "d" * 64 if snapshot_binding_sha is None else snapshot_binding_sha
        )
    manifest_bindings = {
        name: {
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "semantic_sha256": semantic_fields.get(
                name, hashlib.sha256(path.read_bytes()).hexdigest()
            ),
            "size_bytes": path.stat().st_size,
            "role": name,
        }
        for name, path in identity_files.items()
    }
    manifest = {
        "schema_id": "FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2",
        "schema_version": 2,
        "manifest_sha256": "0" * 64,
        "stage": stage,
        "fixed_code_head": fixed_head,
        "scientific_execution_authorized": False,
        "preoutcome_frozen": True,
        "registered_cell_count": len(identities),
        "cell_result_schema_id": "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",
        "bindings": manifest_bindings,
        "operational_paths": {
            "cell_executor": "/approved/executor",
            "cell_manifest": "/approved/cells.jsonl",
        },
    }
    manifest["manifest_sha256"] = dsha(
        "FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2", manifest, "manifest_sha256"
    )
    manifest_path = root / "bound" / "execution_manifest.json"
    write_json(manifest_path, manifest)

    supporting = [
        binding(path, root, f"EXECUTION_BINDING:{name}")
        for name, path in identity_files.items()
        if name != "decision_rule"
    ]
    supporting.append(binding(manifest_path, root, "EXECUTION_MANIFEST"))
    supporting.append(binding(decision_path, root, "DECISION_RULE"))

    results = []
    census_rows = []
    for identity in identities:
        cell_dir = root / "cells" / identity["cell_id"]
        role_pack_sha256s: dict[str, str] = {}
        for role in ("policy", "analyzer", "researcher"):
            pack_path = cell_dir / f"{role.upper()}_MEMORY_PACK_V1.json"
            pack_raw = canonical_json_bytes({
                "cell_id": identity["cell_id"],
                "role": role,
                "test_payload": True,
            })
            pack_sha = write_bytes(pack_path, pack_raw)
            role_pack_sha256s[role] = pack_sha
            supporting.append(
                binding(
                    pack_path,
                    root,
                    f"ROLE_PACK:{role}:{identity['cell_id']}",
                )
            )
        result = make_cell_result(
            identity,
            stage=stage,
            manifest_sha=manifest["manifest_sha256"],
            role_pack_sha256s=role_pack_sha256s,
        )
        results.append(result)
        result_path = cell_dir / "CELL_SCIENTIFIC_RESULT_V1.json"
        result_file_sha = write_json(result_path, result)
        receipt = {
            "schema_id": "FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1",
            "schema_version": 1,
            "receipt_sha256": "0" * 64,
            "cell_id": identity["cell_id"],
            "execution_manifest_sha256": manifest["manifest_sha256"],
            "cell_result_sha256": result["cell_result_sha256"],
            "cell_complete": True,
            "scientific_outcome_produced": True,
            "infrastructure_error": False,
        }
        receipt["receipt_sha256"] = dsha(
            "FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1", receipt, "receipt_sha256"
        )
        receipt_path = cell_dir / "CELL_TERMINAL_RECEIPT_V1.json"
        receipt_file_sha = write_json(receipt_path, receipt)
        supporting.append(binding(result_path, root, f"CELL_RESULT:{identity['cell_id']}"))
        supporting.append(binding(receipt_path, root, f"CELL_RECEIPT:{identity['cell_id']}"))
        census_rows.append({
            "cell_id": identity["cell_id"],
            "receipt_file_sha256": receipt_file_sha,
            "result_file_sha256": result_file_sha,
            "receipt_sha256": receipt["receipt_sha256"],
            "cell_result_sha256": result["cell_result_sha256"],
        })

    census = {
        "schema_id": "FAILURE_MEMORY_CELL_ARTIFACT_CENSUS_V1",
        "schema_version": 1,
        "execution_manifest_sha256": manifest["manifest_sha256"],
        "registered_cell_count": len(identities),
        "resolved_cell_count": len(identities),
        "cells": census_rows,
        "census_sha256": "0" * 64,
    }
    census["census_sha256"] = dsha(
        "FAILURE_MEMORY_CELL_ARTIFACT_CENSUS_V1", census, "census_sha256"
    )
    census_path = root / "audits" / "cell_census.json"
    write_json(census_path, census)
    supporting.append(binding(census_path, root, "CELL_CENSUS"))

    recomputed = recompute_stage_decisions_v1(
        stage=stage,
        cell_results=results,
        decision_rule=decision_value,
        execution_manifest_sha256=manifest["manifest_sha256"],
    )
    role_presence = {role: len(results) for role in ("policy", "analyzer", "researcher")}
    round_summary = {}
    if stage == STAGE_2:
        round_summary = {
            "0": ["d" * 64],
            "1": ["e" * 64],
        }
    audit_payloads = {
        "contamination": {
            "status": "PASS",
            "same_round_memory_readback_count": 0,
            "evaluation_writeback_attempt_count": 0,
            "unregistered_cell_count": 0,
        },
        "writeback": {"status": "PASS", "prohibited_writeback_count": 0},
        "independent_recomputation": {
            "status": "PASS",
            "decision_sha256": recomputed["decision_sha256"],
            "cell_result_count": len(results),
        },
        "role_pack": {"status": "PASS", "role_pack_presence_counts": role_presence},
        "round_governance": {"status": "PASS", "round_snapshot_sha256s": round_summary},
    }
    audit_bindings = {}
    for name, payload in audit_payloads.items():
        path = root / "audits" / f"{name}.json"
        write_json(path, payload)
        row = binding(path, root, f"AUDIT:{name}")
        supporting.append(row)
        audit_bindings[name] = row

    def by_role(role: str) -> dict:
        return next(row for row in supporting if row["role"] == role)

    schema = {
        STAGE_1B: "STAGE_1B_FROZEN_POLICY_FM0_FM3_RESULT_AUTHORITY_V2",
        STAGE_2: "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY_RESULT_AUTHORITY_V2",
        STAGE_3: "STAGE_3_FROZEN_ID_OOD_RESULT_AUTHORITY_V2",
    }[stage]
    authority = {
        "schema_id": schema,
        "schema_version": 2,
        "authority_scope": "TEST_REGISTERED_AUTHORITY",
        "scientific_stage": stage,
        "result_authority_sha256": "0" * 64,
        "execution_manifest_binding": by_role("EXECUTION_MANIFEST"),
        "decision_rule_binding": by_role("DECISION_RULE"),
        "cell_census_binding": by_role("CELL_CENSUS"),
        "audit_bindings": audit_bindings,
        "registered_cell_count": len(identities),
        "resolved_cell_count": len(identities),
        "scientific_execution_complete": True,
        "method_frozen": True,
        "registered_statistical_decision": recomputed,
        "supporting_artifacts": supporting,
        "result_payload": {"cell_result_count": len(results)},
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
    authority_path = root / "RESULT_AUTHORITY_V2.json"
    write_json(authority_path, authority)
    return authority_path, {"fixed_head": fixed_head, "program_sha": program_sha}
