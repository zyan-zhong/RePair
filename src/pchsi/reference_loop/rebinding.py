"""Immutable Analyzer-era sidecar binding for sealed attempt bundles."""
from __future__ import annotations

from pathlib import Path

from .canonical import domain_hash, sha256_file, write_new_json
from .identity import load_pi1_reference_identity
from .task_access import (
    find_access_row,
    load_task_access_revalidation,
)
from .types import ValidatedAttemptBundle


def build_trajectory_rebinding_manifest(
    *,
    bundle: ValidatedAttemptBundle,
    pi1_identity: dict[str, object],
    task_access: dict[str, object],
    analyzer_run_id: str | None = None,
    analyzer_condition: str | None = None,
    analyzer_evidence_pack_id: str | None = None,
    analyzer_evidence_sha256: str | None = None,
    memory_pack_id: str | None = None,
    memory_snapshot_id: str | None = None,
    memory_pack_sha256: str | None = None,
    research_decision_id: str | None = None,
    candidate_repair_ids: tuple[str, ...] = (),
    paired_state_id: str | None = None,
    f0f1_arm: str | None = None,
    pair_seed: int | None = None,
    repair_registration_sha256: str | None = None,
    training_sample_ids: tuple[str, ...] = (),
    result_manifest_ids: tuple[str, ...] = (),
) -> dict[str, object]:
    if pi1_identity["logical_policy_id"] != "P4-R1-Q2-BAD":
        raise ValueError("trajectory rebinding requires π1 logical policy")
    if bundle.logical_condition_id != pi1_identity["logical_policy_id"]:
        raise ValueError(
            "bundle must explicitly bind the same π1 logical policy identity"
        )
    if (
        bundle.checkpoint_instance_id
        != pi1_identity["checkpoint_instance_id"]
    ):
        raise ValueError(
            "bundle must explicitly bind the same π1 checkpoint identity"
        )
    if bundle.access_class not in {
        "DEV_VISIBLE",
        "TRAIN_MEMORY_SOURCE",
        "TRAIN_RETRIEVAL_DEV",
    }:
        raise ValueError(
            "bundle-local access identity does not permit detailed Analyzer release"
        )

    access_row = find_access_row(
        task_access,
        task_id=bundle.task_id,
        gamefile_sha256=bundle.gamefile_sha256,
    )
    if access_row["revalidation_disposition"] not in {
        "CONFIRMED_UNCHANGED",
        "DOWNGRADED_DUE_TO_HISTORICAL_EXPOSURE",
    }:
        raise ValueError(
            "task access is blocked: "
            + str(access_row["revalidation_disposition"])
        )
    if access_row["strong_model_allowed"] is not True:
        raise ValueError(
            "task access does not permit full Analyzer trajectory release"
        )
    if access_row["allowed_artifact_granularity"] != (
        "FULL_TRAJECTORY_DEV_VISIBLE"
    ):
        raise ValueError("task access granularity is not full trajectory")

    future_bundle = (
        analyzer_run_id,
        analyzer_condition,
        analyzer_evidence_pack_id,
        analyzer_evidence_sha256,
    )
    if any(value is not None for value in future_bundle) and not all(
        value is not None for value in future_bundle
    ):
        raise ValueError("Analyzer sidecar fields must be supplied together")

    memory_bundle = (
        memory_pack_id,
        memory_snapshot_id,
        memory_pack_sha256,
    )
    if any(value is not None for value in memory_bundle) and not all(
        value is not None for value in memory_bundle
    ):
        raise ValueError("Memory sidecar fields must be supplied together")

    pair_bundle = (
        paired_state_id,
        f0f1_arm,
        pair_seed,
        repair_registration_sha256,
    )
    if any(value is not None for value in pair_bundle) and not all(
        value is not None for value in pair_bundle
    ):
        raise ValueError("F0/F1 sidecar fields must be supplied together")

    source_bindings = [
        {
            "filename": name,
            "sha256": digest,
            "path": str(bundle.bundle_root / name),
        }
        for name, digest in bundle.source_file_sha256s
    ]
    manifest = {
        "schema_id": "TRAJECTORY_REBINDING_MANIFEST_V1",
        "schema_version": 1,
        "source_attempt_bundle_path": str(bundle.bundle_root),
        "source_attempt_bundle_sha256": (
            bundle.attempt_bundle_sha256
        ),
        "source_episode_semantic_sha256": (
            bundle.episode_semantic_sha256
        ),
        "source_file_bindings": source_bindings,
        "policy_identity_sha256": pi1_identity["identity_sha256"],
        "task_access_revalidation_sha256": task_access[
            "revalidation_sha256"
        ],
        "task_access_row_sha256": access_row["row_sha256"],
        "task_id": bundle.task_id,
        "gamefile_sha256": bundle.gamefile_sha256,
        "checkpoint_instance_id": pi1_identity[
            "checkpoint_instance_id"
        ],
        "analyzer_run_id": analyzer_run_id,
        "analyzer_condition": analyzer_condition,
        "analyzer_evidence_pack_id": analyzer_evidence_pack_id,
        "analyzer_evidence_sha256": analyzer_evidence_sha256,
        "memory_pack_id": memory_pack_id,
        "memory_snapshot_id": memory_snapshot_id,
        "memory_pack_sha256": memory_pack_sha256,
        "research_decision_id": research_decision_id,
        "candidate_repair_ids": list(candidate_repair_ids),
        "paired_state_id": paired_state_id,
        "f0f1_arm": f0f1_arm,
        "pair_seed": pair_seed,
        "repair_registration_sha256": repair_registration_sha256,
        "training_sample_ids": list(training_sample_ids),
        "result_manifest_ids": list(result_manifest_ids),
        "alignment_census": bundle.alignment_census,
        "revalidation_status": "VALIDATED_FOR_ANALYZER_EVIDENCE",
        "manifest_sha256": "0" * 64,
    }
    manifest["manifest_sha256"] = domain_hash(
        "TRAJECTORY_REBINDING_MANIFEST_V1",
        manifest,
        excluded_field="manifest_sha256",
    )
    return manifest


def rebind_trajectory_file(
    *,
    bundle: ValidatedAttemptBundle,
    pi1_identity_path: Path,
    task_access_revalidation_path: Path,
    output_path: Path,
) -> dict[str, object]:
    identity = load_pi1_reference_identity(pi1_identity_path)
    access = load_task_access_revalidation(
        task_access_revalidation_path
    )
    manifest = build_trajectory_rebinding_manifest(
        bundle=bundle,
        pi1_identity=identity,
        task_access=access,
    )
    write_new_json(output_path, manifest)
    return manifest
