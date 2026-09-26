#!/usr/bin/env python3
"""Freeze exact paths and identities for the complete Memory-owned closure run."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes


def regular(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=CLOSURE_INPUT_NOT_REGULAR:" + str(path))


def bind(path: Path) -> dict[str, object]:
    regular(path)
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "file_sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def write_new(path: Path, value: dict[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=CLOSURE_MANIFEST_OUTPUT_EXISTS")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fixed-head", required=True)
    p.add_argument("--scientific-program-sha256", required=True)
    p.add_argument("--stage0-result", required=True)
    p.add_argument("--a0-result", required=True)
    p.add_argument("--b-result", required=True)
    p.add_argument("--stage1b-execution-manifest", required=True)
    p.add_argument("--stage2-execution-manifest", required=True)
    p.add_argument("--stage3-execution-manifest", required=True)
    p.add_argument("--live-output-root", required=True)
    p.add_argument("--closure-output-root", required=True)
    p.add_argument("--execution-mode", choices=("local", "slurm"), default="slurm")
    p.add_argument("--max-parallel", type=int, default=8)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    if len(args.fixed_head) != 40 or any(c not in "0123456789abcdef" for c in args.fixed_head):
        raise SystemExit("STOP=CLOSURE_FIXED_HEAD_INVALID")
    if len(args.scientific_program_sha256) != 64 or any(c not in "0123456789abcdef" for c in args.scientific_program_sha256):
        raise SystemExit("STOP=CLOSURE_PROGRAM_SHA_INVALID")
    if args.max_parallel < 1:
        raise SystemExit("STOP=CLOSURE_MAX_PARALLEL_INVALID")
    inputs = {
        "stage0_result": bind(Path(args.stage0_result)),
        "a0_result": bind(Path(args.a0_result)),
        "b_result": bind(Path(args.b_result)),
        "stage1b_execution_manifest": bind(Path(args.stage1b_execution_manifest)),
        "stage2_execution_manifest": bind(Path(args.stage2_execution_manifest)),
        "stage3_execution_manifest": bind(Path(args.stage3_execution_manifest)),
    }
    payload = {
        "schema_id": "FAILURE_MEMORY_CLOSURE_EXECUTION_MANIFEST_V1",
        "schema_version": 1,
        "closure_execution_manifest_sha256": "0" * 64,
        "fixed_code_head": args.fixed_head,
        "scientific_program_sha256": args.scientific_program_sha256,
        "execution_mode": args.execution_mode,
        "max_parallel": args.max_parallel,
        "inputs": inputs,
        "live_output_root": str(Path(args.live_output_root).resolve()),
        "closure_output_root": str(Path(args.closure_output_root).resolve()),
        "scientific_execution_authorized": False,
        "q4_analyzer_execution_included": False,
        "q5_policy_training_included": False,
    }
    payload["closure_execution_manifest_sha256"] = hashlib.sha256(
        b"FAILURE_MEMORY_CLOSURE_EXECUTION_MANIFEST_V1\0"
        + canonical_json_bytes({k: v for k, v in payload.items() if k != "closure_execution_manifest_sha256"})
    ).hexdigest()
    write_new(Path(args.output), payload)
    print("FAILURE_MEMORY_CLOSURE_EXECUTION_MANIFEST_V1_PASS")
    print("CLOSURE_EXECUTION_MANIFEST_SHA256=" + payload["closure_execution_manifest_sha256"])
    print("SCIENTIFIC_EXECUTION_AUTHORIZED=false")


if __name__ == "__main__":
    main()
