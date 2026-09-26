from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import domain_sha256, write_or_reuse_exact
from .constants import (
    APPROVAL_TOKEN,
    CANDIDATE_ADAPTER_SHA256,
    OFFOFF_HANDOFF_SHA256,
    PAIRED_CELL_COUNT,
    PARENT_ADAPTER_SHA256,
    PROTOCOL_EQUALITY_SHA256,
    TOTAL_CONDITION_CELL_COUNT,
)

SCHEMA_ID = "HUMAN_PILOT_STAGE0_EXECUTION_AUTHORIZATION_V1"


def prepare_authorization(
    *,
    output_path: Path,
    supplied_token: str,
    package_inventory_sha256: str,
    preflight_receipt_sha256: str,
) -> dict[str, Any]:
    if supplied_token != APPROVAL_TOKEN:
        raise ValueError("explicit Stage 0 execution approval is required")
    value: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "authorization_status": "APPROVED",
        "approval_token_id": APPROVAL_TOKEN,
        "round_role": "PILOT_ENGINEERING_ROUND_V1",
        "package_inventory_sha256": package_inventory_sha256,
        "preflight_receipt_sha256": preflight_receipt_sha256,
        "protocol_equality_sha256": PROTOCOL_EQUALITY_SHA256,
        "offoff_handoff_sha256": OFFOFF_HANDOFF_SHA256,
        "parent_adapter_bundle_sha256": PARENT_ADAPTER_SHA256,
        "candidate_adapter_bundle_sha256": CANDIDATE_ADAPTER_SHA256,
        "authorized_paired_cell_count": PAIRED_CELL_COUNT,
        "authorized_total_condition_cell_count": TOTAL_CONDITION_CELL_COUNT,
        "memory_off": True,
        "harness_off": True,
        "paper_efficacy_evidence": False,
        "promotion_decision_authorized": False,
        "promotion_eligible": False,
        "repository_commit_authorized": False,
        "repository_push_authorized": False,
        "authorization_sha256": "",
    }
    value["authorization_sha256"] = domain_sha256(
        SCHEMA_ID,
        value,
        sha_field="authorization_sha256",
    )
    return write_or_reuse_exact(output_path, value)
