"""Bounded read-only discovery of candidate evidence and identity inputs."""
from __future__ import annotations

from pathlib import Path

from .canonical import (
    canonical_json_bytes,
    sha256_file,
    strict_json_loads,
    write_new_json,
)


_REQUIRED = {
    "attempt.json",
    "action_traces.jsonl",
    "policy_calls.jsonl",
    "public_transitions.jsonl",
    "SHA256SUMS",
}


def _episode_metadata(path: Path) -> dict[str, object] | None:
    try:
        value = strict_json_loads(path.read_bytes())
    except Exception:
        return None
    if not isinstance(value, dict):
        return None
    return {
        "task_id": value.get("task_id"),
        "gamefile_sha256": value.get("gamefile_sha256"),
        "logical_condition_id": value.get("logical_condition_id"),
        "checkpoint_instance_id": value.get(
            "checkpoint_instance_id"
        ),
        "training_seed": value.get("training_seed"),
        "access_class": value.get("access_class"),
        "evaluation_context": value.get("evaluation_context"),
        "policy_runtime_manifest_sha256": value.get(
            "select_policy_runtime_manifest_sha256"
        )
        or value.get("policy_runtime_manifest_sha256"),
    }


def discover_reference_loop_inputs(
    *,
    roots: tuple[Path, ...],
    max_json_bytes: int = 8 * 1024 * 1024,
) -> dict[str, object]:
    bundle_rows: list[dict[str, object]] = []
    runtime_candidates: dict[str, list[dict[str, object]]] = {}
    visited: set[Path] = set()

    for root in roots:
        if not root.exists():
            continue
        for attempt in root.rglob("attempt.json"):
            try:
                parent = attempt.parent.resolve()
            except OSError:
                continue
            if parent in visited:
                continue
            visited.add(parent)
            names = {
                item.name
                for item in parent.iterdir()
                if item.is_file()
            }
            if names != _REQUIRED:
                continue
            metadata = _episode_metadata(attempt)
            if metadata is None:
                continue
            bundle_rows.append(
                {
                    "bundle_path": str(parent),
                    "attempt_json_sha256": sha256_file(attempt),
                    **metadata,
                    "formal_analyzer_bundle_shape": True,
                    "pi1_logical_policy": (
                        metadata.get("logical_condition_id")
                        == "P4-R1-Q2-BAD"
                    ),
                    "detailed_analyzer_access_candidate": (
                        metadata.get("access_class")
                        in {
                            "DEV_VISIBLE",
                            "TRAIN_MEMORY_SOURCE",
                            "TRAIN_RETRIEVAL_DEV",
                        }
                    ),
                }
            )

        for candidate in root.rglob("*.json"):
            try:
                if (
                    candidate.stat().st_size > max_json_bytes
                    or candidate.is_symlink()
                ):
                    continue
            except OSError:
                continue
            name = candidate.name.lower()
            if "runtime" not in name or "manifest" not in name:
                continue
            digest = sha256_file(candidate)
            runtime_candidates.setdefault(digest, []).append(
                {
                    "path": str(candidate.resolve()),
                    "sha256": digest,
                    "size_bytes": candidate.stat().st_size,
                }
            )

    bundle_rows.sort(
        key=lambda item: (
            str(item.get("logical_condition_id")),
            str(item.get("checkpoint_instance_id")),
            str(item.get("bundle_path")),
        )
    )
    pi1_dev = [
        row
        for row in bundle_rows
        if row["pi1_logical_policy"]
        and row["detailed_analyzer_access_candidate"]
    ]
    checkpoints = sorted(
        {
            str(row["checkpoint_instance_id"])
            for row in pi1_dev
            if row.get("checkpoint_instance_id")
        }
    )
    status = (
        "READY_FOR_EXPLICIT_REGISTRATION"
        if pi1_dev and len(checkpoints) >= 1
        else "BLOCKED_NO_PI1_DEV_COMPLETE_TRAJECTORY"
    )
    return {
        "schema_id": "REFERENCE_LOOP_INPUT_DISCOVERY_V1",
        "schema_version": 1,
        "roots": [str(root.resolve()) for root in roots if root.exists()],
        "complete_bundle_count": len(bundle_rows),
        "pi1_dev_complete_bundle_count": len(pi1_dev),
        "pi1_dev_checkpoint_candidates": checkpoints,
        "runtime_manifest_candidates_by_sha256": runtime_candidates,
        "bundles": bundle_rows,
        "discovery_status": status,
        "selection_performed": False,
        "scientific_execution_performed": False,
        "model_call_performed": False,
        "environment_execution_performed": False,
    }


def discover_reference_loop_inputs_file(
    *,
    roots: tuple[Path, ...],
    output_path: Path,
) -> dict[str, object]:
    artifact = discover_reference_loop_inputs(roots=roots)
    write_new_json(output_path, artifact)
    return artifact
