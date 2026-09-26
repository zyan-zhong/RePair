from __future__ import annotations

import argparse
from pathlib import Path

from .contract import (
    APPROVAL_TOKEN,
    EXPECTED_BINDING_ROOT,
    EXPECTED_READINESS_RECEIPT,
    EXPECTED_READINESS_RECEIPT_SHA256,
    READINESS_PACKAGE_ROOT,
    EXPECTED_READINESS_PY_SHA256,
    EXPECTED_READINESS_COMMON_SHA256,
    Stage4DFullError,
    authorization_payload,
    authorization_sha,
    execution_root,
    load_json,
    require_sha,
    validate_readiness_receipt,
    verify_binding_inventory,
    verify_code_authority,
    verify_scientific_grid,
    write_or_reuse_exact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True)
    args = parser.parse_args(argv)
    if args.approval != APPROVAL_TOKEN:
        raise Stage4DFullError("EXPLICIT_FULL_SELECT_APPROVAL_REQUIRED")

    binding_root = EXPECTED_BINDING_ROOT
    verify_binding_inventory(binding_root)
    verify_scientific_grid(binding_root)
    code_worktree = verify_code_authority(binding_root)

    require_sha(READINESS_PACKAGE_ROOT / "stage4d_pkg/readiness.py", EXPECTED_READINESS_PY_SHA256, "READINESS_RUNTIME_SOURCE")
    require_sha(READINESS_PACKAGE_ROOT / "stage4d_pkg/common.py", EXPECTED_READINESS_COMMON_SHA256, "READINESS_COMMON_SOURCE")
    require_sha(EXPECTED_READINESS_RECEIPT, EXPECTED_READINESS_RECEIPT_SHA256, "READINESS_RECEIPT")
    readiness = load_json(EXPECTED_READINESS_RECEIPT)
    validate_readiness_receipt(readiness)

    auth = authorization_payload(
        binding_root=binding_root,
        readiness_receipt_sha256=EXPECTED_READINESS_RECEIPT_SHA256,
    )
    auth_sha = authorization_sha(auth)
    root = execution_root(auth_sha)
    root.mkdir(parents=True, exist_ok=True)
    write_or_reuse_exact(root / "STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_V1.json", auth)
    write_or_reuse_exact(root / "EXECUTION_IDENTITY_V1.json", {
        "schema_id": "STAGE4D_FULL_SELECT_EXECUTION_IDENTITY_V1",
        "schema_version": 1,
        "authorization_sha256": auth_sha,
        "binding_sha256": auth["binding_sha256"],
        "readiness_receipt_sha256": auth["readiness_receipt_sha256"],
        "code_worktree": str(code_worktree),
        "fixed_head": auth["fixed_head"],
        "scientific_total_condition_cells": auth["authorized_total_condition_cell_count"],
        "result_interpretation_authorized": False,
        "promotion_authorized": False,
    })
    print("STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_PASS")
    print(f"STAGE4D_EXECUTION_ROOT={root}")
    print(f"STAGE4D_EXECUTION_AUTHORIZATION_SHA256={auth_sha}")
    print("SCIENTIFIC_SELECT_CELL_EXECUTION_COUNT=0")
    print("EVALUATION_EXECUTION_AUTHORIZED=true")
    print("RESULT_INTERPRETATION_AUTHORIZED=false")
    print("PROMOTION_AUTHORIZED=false")
    print("NEXT_GATE=SUBMIT_RESUMABLE_FULL_SELECT_EXECUTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
