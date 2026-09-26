#!/usr/bin/env python3
"""Validate and canonicalize an S1 x86-64 syscall table."""

from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.security.canonical import canonical_json_bytes
from pchsi.security.syscall_table import load_syscall_table


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    table = load_syscall_table(arguments.input)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(canonical_json_bytes(table.to_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# Task 14 candidate-artifact status marker.
CANDIDATE_ARTIFACT_STATUS = (
    "candidate_pending_static_and_semantic_review"
)
