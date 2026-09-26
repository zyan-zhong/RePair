#!/usr/bin/env python3
"""Build a deterministic environment runtime manifest from explicit files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build an ALFWorld environment runtime manifest "
            "from explicit fixture or readiness inputs."
        )
    )
    parser.add_argument("--python-version", required=True)
    parser.add_argument(
        "--python-executable",
        required=True,
        type=Path,
    )
    parser.add_argument("--alfworld-version", required=True)
    parser.add_argument("--textworld-version", required=True)
    parser.add_argument("--gym-version", required=True)
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        metavar="LOGICAL_NAME=PATH",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    return parser


def _parse_source(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise ValueError(
            "--source must use LOGICAL_NAME=PATH"
        )
    logical_name, raw_path = value.split("=", 1)
    if not logical_name or not raw_path:
        raise ValueError(
            "--source must use non-empty LOGICAL_NAME=PATH"
        )
    return logical_name, Path(raw_path)


def main() -> int:
    args = build_parser().parse_args()

    from pchsi.evaluation.canonical_evidence import (
        sha256_file,
    )
    from pchsi.evaluation.environment_runtime_manifest import (
        EnvironmentRuntimeInputs,
        SourceIdentity,
        build_environment_runtime_manifest,
    )

    sources = tuple(
        SourceIdentity(
            logical_name=logical_name,
            source_path=str(path.resolve(strict=True)),
            sha256=sha256_file(path),
        )
        for logical_name, path in (
            _parse_source(value)
            for value in args.source
        )
    )

    python_path = args.python_executable.resolve(
        strict=True
    )

    inputs = EnvironmentRuntimeInputs(
        python_version=args.python_version,
        python_executable_sha256=sha256_file(
            python_path
        ),
        alfworld_version=args.alfworld_version,
        textworld_version=args.textworld_version,
        gym_version=args.gym_version,
        source_identities=sources,
        wrapper_order=(
            "AlfredDemangler(shuffle=false)",
            "AlfredInfos",
        ),
        env_infos=(
            "won",
            "admissible_commands",
            "extra.gamefile",
        ),
        batch_size=1,
        asynchronous=False,
        auto_reset=False,
        max_episode_steps=31,
        process_start_method="spawn",
    )

    manifest = build_environment_runtime_manifest(
        inputs=inputs,
        output_path=args.output,
    )

    print(
        json.dumps(
            {
                "manifest_id": manifest.manifest_id,
                "output": str(args.output),
                "source_count": len(
                    manifest.source_identities
                ),
                "status": (
                    "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_CREATED"
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
