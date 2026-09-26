"""Read-only census of historical π1 identity authorities for explicit registration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import (
    domain_hash,
    ensure_directory_no_symlink,
    ensure_regular_no_symlink,
    sha256_file,
    strict_json_loads,
    write_new_json,
)


TRAIN17 = "P4-R1-Q2-BAD-TRAIN17"
RUNTIME_SHA = (
    "215bbe3981668181c8b2eb51c4568af944512f7c20c4504ad75faa012cc83faa"
)


def _collect_relevant(value: object, *, prefix: str = "$") -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}"
            key_lower = str(key).lower()
            if isinstance(child, (str, int, float, bool)) or child is None:
                if any(
                    token in key_lower
                    for token in (
                        "model",
                        "adapter",
                        "tokenizer",
                        "chat",
                        "runtime",
                        "manifest",
                        "config",
                        "protocol",
                        "seed",
                        "sha",
                        "path",
                    )
                ):
                    rows.append(
                        {
                            "json_path": child_prefix,
                            "value": child,
                        }
                    )
            rows.extend(_collect_relevant(child, prefix=child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(
                _collect_relevant(child, prefix=f"{prefix}[{index}]")
            )
    return rows


def _load_any_json(path: Path) -> object:
    source = ensure_regular_no_symlink(path, name=path.name)
    return strict_json_loads(source.read_bytes())


def _find_by_sha(
    roots: tuple[Path, ...],
    expected_sha256: str,
    *,
    max_file_bytes: int = 32 * 1024 * 1024,
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        root = ensure_directory_no_symlink(root, name="identity census root")
        for path in root.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            if sha256_file(path) == expected_sha256:
                matches.append(
                    {
                        "path": str(resolved),
                        "sha256": expected_sha256,
                        "size_bytes": path.stat().st_size,
                    }
                )
    return matches


def build_pi1_identity_authority_census(
    *,
    formal_a_runtime_roots: tuple[Path, ...],
    select_roots: tuple[Path, ...],
    checkpoint_root: Path,
) -> dict[str, object]:
    checkpoint = ensure_directory_no_symlink(
        checkpoint_root,
        name="frozen checkpoint-set root",
    )
    runtime_candidates: list[dict[str, object]] = []
    seen_runtime_sha: dict[str, list[str]] = {}

    for root in formal_a_runtime_roots:
        if not root.exists():
            continue
        root = ensure_directory_no_symlink(
            root, name="Formal-A runtime root"
        )
        for path in root.rglob("FORMAL_A0_RUNTIME_BINDING_V1.json"):
            if path.is_symlink() or not path.is_file():
                continue
            raw = _load_any_json(path)
            strings = [
                str(row["value"])
                for row in _collect_relevant(raw)
                if isinstance(row.get("value"), str)
            ]
            if TRAIN17 not in strings:
                continue
            digest = sha256_file(path)
            runtime_candidates.append(
                {
                    "path": str(path.resolve()),
                    "sha256": digest,
                    "relevant_fields": _collect_relevant(raw),
                }
            )
            seen_runtime_sha.setdefault(digest, []).append(
                str(path.resolve())
            )

    checkpoint_files = []
    for rel in (
        "checkpoint_set_manifest.json",
        "package_files.sha256",
        "provenance/execution_spec.json",
        "provenance/runner_manifest.json",
        "seed_17/adapter_artifact_manifest.json",
        "seed_17/formal_run_manifest.json",
        "seed_17/training_step_ledger.jsonl",
    ):
        path = checkpoint / rel
        if path.is_file() and not path.is_symlink():
            checkpoint_files.append(
                {
                    "relative_path": rel,
                    "path": str(path.resolve()),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )

    adapter_dir = checkpoint / "seed_17" / "adapter"
    adapter_present = (
        adapter_dir.is_dir() and not adapter_dir.is_symlink()
    )

    select_runtime_matches = _find_by_sha(
        select_roots,
        RUNTIME_SHA,
    )
    distinct_formal_a_runtime_shas = sorted(seen_runtime_sha)
    readiness = (
        "READY_FOR_EXPLICIT_PI1_IDENTITY_REGISTRATION_REVIEW"
        if (
            len(distinct_formal_a_runtime_shas) == 1
            and len(select_runtime_matches) >= 1
            and adapter_present
            and len(checkpoint_files) == 7
        )
        else "BLOCKED_IDENTITY_AUTHORITY_CENSUS_INCOMPLETE"
    )

    artifact = {
        "schema_id": "PI1_IDENTITY_AUTHORITY_CENSUS_V1",
        "schema_version": 1,
        "logical_policy_id": "P4-R1-Q2-BAD",
        "checkpoint_instance_id": TRAIN17,
        "expected_select_runtime_manifest_sha256": RUNTIME_SHA,
        "formal_a_runtime_binding_candidates": runtime_candidates,
        "formal_a_runtime_distinct_sha256s": distinct_formal_a_runtime_shas,
        "select_runtime_manifest_matches": select_runtime_matches,
        "frozen_checkpoint_root": str(checkpoint),
        "frozen_checkpoint_files": checkpoint_files,
        "seed17_adapter_directory": str(adapter_dir.resolve())
        if adapter_present
        else None,
        "seed17_adapter_directory_present": adapter_present,
        "selection_performed": False,
        "identity_registration_created": False,
        "identity_materialization_created": False,
        "readiness_status": readiness,
        "census_sha256": "0" * 64,
    }
    artifact["census_sha256"] = domain_hash(
        "PI1_IDENTITY_AUTHORITY_CENSUS_V1",
        artifact,
        excluded_field="census_sha256",
    )
    return artifact


def build_pi1_identity_authority_census_file(
    *,
    formal_a_runtime_roots: tuple[Path, ...],
    select_roots: tuple[Path, ...],
    checkpoint_root: Path,
    output_path: Path,
) -> dict[str, object]:
    artifact = build_pi1_identity_authority_census(
        formal_a_runtime_roots=formal_a_runtime_roots,
        select_roots=select_roots,
        checkpoint_root=checkpoint_root,
    )
    write_new_json(output_path, artifact)
    return artifact
