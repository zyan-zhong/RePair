#!/usr/bin/env python3
"""Build one correction-evidence artifact from an explicit request JSON.

This CLI does not enumerate ALFWorld, generate a task split, or derive task
membership.  The request must point to already-created reproduction bytes and
incident evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pchsi.memory.task_access_sha_authority_correction import (
    CorrectionEvidenceRequestV1,
    IncidentEvidenceInputV1,
    ReproductionInputV1,
    TaskAccessShaAuthorityCorrectionError,
    write_correction_evidence,
)


def _role_counts(
    payload: object,
) -> tuple[tuple[str, int], ...]:
    if type(payload) is not dict:
        raise TaskAccessShaAuthorityCorrectionError(
            "REQUEST_ROLE_COUNTS_NOT_OBJECT"
        )
    result: list[tuple[str, int]] = []
    for key, value in payload.items():
        if not isinstance(key, str):
            raise TaskAccessShaAuthorityCorrectionError(
                "REQUEST_ROLE_COUNT_KEY_INVALID"
            )
        if type(value) is not int:
            raise TaskAccessShaAuthorityCorrectionError(
                "REQUEST_ROLE_COUNT_VALUE_INVALID"
            )
        result.append((key, value))
    return tuple(sorted(result))


def _load_request(
    path: Path,
) -> CorrectionEvidenceRequestV1:
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise TaskAccessShaAuthorityCorrectionError(
            "REQUEST_JSON_UNREADABLE"
        ) from exc

    if type(payload) is not dict:
        raise TaskAccessShaAuthorityCorrectionError(
            "REQUEST_JSON_NOT_OBJECT"
        )

    reproductions_payload = payload.get(
        "reproductions"
    )
    if type(reproductions_payload) is not list:
        raise TaskAccessShaAuthorityCorrectionError(
            "REQUEST_REPRODUCTIONS_NOT_ARRAY"
        )

    reproductions = tuple(
        ReproductionInputV1(
            reproduction_id=str(
                item["reproduction_id"]
            ),
            implementation_identity=str(
                item["implementation_identity"]
            ),
            implementation_path=Path(
                item["implementation_path"]
            ),
            canonical_output_path=Path(
                item["canonical_output_path"]
            ),
            declared_observed_protected_sha256=str(
                item[
                    "declared_observed_protected_sha256"
                ]
            ),
            source_fingerprint=str(
                item["source_fingerprint"]
            ),
            record_count=int(
                item["record_count"]
            ),
            role_counts=_role_counts(
                item["role_counts"]
            ),
        )
        for item in reproductions_payload
    )

    incident_payload = payload.get(
        "incident_evidence"
    )
    if type(incident_payload) is not list:
        raise TaskAccessShaAuthorityCorrectionError(
            "REQUEST_INCIDENT_EVIDENCE_NOT_ARRAY"
        )

    incidents = tuple(
        IncidentEvidenceInputV1(
            artifact_id=str(
                item["artifact_id"]
            ),
            path=Path(
                item["path"]
            ),
            expected_sha256=str(
                item["expected_sha256"]
            ),
        )
        for item in incident_payload
    )

    return CorrectionEvidenceRequestV1(
        correction_base_commit=str(
            payload["correction_base_commit"]
        ),
        correction_design_commit=str(
            payload["correction_design_commit"]
        ),
        access_policy_id=str(
            payload["access_policy_id"]
        ),
        historical_design_candidate_sha256=str(
            payload[
                "historical_design_candidate_sha256"
            ]
        ),
        proposed_exact_contract_protected_sha256=str(
            payload[
                "proposed_exact_contract_protected_sha256"
            ]
        ),
        dataset_source_fingerprint=str(
            payload["dataset_source_fingerprint"]
        ),
        record_count=int(
            payload["record_count"]
        ),
        role_counts=_role_counts(
            payload["role_counts"]
        ),
        reproductions=reproductions,
        incident_evidence=incidents,
    )


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--request",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    args = parser.parse_args(argv)

    try:
        request = _load_request(
            args.request
        )
        result = write_correction_evidence(
            request,
            args.output,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        TaskAccessShaAuthorityCorrectionError,
    ) as exc:
        print(
            "TASK_ACCESS_SHA_AUTHORITY_"
            f"CORRECTION_EVIDENCE_STOP={exc}",
            file=sys.stderr,
        )
        return 2

    print(
        "TASK_ACCESS_SHA_AUTHORITY_"
        "CORRECTION_EVIDENCE_BUILT=true"
    )
    print(
        "evidence_sha256="
        + result.evidence_sha256
    )
    print(
        "record_count="
        + str(
            result.payload["record_count"]
        )
    )
    print(
        "all_three_sha256_equal="
        + str(
            result.payload[
                "all_three_sha256_equal"
            ]
        ).lower()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
