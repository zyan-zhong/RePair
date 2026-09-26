from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
import os
import shutil

from .closeout import build_closeout, build_stage1_handoff
from .common import (
    Stage0Error,
    atomic_publish_zip,
    canonical_json_bytes,
    fsync_directory,
    load_json_object,
    sha256_bytes,
    sha256_file,
    stable_file_index,
    write_json_new,
)
from .constants import (
    AUTHORIZATION_ROOT,
    FINAL_REVIEW_ZIP,
    GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT,
    GENERIC_WORKTREE,
    PAIRED_CELL_COUNT,
    PREFLIGHT_ROOT,
    REVIEW_ROOT,
    SELECT_TASK_COUNT,
    STAGE0_ROOT,
    TWIN_REVIEW,
)
from .live_runner import _load_attempt_auditor
from .receipts import load_receipts


def audit_receipt_attempts(
    *,
    label: str,
    receipts: tuple[dict[str, Any], ...],
    evaluator_root: Path,
) -> dict[str, Any]:
    auditor = _load_attempt_auditor(GENERIC_WORKTREE)
    audited = []
    for receipt in receipts:
        attempt_dir = (
            evaluator_root
            / "attempts"
            / receipt["execution_attempt_id"]
        )
        loaded = auditor.load_attempt_directory_v1(attempt_dir)
        checks = {
            "attempt_bundle_sha256":
                loaded.attempt_bundle.attempt_bundle_sha256
                == receipt["attempt_bundle_sha256"],
            "task_id":
                loaded.episode_artifact.task_id
                == receipt["task_id"],
            "success":
                loaded.episode_artifact.success
                == receipt["success"],
            "termination_reason":
                loaded.episode_artifact.termination_reason
                == receipt["termination_reason"],
        }
        failed = sorted(
            key
            for key, passed in checks.items()
            if not passed
        )
        if failed:
            raise Stage0Error(
                "STAGE0_ATTEMPT_RECEIPT_MISMATCH:"
                + label
                + ":"
                + receipt["execution_attempt_id"]
                + ":"
                + ",".join(failed)
            )
        audited.append({
            "execution_attempt_id": receipt["execution_attempt_id"],
            "attempt_bundle_sha256": receipt["attempt_bundle_sha256"],
            "episode_semantic_sha256":
                loaded.episode_artifact.episode_semantic_sha256,
        })
    return {
        "condition_label": label,
        "audited_attempt_count": len(audited),
        "audited_attempts": audited,
    }


def aggregate_paired_results(
    *,
    parent_receipts: tuple[dict[str, Any], ...],
    candidate_receipts: tuple[dict[str, Any], ...],
    expected_task_count: int,
    expected_seeds: tuple[int, ...],
) -> dict[str, Any]:
    def index(rows: tuple[dict[str, Any], ...]) -> dict[tuple[int, str, int], dict]:
        result: dict[tuple[int, str, int], dict] = {}
        for row in rows:
            key = (row["manifest_index"], row["task_id"], row["seed"])
            if key in result:
                raise Stage0Error("PAIRED_RESULT_DUPLICATE_CELL")
            result[key] = row
        return result

    parent = index(parent_receipts)
    candidate = index(candidate_receipts)
    if set(parent) != set(candidate):
        raise Stage0Error("PAIRED_RESULT_GRID_MISMATCH")
    expected_cells = expected_task_count * len(expected_seeds)
    if len(parent) != expected_cells:
        raise Stage0Error(
            f"PAIRED_RESULT_CELL_COUNT_CHANGED:{len(parent)}:{expected_cells}"
        )

    tasks: dict[tuple[int, str], dict[str, list[bool]]] = defaultdict(
        lambda: {"parent": [], "candidate": []}
    )
    both_success = 0
    both_failure = 0
    parent_only = 0
    candidate_only = 0
    for key in sorted(parent):
        manifest_index, task_id, seed = key
        if seed not in expected_seeds:
            raise Stage0Error("PAIRED_RESULT_UNKNOWN_SEED")
        parent_success = bool(parent[key]["success"])
        candidate_success = bool(candidate[key]["success"])
        tasks[(manifest_index, task_id)]["parent"].append(parent_success)
        tasks[(manifest_index, task_id)]["candidate"].append(candidate_success)
        if parent_success and candidate_success:
            both_success += 1
        elif not parent_success and not candidate_success:
            both_failure += 1
        elif parent_success:
            parent_only += 1
        else:
            candidate_only += 1

    if len(tasks) != expected_task_count:
        raise Stage0Error("PAIRED_RESULT_TASK_COUNT_CHANGED")

    task_rows = []
    deltas = []
    for (manifest_index, task_id), values in sorted(tasks.items()):
        if len(values["parent"]) != len(expected_seeds):
            raise Stage0Error("PAIRED_RESULT_TASK_REPLICATE_COUNT_CHANGED")
        parent_rate = sum(values["parent"]) / len(expected_seeds)
        candidate_rate = sum(values["candidate"]) / len(expected_seeds)
        delta = candidate_rate - parent_rate
        deltas.append(delta)
        task_rows.append({
            "manifest_index": manifest_index,
            "task_id": task_id,
            "replicate_count": len(expected_seeds),
            "parent_success_rate": parent_rate,
            "candidate_success_rate": candidate_rate,
            "success_rate_delta": delta,
        })

    return {
        "schema_id": "HUMAN_PILOT_STAGE0_PAIRED_RESULTS_V1",
        "schema_version": 1,
        "round_role": "PILOT_ENGINEERING_ROUND_V1",
        "paper_efficacy_evidence": False,
        "primary_statistical_unit": "unique_task",
        "replicates_are_not_independent_tasks": True,
        "unique_task_count": len(tasks),
        "replicate_seeds": list(expected_seeds),
        "paired_cell_count": len(parent),
        "total_condition_cell_count": len(parent) + len(candidate),
        "parent_success_cells": sum(bool(row["success"]) for row in parent.values()),
        "candidate_success_cells": sum(bool(row["success"]) for row in candidate.values()),
        "both_success_cells": both_success,
        "both_failure_cells": both_failure,
        "parent_only_success_cells": parent_only,
        "candidate_only_success_cells": candidate_only,
        "mean_task_success_rate_delta": sum(deltas) / len(deltas),
        "task_results": task_rows,
        "promotion_eligible": False,
        "scientific_interpretation": (
            "INTERNAL_ENGINEERING_DIAGNOSTIC_ONLY_NOT_PAPER_EFFICACY"
        ),
    }


def _publish_recovered_review_root(
    *,
    results: dict[str, Any],
) -> dict[str, Any]:
    required = (
        "HUMAN_PILOT_STAGE0_PAIRED_RESULTS_V1.json",
        "HUMAN_PILOT_STAGE0_ARTIFACT_INDEX_V1.json",
        "PILOT_ENGINEERING_ROUND_CLOSEOUT_V1.json",
        "STAGE1_AUTOMATION_HANDOFF_V1.json",
        "REVIEW_MANIFEST_V1.json",
        "evidence/parent_cell_receipts.jsonl",
        "evidence/candidate_cell_receipts.jsonl",
        "evidence/PARENT_ATTEMPT_RELOAD_AUDIT_V1.json",
        "evidence/CANDIDATE_ATTEMPT_RELOAD_AUDIT_V1.json",
        "authorities/OFFLINE_PREFLIGHT_RECEIPT_V1.json",
        "authorities/STAGE0_EXECUTION_AUTHORIZATION_V1.json",
        "authorities/GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT_V1.json",
        "authorities/HUMAN_T2_TWIN_OFFOFF_BINDING_REVIEW_V1_1.zip",
    )
    missing = [
        relative
        for relative in required
        if not (REVIEW_ROOT / relative).is_file()
    ]
    if missing:
        raise Stage0Error(
            "STAGE0_EXISTING_REVIEW_ROOT_INCOMPLETE:"
            + ",".join(missing)
        )
    result_path = (
        REVIEW_ROOT
        / "HUMAN_PILOT_STAGE0_PAIRED_RESULTS_V1.json"
    )
    if result_path.read_bytes() != canonical_json_bytes(results):
        raise Stage0Error(
            "STAGE0_EXISTING_REVIEW_RESULTS_CHANGED"
        )
    closeout = load_json_object(
        REVIEW_ROOT
        / "PILOT_ENGINEERING_ROUND_CLOSEOUT_V1.json"
    )
    publication = atomic_publish_zip(
        source_root=REVIEW_ROOT,
        destination=FINAL_REVIEW_ZIP,
    )
    return {
        "results": results,
        "closeout": closeout,
        "publication": publication,
        "review_root_reused": True,
    }


def finalize_stage0(*, package_inventory_sha256: str) -> dict[str, Any]:
    parent_ledger = (
        STAGE0_ROOT
        / "execution/parent/cell_receipts.jsonl"
    )
    candidate_ledger = (
        STAGE0_ROOT
        / "execution/candidate/cell_receipts.jsonl"
    )
    parent = load_receipts(parent_ledger)
    candidate = load_receipts(candidate_ledger)
    parent_attempt_audit = audit_receipt_attempts(
        label="parent",
        receipts=parent,
        evaluator_root=(
            STAGE0_ROOT
            / "execution/parent/evaluator_run"
        ),
    )
    candidate_attempt_audit = audit_receipt_attempts(
        label="candidate",
        receipts=candidate,
        evaluator_root=(
            STAGE0_ROOT
            / "execution/candidate/evaluator_run"
        ),
    )
    results = aggregate_paired_results(
        parent_receipts=parent,
        candidate_receipts=candidate,
        expected_task_count=SELECT_TASK_COUNT,
        expected_seeds=(17, 31, 47, 73, 101),
    )
    if results["paired_cell_count"] != PAIRED_CELL_COUNT:
        raise Stage0Error(
            "STAGE0_FINAL_PAIRED_CELL_COUNT_CHANGED"
        )

    if FINAL_REVIEW_ZIP.exists():
        raise Stage0Error(
            f"STAGE0_FINAL_REVIEW_ALREADY_EXISTS:{FINAL_REVIEW_ZIP}"
        )
    if REVIEW_ROOT.exists():
        return _publish_recovered_review_root(
            results=results
        )

    staging_root = (
        REVIEW_ROOT.parent
        / "review_v1.staging"
    )
    interrupted_root = (
        REVIEW_ROOT.parent
        / "review_v1.staging.interrupted"
    )
    if staging_root.exists():
        if interrupted_root.exists():
            raise Stage0Error(
                "STAGE0_REVIEW_STAGING_AND_INTERRUPTED_BOTH_EXIST"
            )
        os.replace(
            staging_root,
            interrupted_root,
        )
        fsync_directory(REVIEW_ROOT.parent)

    staging_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    results_path = (
        staging_root
        / "HUMAN_PILOT_STAGE0_PAIRED_RESULTS_V1.json"
    )
    write_json_new(
        results_path,
        results,
    )
    result_sha = sha256_file(results_path)

    authority_root = staging_root / "authorities"
    authority_root.mkdir()
    for source in (
        PREFLIGHT_ROOT / "OFFLINE_PREFLIGHT_RECEIPT_V1.json",
        AUTHORIZATION_ROOT
        / "STAGE0_EXECUTION_AUTHORIZATION_V1.json",
        GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT,
        TWIN_REVIEW,
    ):
        if not source.is_file():
            raise Stage0Error(
                f"STAGE0_AUTHORITY_MISSING:{source}"
            )
        shutil.copy2(
            source,
            authority_root / source.name,
        )

    evidence_root = staging_root / "evidence"
    evidence_root.mkdir()
    shutil.copy2(
        parent_ledger,
        evidence_root / "parent_cell_receipts.jsonl",
    )
    shutil.copy2(
        candidate_ledger,
        evidence_root / "candidate_cell_receipts.jsonl",
    )
    write_json_new(
        evidence_root
        / "PARENT_ATTEMPT_RELOAD_AUDIT_V1.json",
        parent_attempt_audit,
    )
    write_json_new(
        evidence_root
        / "CANDIDATE_ATTEMPT_RELOAD_AUDIT_V1.json",
        candidate_attempt_audit,
    )

    provisional_index = {
        "schema_id":
            "HUMAN_PILOT_STAGE0_ARTIFACT_INDEX_V1",
        "schema_version": 1,
        "stage0_root": str(STAGE0_ROOT),
        "parent_attempt_root": str(
            STAGE0_ROOT
            / "execution/parent/evaluator_run"
        ),
        "candidate_attempt_root": str(
            STAGE0_ROOT
            / "execution/candidate/evaluator_run"
        ),
        "parent_receipt_count": len(parent),
        "candidate_receipt_count": len(candidate),
        "parent_attempt_bundle_sha256s": [
            row["attempt_bundle_sha256"]
            for row in parent
        ],
        "candidate_attempt_bundle_sha256s": [
            row["attempt_bundle_sha256"]
            for row in candidate
        ],
        "parent_attempt_reload_audit_sha256":
            sha256_file(
                evidence_root
                / "PARENT_ATTEMPT_RELOAD_AUDIT_V1.json"
            ),
        "candidate_attempt_reload_audit_sha256":
            sha256_file(
                evidence_root
                / "CANDIDATE_ATTEMPT_RELOAD_AUDIT_V1.json"
            ),
    }
    artifact_index_path = (
        staging_root
        / "HUMAN_PILOT_STAGE0_ARTIFACT_INDEX_V1.json"
    )
    write_json_new(
        artifact_index_path,
        provisional_index,
    )
    artifact_index_sha = sha256_file(
        artifact_index_path
    )

    closeout = build_closeout(
        result_sha256=result_sha,
        artifact_index_sha256=artifact_index_sha,
        package_inventory_sha256=package_inventory_sha256,
    )
    closeout_path = (
        staging_root
        / "PILOT_ENGINEERING_ROUND_CLOSEOUT_V1.json"
    )
    write_json_new(
        closeout_path,
        closeout,
    )
    handoff = build_stage1_handoff(
        closeout_sha256=sha256_file(
            closeout_path
        )
    )
    write_json_new(
        staging_root
        / "STAGE1_AUTOMATION_HANDOFF_V1.json",
        handoff,
    )

    manifest = {
        "schema_id":
            "HUMAN_PILOT_STAGE0_CLOSEOUT_REVIEW_MANIFEST_V1",
        "schema_version": 1,
        "review_status":
            "STAGE0_ENGINEERING_PILOT_CLOSED",
        "round_role":
            "PILOT_ENGINEERING_ROUND_V1",
        "paper_efficacy_evidence": False,
        "promotion_eligible": False,
        "result_sha256": result_sha,
        "artifact_index_sha256":
            artifact_index_sha,
        "files": stable_file_index(
            staging_root
        ),
        "next_gate": (
            "GENERIC_ROUND_ORCHESTRATOR_"
            "AND_ROLE_HANDOFF_AUTOMATION"
        ),
    }
    write_json_new(
        staging_root / "REVIEW_MANIFEST_V1.json",
        manifest,
    )

    os.replace(
        staging_root,
        REVIEW_ROOT,
    )
    fsync_directory(
        REVIEW_ROOT.parent
    )

    publication = atomic_publish_zip(
        source_root=REVIEW_ROOT,
        destination=FINAL_REVIEW_ZIP,
    )
    return {
        "results": results,
        "closeout": closeout,
        "publication": publication,
        "review_root_reused": False,
    }
