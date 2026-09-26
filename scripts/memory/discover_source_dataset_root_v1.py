#!/usr/bin/env python3
"""Discover the unique local dataset root for protected Memory task access."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from pchsi.evaluation.canonical_evidence import (
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)


PROTECTED_TASK_ACCESS_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)


def _candidate_root_from_match(match: Path, relative: str) -> Path:
    parts = Path(relative).parts
    candidate = match
    for _ in parts:
        candidate = candidate.parent
    return candidate.resolve()


def _direct_dataset_root_candidates(
    scan_roots: tuple[Path, ...],
) -> tuple[Path, ...]:
    """Return explicit ALFWorld json_2.1.1 roots without broad cache walks."""

    bases: list[Path] = []

    env_data = os.environ.get("ALFWORLD_DATA")
    if env_data:
        bases.append(Path(env_data))

    try:
        from alfworld.info import ALFWORLD_DATA as package_data
    except Exception:
        package_data = None

    if isinstance(package_data, (str, os.PathLike)) and str(package_data):
        bases.append(Path(package_data))

    bases.append(Path.home() / ".cache" / "alfworld")

    for search_root in scan_roots:
        bases.extend(
            (
                search_root / ".cache" / "alfworld",
                search_root / "alfworld",
                search_root,
            )
        )

    result: list[Path] = []
    seen: set[str] = set()

    for base in bases:
        candidate = (
            base
            if base.name == "json_2.1.1"
            else base / "json_2.1.1"
        )
        try:
            if candidate.is_symlink() or not candidate.is_dir():
                continue
            resolved = candidate.resolve()
        except OSError:
            continue

        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        result.append(resolved)

    return tuple(sorted(result, key=lambda path: str(path)))


def _probe_candidate(
    *,
    dataset_root: Path,
    relative: str,
    expected_sha256: str,
) -> bool:
    path = dataset_root / relative

    try:
        resolved = path.resolve()
        resolved.relative_to(dataset_root)
    except (OSError, ValueError):
        return False

    if path.is_symlink() or not path.is_file():
        return False

    try:
        return sha256_file(path) == expected_sha256
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protected-task-access-manifest",
        required=True,
    )
    parser.add_argument(
        "--search-root",
        action="append",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    args = parser.parse_args()

    protected = Path(args.protected_task_access_manifest)
    if protected.is_symlink() or not protected.is_file():
        raise SystemExit(
            "STOP=PROTECTED_TASK_ACCESS_PATH_INVALID"
        )

    raw = protected.read_bytes()

    if sha256_bytes(raw) != PROTECTED_TASK_ACCESS_SHA256:
        raise SystemExit(
            "STOP=PROTECTED_TASK_ACCESS_SHA_MISMATCH"
        )

    source_records = []

    for line in raw.splitlines(keepends=True):
        payload = strict_json_loads(line)

        if (
            isinstance(payload, dict)
            and payload.get("access_class")
            == "TRAIN_MEMORY_SOURCE"
        ):
            source_records.append(payload)

    if len(source_records) != 2367:
        raise SystemExit(
            "STOP=TRAIN_MEMORY_SOURCE_POPULATION_MISMATCH:"
            + str(len(source_records))
        )

    probe_indices = (
        0,
        len(source_records) // 2,
        len(source_records) - 1,
    )
    probes = [
        source_records[index]
        for index in probe_indices
    ]

    scan_roots = tuple(
        Path(item).resolve()
        for item in args.search_root
    )

    direct_roots = (
        _direct_dataset_root_candidates(
            scan_roots
        )
    )

    for candidate in direct_roots:
        print(
            "DIRECT_ALFWORLD_DATASET_CANDIDATE="
            + str(candidate)
        )

    candidate_sets = []

    for probe in probes:
        relative = probe[
            "dataset_relative_gamefile"
        ]
        expected_sha = probe[
            "gamefile_sha256"
        ]
        matches: list[Path] = []

        for dataset_root in direct_roots:
            if _probe_candidate(
                dataset_root=dataset_root,
                relative=relative,
                expected_sha256=expected_sha,
            ):
                matches.append(dataset_root)

        # Project-specific mirrors may exist outside standard ALFWorld roots.
        # Keep broad .cache traversal pruned to avoid walking unrelated model
        # caches; the official ALFWorld cache was already checked explicitly.
        for search_root in scan_roots:
            if not search_root.is_dir():
                continue

            target_name = Path(
                relative
            ).name

            for (
                dirpath,
                dirnames,
                filenames,
            ) in os.walk(
                search_root,
                topdown=True,
            ):
                dirnames[:] = [
                    name
                    for name in dirnames
                    if name
                    not in {
                        ".git",
                        "__pycache__",
                        ".pytest_cache",
                        "node_modules",
                        "build",
                        "conda_envs",
                        ".cache",
                        "site-packages",
                    }
                ]

                if (
                    target_name
                    not in filenames
                ):
                    continue

                path = (
                    Path(dirpath)
                    / target_name
                )

                try:
                    resolved = (
                        path.resolve()
                    )
                except OSError:
                    continue

                if not (
                    resolved
                    .as_posix()
                    .endswith(
                        "/"
                        + relative
                    )
                ):
                    continue

                if (
                    path.is_symlink()
                    or not path.is_file()
                ):
                    continue

                try:
                    if (
                        sha256_file(path)
                        != expected_sha
                    ):
                        continue
                except OSError:
                    continue

                matches.append(
                    _candidate_root_from_match(
                        resolved,
                        relative,
                    )
                )

        candidates = {
            str(path.resolve())
            for path in matches
        }

        if not candidates:
            raise SystemExit(
                "STOP=DATASET_ROOT_PROBE_NOT_FOUND:"
                + relative
            )

        candidate_sets.append(
            candidates
        )

    common = set.intersection(
        *candidate_sets
    )

    if len(common) != 1:
        raise SystemExit(
            "STOP=DATASET_ROOT_NOT_UNIQUE:"
            + repr(
                sorted(common)
            )
        )

    dataset_root = Path(
        next(iter(common))
    )

    if (
        dataset_root.is_symlink()
        or not dataset_root.is_dir()
    ):
        raise SystemExit(
            "STOP=DATASET_ROOT_INVALID"
        )

    for index, record in enumerate(
        source_records
    ):
        relative = record[
            "dataset_relative_gamefile"
        ]
        path = (
            dataset_root
            / relative
        ).resolve()

        try:
            path.relative_to(
                dataset_root
            )
        except ValueError as exc:
            raise SystemExit(
                "STOP=DATASET_PATH_ESCAPE:"
                + str(index)
            ) from exc

        if (
            path.is_symlink()
            or not path.is_file()
        ):
            raise SystemExit(
                "STOP=DATASET_GAMEFILE_MISSING:"
                + str(index)
                + ":"
                + relative
            )

        if (
            sha256_file(path)
            != record[
                "gamefile_sha256"
            ]
        ):
            raise SystemExit(
                "STOP=DATASET_GAMEFILE_SHA_MISMATCH:"
                + str(index)
            )

    payload = {
        "schema_id": (
            "FAILURE_MEMORY_"
            "SOURCE_DATASET_ROOT_BINDING_V1"
        ),
        "schema_version": 1,
        "protected_task_access_manifest_sha256": (
            PROTECTED_TASK_ACCESS_SHA256
        ),
        "dataset_root": (
            str(dataset_root)
        ),
        "verified_train_memory_source_record_count": (
            len(source_records)
        ),
        "selection_rule": (
            "EXPLICIT_ALFWORLD_DATA_ROOTS_"
            "PLUS_BOUNDED_FALLBACK_"
            "THEN_FULL_2367_SHA_AUDIT_V1"
        ),
    }

    output = Path(
        args.output
    )

    if (
        output.exists()
        or output.is_symlink()
    ):
        raise SystemExit(
            "STOP=DATASET_BINDING_OUTPUT_ALREADY_EXISTS"
        )

    output.write_bytes(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )

    print(
        "SOURCE_DATASET_ROOT="
        + str(dataset_root)
    )

    print(
        "SOURCE_DATASET_FULL_2367_SHA_AUDIT_PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
