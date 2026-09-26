#!/usr/bin/env python3
"""Audit whether Package-A environment-only A9 replay is token-budget independent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1,
    SourceStateReplayReportV1,
)


FORBIDDEN_KEY_FRAGMENTS = (
    "snapshot",
    "fm1",
    "fm2",
    "projection",
    "token_budget",
    "token_ceiling",
)


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _walk_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _parse_replay_report(path: Path) -> SourceStateReplayReportV1:
    raw = path.read_bytes()
    payload = strict_json_loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("replay report must be object")
    report = SourceStateReplayReportV1(
        schema_id=payload["schema_id"],
        schema_version=payload["schema_version"],
        source_fingerprint_sha256=payload[
            "source_fingerprint_sha256"
        ],
        replay_fingerprint_sha256=payload[
            "replay_fingerprint_sha256"
        ],
        transition_count=payload["transition_count"],
        status=payload["status"],
        failure_code=payload["failure_code"],
        report_sha256=payload["report_sha256"],
    )
    if report.canonical_bytes() != raw:
        raise ValueError("replay report is not canonical")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-manifest", required=True)
    parser.add_argument("--replay-root", required=True)
    parser.add_argument("--historical-candidate-root", required=True)
    parser.add_argument("--historical-snapshot-sha256", required=True)
    parser.add_argument("--historical-a9-receipt", required=True)
    parser.add_argument("--new-snapshot-sha256", required=True)
    parser.add_argument("--token-budget-contract-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    replay_manifest_path = Path(args.replay_manifest)
    replay_manifest_raw = replay_manifest_path.read_bytes()
    replay_manifest = strict_json_loads(replay_manifest_raw)

    if not isinstance(replay_manifest, dict):
        raise SystemExit("STOP=A9_REPLAY_MANIFEST_NOT_OBJECT")
    cases = replay_manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 3:
        raise SystemExit("STOP=A9_REPLAY_MANIFEST_CASE_COUNT_NOT_THREE")

    historical_candidates = Path(
        args.historical_candidate_root
    )
    if (
        historical_candidates.is_symlink()
        or not historical_candidates.is_dir()
    ):
        raise SystemExit("STOP=HISTORICAL_CANDIDATE_ROOT_INVALID")

    forbidden_values = {
        args.historical_snapshot_sha256,
    }

    for candidate in historical_candidates.iterdir():
        if not candidate.is_dir() or candidate.name.startswith("."):
            continue
        for name in ("fm1.json", "fm2.json"):
            path = candidate / name
            if not path.is_file():
                raise SystemExit(
                    "STOP=HISTORICAL_PROJECTION_ARTIFACT_MISSING:"
                    + candidate.name
                    + ":"
                    + name
                )
            forbidden_values.add(sha256_file(path))

    replay_root = Path(args.replay_root)
    if replay_root.is_symlink() or not replay_root.is_dir():
        raise SystemExit("STOP=HISTORICAL_REPLAY_ROOT_INVALID")

    replay_evidence_sha256s = []

    for case in cases:
        replay_source_path = Path(case["replay_source_path"])
        replay_source_raw = replay_source_path.read_bytes()
        if (
            hashlib.sha256(replay_source_raw).hexdigest()
            != case["replay_source_sha256"]
        ):
            raise SystemExit("STOP=A9_REPLAY_SOURCE_SHA_MISMATCH")

        source = RegisteredReplaySourceV1.from_json(
            replay_source_raw
        )
        if source.canonical_bytes() != replay_source_raw:
            raise SystemExit("STOP=A9_REPLAY_SOURCE_NOT_CANONICAL")

        payload = source.to_dict()

        bad_keys = sorted(
            key
            for key in _walk_keys(payload)
            if any(
                fragment in key.casefold()
                for fragment in FORBIDDEN_KEY_FRAGMENTS
            )
        )
        if bad_keys:
            raise SystemExit(
                "STOP=A9_REPLAY_SOURCE_HAS_PROJECTION_DEPENDENCY_KEY:"
                + repr(bad_keys)
            )

        strings = set(_walk_strings(payload))
        overlap = sorted(strings & forbidden_values)
        if overlap:
            raise SystemExit(
                "STOP=A9_REPLAY_SOURCE_BINDS_OLD_PROJECTION_OR_SNAPSHOT:"
                + repr(overlap)
            )

        case_root = replay_root / case["case_id"]
        first_path = case_root / "reconstruction_a.json"
        second_path = case_root / "reconstruction_b.json"
        first = _parse_replay_report(first_path)
        second = _parse_replay_report(second_path)

        expected = (
            source.expected_source_fingerprint.fingerprint_sha256
        )
        for report in (first, second):
            if (
                report.source_fingerprint_sha256 != expected
                or report.replay_fingerprint_sha256 != expected
                or report.status != "PASS"
                or report.failure_code is not None
            ):
                raise SystemExit(
                    "STOP=A9_HISTORICAL_REPLAY_REPORT_NOT_REUSABLE:"
                    + case["case_id"]
                )

        replay_evidence_sha256s.extend(
            (
                sha256_file(replay_source_path),
                sha256_file(first_path),
                sha256_file(second_path),
            )
        )

    old_receipt_path = Path(args.historical_a9_receipt)
    old_receipt_raw = old_receipt_path.read_bytes()
    old_receipt = strict_json_loads(old_receipt_raw)
    if not isinstance(old_receipt, dict):
        raise SystemExit("STOP=HISTORICAL_A9_RECEIPT_NOT_OBJECT")

    # The integrated Package-A receipt is expected to mention the historical
    # snapshot. That wrapper does not make the environment-only reconstruction
    # reports projection-dependent; this audit explicitly rebinds only the
    # environment replay authority.
    if (
        old_receipt.get("real_alfworld_environment_replay_executed")
        is not True
        or old_receipt.get("policy_inference_executed_during_a9")
        is not False
        or old_receipt.get("memory_continuation_executed")
        is not False
    ):
        raise SystemExit("STOP=HISTORICAL_A9_RECEIPT_SCOPE_INVALID")

    report = {
        "schema_id": (
            "FAILURE_MEMORY_A9_TOKEN_BUDGET_DEPENDENCY_AUDIT_V1"
        ),
        "schema_version": 1,
        "dependency_status": "REUSE_ALLOWED",
        "historical_replay_manifest_sha256": hashlib.sha256(
            replay_manifest_raw
        ).hexdigest(),
        "historical_replay_evidence_sha256s": sorted(
            replay_evidence_sha256s
        ),
        "historical_a9_receipt_sha256": hashlib.sha256(
            old_receipt_raw
        ).hexdigest(),
        "historical_snapshot_sha256": (
            args.historical_snapshot_sha256
        ),
        "new_snapshot_sha256": args.new_snapshot_sha256,
        "token_budget_contract_sha256": (
            args.token_budget_contract_sha256
        ),
        "environment_replay_depends_on_policy_projection": False,
        "environment_replay_depends_on_active_snapshot": False,
        "environment_replay_depends_on_token_ceiling": False,
        "environment_replay_depends_on_source_fingerprint": True,
        "policy_inference_rerun_required": False,
        "environment_replay_rerun_required": False,
        "scientific_reason": (
            "Registered replay sources and reconstruction reports bind source "
            "task/gamefile, environment runtime, executed prefix, M0, visible "
            "state and source fingerprint; no snapshot/FM1/FM2/token-budget "
            "identity is present in the environment-only replay authority."
        ),
    }

    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=A9_DEPENDENCY_AUDIT_OUTPUT_EXISTS")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(report))

    print("A9_TOKEN_BUDGET_DEPENDENCY_STATUS=REUSE_ALLOWED")
    print("A9_ENVIRONMENT_REPLAY_RERUN_REQUIRED=false")
    print("A9_POLICY_INFERENCE_RERUN_REQUIRED=false")
    print("A9_TOKEN_BUDGET_DEPENDENCY_AUDIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
