#!/usr/bin/env python3
"""Generate a non-executing candidate classic-BPF instruction manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.security.canonical import canonical_json_bytes, sha256_hex
from pchsi.security.syscall_table import (
    build_seccomp_instruction_records,
    derive_p7_case_ids,
    load_syscall_table,
    p7_aggregate_deadline_seconds,
)


def _parse_allowlist(text: str) -> frozenset[int]:
    if not text:
        return frozenset()
    return frozenset(int(token, 10) for token in text.split(","))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--syscall-table", type=Path, required=True)
    parser.add_argument("--allowlist", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    table = load_syscall_table(arguments.syscall_table)
    allowlist = _parse_allowlist(arguments.allowlist)
    instructions = build_seccomp_instruction_records(
        syscall_table=table,
        collector_allowlist=allowlist,
    )
    cases = derive_p7_case_ids(
        syscall_table=table,
        collector_allowlist=allowlist,
    )
    payload = {
        "schema_version": "s1_seccomp_candidate_v1",
        "status": "candidate_pending_static_and_semantic_review",
        "architecture": table.architecture,
        "audit_arch": table.audit_arch,
        "syscall_table_sha256": table.exact_semantics_sha256,
        "allowlist": sorted(allowlist),
        "instructions": [
            instruction.to_dict()
            for instruction in instructions
        ],
        "p7_case_ids": list(cases),
        "p7_case_timeout_seconds": 2,
        "p7_aggregate_deadline_seconds": (
            p7_aggregate_deadline_seconds(len(cases))
        ),
    }
    encoded = canonical_json_bytes(payload)
    payload["candidate_exact_sha256"] = sha256_hex(encoded)

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(canonical_json_bytes(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# Task 14 candidate-artifact status marker.
CANDIDATE_ARTIFACT_STATUS = (
    "candidate_pending_static_and_semantic_review"
)
