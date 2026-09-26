#!/usr/bin/env python3
"""Build an E1 gamefile SHA-256 manifest from explicit inputs."""

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
            "Build a no-clobber E1 gamefile identity "
            "manifest from an explicitly supplied task manifest."
        )
    )
    parser.add_argument(
        "--task-manifest",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--expected-manifest-sha256",
        required=True,
    )
    parser.add_argument(
        "--expected-record-count",
        type=int,
        default=134,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    from pchsi.evaluation.gamefile_identity import (
        build_gamefile_identity_manifest,
    )
    from pchsi.evaluation.task_manifest import (
        load_frozen_task_manifest,
    )

    records = load_frozen_task_manifest(
        manifest_path=args.task_manifest,
        expected_sha256=(
            args.expected_manifest_sha256
        ),
        expected_record_count=args.expected_record_count,
    )
    manifest = build_gamefile_identity_manifest(
        records=records,
        output_path=args.output,
    )

    print(
        json.dumps(
            {
                "manifest_id": manifest.manifest_id,
                "output": str(args.output),
                "record_count": manifest.record_count,
                "status": (
                    "E1_GAMEFILE_IDENTITY_MANIFEST_CREATED"
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
