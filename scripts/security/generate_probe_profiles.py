#!/usr/bin/env python3
"""Generate deterministic candidate S1 probe profile descriptions."""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Sequence


CANDIDATE_STATUS = "candidate_pending_static_and_semantic_review"

PROFILE_IDS = (
    "S1_PRODUCTION_V1",
    "S1_P7_SYSCALL_CASE_V1",
    "S1_P15_RLIMIT_ATTRIBUTION_V1",
    "S1_P18_LANDLOCK_ATTRIBUTION_V1",
    "S1_P20_CLEANUP_V1",
)


def canonical_profile_payload(profile_id: str) -> bytes:
    if profile_id not in PROFILE_IDS:
        raise ValueError("unknown profile_id")

    payload = {
        "profile_id": profile_id,
        "schema_version": 1,
        "status": CANDIDATE_STATUS,
    }

    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def profile_sha256(profile_id: str) -> str:
    return hashlib.sha256(
        canonical_profile_payload(profile_id)
    ).hexdigest()


def describe_profiles() -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": CANDIDATE_STATUS,
        "profiles": [
            {
                "profile_id": profile_id,
                "sha256": profile_sha256(profile_id),
            }
            for profile_id in PROFILE_IDS
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(
        json.dumps(
            describe_profiles(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# Task 14 candidate-artifact status marker.
CANDIDATE_ARTIFACT_STATUS = (
    "candidate_pending_static_and_semantic_review"
)
