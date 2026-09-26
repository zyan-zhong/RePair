#!/usr/bin/env python3
"""Prepare a non-executing S1 backend-probe decision preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from pchsi.security.execution_preflight import (
    PREFLIGHT_STATUS,
    PreflightError,
    build_preflight_bundle,
)


_EXECUTION_NOT_APPROVED = "PCHSI_EXECUTION_NOT_APPROVED"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--describe", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")

    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--preflight-source-commit")
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--legacy-manifest", type=Path)
    parser.add_argument("--input-contract", type=Path)
    parser.add_argument("--logical-root-id")
    parser.add_argument(
        "--mountinfo-path",
        type=Path,
        default=Path("/proc/self/mountinfo"),
    )
    parser.add_argument("--native-binary", type=Path)
    parser.add_argument("--profile-description", type=Path)
    parser.add_argument("--decision-schema", type=Path)
    parser.add_argument("--output-root", type=Path)

    return parser


def _require_prepare_arguments(
    arguments: argparse.Namespace,
) -> None:
    required = (
        "repository_root",
        "preflight_source_commit",
        "dataset_root",
        "legacy_manifest",
        "input_contract",
        "logical_root_id",
        "native_binary",
        "profile_description",
        "decision_schema",
        "output_root",
    )
    missing = [
        name
        for name in required
        if getattr(arguments, name) is None
    ]
    if missing:
        raise PreflightError(
            "missing --prepare arguments: "
            + ", ".join(sorted(missing))
        )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

    if arguments.describe:
        print(
            json.dumps(
                {
                    "design_id": (
                        "S1_BACKEND_PROBE_EXECUTION_PREFLIGHT_V1"
                    ),
                    "status": PREFLIGHT_STATUS,
                    "backend_probe_execution": "NOT_APPROVED",
                    "read_only_inventory_execution": "NOT_APPROVED",
                    "writes_repository": False,
                    "executes_probe": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0

    if arguments.execute:
        print(
            f"{_EXECUTION_NOT_APPROVED}: "
            "execution preflight cannot execute P1-P20",
            file=sys.stderr,
        )
        return 77

    try:
        _require_prepare_arguments(arguments)
        result = build_preflight_bundle(
            repository_root=arguments.repository_root,
            preflight_source_commit=(
                arguments.preflight_source_commit
            ),
            dataset_root=arguments.dataset_root,
            legacy_manifest=arguments.legacy_manifest,
            input_contract=arguments.input_contract,
            logical_root_id=arguments.logical_root_id,
            mountinfo_path=arguments.mountinfo_path,
            native_binary=arguments.native_binary,
            profile_description=arguments.profile_description,
            decision_schema=arguments.decision_schema,
            output_root=arguments.output_root,
        )
    except (OSError, PreflightError, ValueError) as error:
        print(f"PCHSI_PREFLIGHT_ERROR: {error}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
