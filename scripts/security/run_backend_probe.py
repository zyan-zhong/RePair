#!/usr/bin/env python3
"""Closed command surface for the dataset-bound S1 probe candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from pchsi.security.execution_gate import (
    EXECUTION_NOT_APPROVED_MARKER,
    ExecutionNotApprovedError,
    require_execution_approval,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--describe", action="store_true")
    mode.add_argument("--execute", action="store_true")

    parser.add_argument("--execution-record", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

    if arguments.describe:
        print(
            json.dumps(
                {
                    "design_id": "S1_COLLECTOR_BACKEND_PROBE_V1",
                    "dataset_version": "json_2.1.1",
                    "requires_external_execution_decision": True,
                    "status": "NOT_APPROVED",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0

    try:
        require_execution_approval(
            approval_path=arguments.execution_record,
            expected_design_commit="0" * 40,
            expected_artifact_manifest_sha256=None,
        )
    except ExecutionNotApprovedError as error:
        print(str(error), file=sys.stderr)
        return 77

    print(
        f"{EXECUTION_NOT_APPROVED_MARKER}: unreachable closed gate",
        file=sys.stderr,
    )
    return 77


if __name__ == "__main__":
    raise SystemExit(main())
