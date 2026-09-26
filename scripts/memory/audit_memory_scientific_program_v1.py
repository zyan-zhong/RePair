#!/usr/bin/env python3
"""Build the truthful Q1--Q5 matrix from sealed, validated authorities."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from pchsi.memory.scientific_program import build_current_q1_q5_matrix_v1


def _optional(value: str | None) -> Path | None:
    return None if value in {None, ""} else Path(value)


def _write_new(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a0-result", required=True)
    parser.add_argument("--b-result", required=True)
    parser.add_argument("--stage0-result")
    parser.add_argument("--stage1b-authority")
    parser.add_argument("--stage2-authority")
    parser.add_argument("--stage3-authority")
    parser.add_argument("--formal-c-authority")
    parser.add_argument("--off-off-authority")
    parser.add_argument("--expected-fixed-head")
    parser.add_argument("--expected-scientific-program-sha256")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    live_present = any((args.stage1b_authority, args.stage2_authority, args.stage3_authority))
    if live_present and (
        not args.expected_fixed_head
        or not args.expected_scientific_program_sha256
    ):
        raise SystemExit(
            "STOP=LIVE_AUTHORITIES_REQUIRE_EXPECTED_HEAD_AND_PROGRAM_SHA"
        )
    matrix = build_current_q1_q5_matrix_v1(
        a0_result_path=Path(args.a0_result),
        b_result_path=Path(args.b_result),
        stage0_result_path=_optional(args.stage0_result),
        stage1b_result_path=_optional(args.stage1b_authority),
        stage2_result_path=_optional(args.stage2_authority),
        stage3_result_path=_optional(args.stage3_authority),
        formal_c_result_path=_optional(args.formal_c_authority),
        off_off_result_path=_optional(args.off_off_authority),
        expected_fixed_code_head=args.expected_fixed_head,
        expected_scientific_program_sha256=(
            args.expected_scientific_program_sha256
        ),
    )
    _write_new(Path(args.output), matrix.canonical_bytes())
    print("FAILURE_MEMORY_Q1_Q5_MATRIX_WRITTEN")
    print("MATRIX_SHA256=" + matrix.matrix_sha256)
    for row in matrix.rows:
        print(row.question_id + "=" + row.status.value)


if __name__ == "__main__":
    main()
