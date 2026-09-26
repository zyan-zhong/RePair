"""Final rebinding for legacy bundles using explicit historical lineage sidecars."""
from __future__ import annotations

from pathlib import Path

from .canonical import domain_hash, write_new_json
from .types import ValidatedAttemptBundle


def _lineage_row(
    bridge: dict[str, object],
    *,
    attempt_bundle_sha256: str,
) -> dict[str, object]:
    rows = bridge.get("rows")
    if not isinstance(rows, list):
        raise TypeError("lineage bridge rows must be an array")
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("attempt_bundle_sha256") == attempt_bundle_sha256
    ]
    if len(matches) != 1:
        raise ValueError(
            "historical bundle must resolve to exactly one lineage row; "
            f"observed={len(matches)}"
        )
    return matches[0]


def _access_row_from_lineage_identity(
    task_access: dict[str, object],
    lineage: dict[str, object],
    *,
    gamefile_sha256: str,
) -> dict[str, object]:
    rows = task_access.get("rows")
    if not isinstance(rows, list):
        raise TypeError("task-access revalidation rows must be array")
    expected_row_sha = lineage.get("task_access_row_sha256")
    if not isinstance(expected_row_sha, str):
        raise ValueError("historical lineage lacks task-access row identity")

    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("row_sha256") == expected_row_sha
        and row.get("gamefile_sha256") == gamefile_sha256
    ]
    if len(matches) != 1:
        raise ValueError(
            "historical task access row must resolve uniquely by "
            "registered row SHA and gamefile SHA; "
            f"observed={len(matches)}"
        )
    return matches[0]


def build_historical_trajectory_rebinding_manifest(
    *,
    bundle: ValidatedAttemptBundle,
    pi1_identity: dict[str, object],
    task_access: dict[str, object],
    lineage_bridge: dict[str, object],
) -> dict[str, object]:
    if pi1_identity.get("schema_id") != "PI1_REFERENCE_IDENTITY_V1":
        raise ValueError("π1 identity schema mismatch")
    if pi1_identity.get("logical_policy_id") != "P4-R1-Q2-BAD":
        raise ValueError("historical rebinding requires P4-R1-Q2-BAD")
    lineage = _lineage_row(
        lineage_bridge,
        attempt_bundle_sha256=bundle.attempt_bundle_sha256,
    )
    if lineage.get("episode_semantic_sha256") != bundle.episode_semantic_sha256:
        raise ValueError("lineage semantic SHA differs from validated bundle")
    if lineage.get("task_id") != bundle.task_id:
        raise ValueError("lineage task_id differs from validated bundle")
    if lineage.get("gamefile_sha256") != bundle.gamefile_sha256:
        raise ValueError("lineage gamefile SHA differs from validated bundle")
    if lineage.get("logical_policy_id") != pi1_identity["logical_policy_id"]:
        raise ValueError("lineage logical policy differs from π1 identity")
    if (
        lineage.get("checkpoint_instance_id")
        != pi1_identity["checkpoint_instance_id"]
    ):
        raise ValueError("lineage checkpoint differs from π1 identity")

    access_row = _access_row_from_lineage_identity(
        task_access,
        lineage,
        gamefile_sha256=bundle.gamefile_sha256,
    )
    if access_row.get("strong_model_allowed") is not True:
        raise ValueError("task access does not allow Analyzer trajectory release")
    if access_row.get("allowed_artifact_granularity") != (
        "FULL_TRAJECTORY_DEV_VISIBLE"
    ):
        raise ValueError("task access is not full-trajectory dev-visible")

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
        "rebinding_mode": "HISTORICAL_LINEAGE_SIDECAR_V1",
        "source_attempt_bundle_path": str(bundle.bundle_root),
        "source_attempt_bundle_sha256": bundle.attempt_bundle_sha256,
        "source_episode_semantic_sha256": bundle.episode_semantic_sha256,
        "source_file_bindings": source_bindings,
        "historical_lineage_bridge_sha256": lineage_bridge["bridge_sha256"],
        "historical_lineage_row_sha256": lineage["row_sha256"],
        "policy_identity_sha256": pi1_identity["identity_sha256"],
        "task_access_revalidation_sha256": task_access[
            "revalidation_sha256"
        ],
        "task_access_row_sha256": access_row["row_sha256"],
        "task_id": bundle.task_id,
        "gamefile_sha256": bundle.gamefile_sha256,
        "checkpoint_instance_id": pi1_identity["checkpoint_instance_id"],
        "analyzer_run_id": None,
        "analyzer_condition": None,
        "analyzer_evidence_pack_id": None,
        "analyzer_evidence_sha256": None,
        "memory_pack_id": None,
        "memory_snapshot_id": None,
        "memory_pack_sha256": None,
        "research_decision_id": None,
        "candidate_repair_ids": [],
        "paired_state_id": None,
        "f0f1_arm": None,
        "pair_seed": None,
        "repair_registration_sha256": None,
        "training_sample_ids": [],
        "result_manifest_ids": [],
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


def write_historical_trajectory_rebinding_manifest(
    *,
    bundle: ValidatedAttemptBundle,
    pi1_identity: dict[str, object],
    task_access: dict[str, object],
    lineage_bridge: dict[str, object],
    output_path: Path,
) -> dict[str, object]:
    value = build_historical_trajectory_rebinding_manifest(
        bundle=bundle,
        pi1_identity=pi1_identity,
        task_access=task_access,
        lineage_bridge=lineage_bridge,
    )
    write_new_json(output_path, value)
    return value
