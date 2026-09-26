#!/usr/bin/env python3
"""Build exact Package-B dependency binding after token-budget calibration."""

from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.dev_descriptive_snapshot_v2 import (
    audit_calibrated_snapshot_v2,
)
from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-a-sealed-head", required=True)
    parser.add_argument("--historical-snapshot-sha256", required=True)
    parser.add_argument("--token-budget-contract", required=True)
    parser.add_argument("--active-snapshot-directory", required=True)
    parser.add_argument("--a9-dependency-audit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    contract_path = Path(args.token_budget_contract)
    contract_raw = contract_path.read_bytes()
    contract = FailureMemoryTokenBudgetContractV1.from_json(
        contract_raw
    )

    active_root = Path(args.active_snapshot_directory)
    snapshot = audit_calibrated_snapshot_v2(
        snapshot_directory=active_root,
        expected_snapshot_sha256=active_root.name,
    )

    if (
        snapshot.package_a_sealed_head
        != args.package_a_sealed_head
        or snapshot.historical_package_a_snapshot_sha256
        != args.historical_snapshot_sha256
        or snapshot.token_budget_contract_sha256
        != contract.contract_sha256
        or snapshot.effect_authority != "UNTESTED"
        or snapshot.previous_package_a_exposure
        != "NOT_EXPOSED_PACKAGE_A"
    ):
        raise SystemExit(
            "STOP=PACKAGE_B_ACTIVE_SNAPSHOT_DEPENDENCY_MISMATCH"
        )

    audit_path = Path(args.a9_dependency_audit)
    audit_raw = audit_path.read_bytes()
    audit = strict_json_loads(audit_raw)
    if (
        not isinstance(audit, dict)
        or audit.get("schema_id")
        != "FAILURE_MEMORY_A9_TOKEN_BUDGET_DEPENDENCY_AUDIT_V1"
        or audit.get("dependency_status") != "REUSE_ALLOWED"
        or audit.get("environment_replay_rerun_required") is not False
        or audit.get("policy_inference_rerun_required") is not False
        or audit.get("new_snapshot_sha256")
        != snapshot.snapshot_sha256
        or audit.get("token_budget_contract_sha256")
        != contract.contract_sha256
    ):
        raise SystemExit("STOP=PACKAGE_B_A9_DEPENDENCY_AUDIT_INVALID")

    payload = {
        "schema_id": "PACKAGE_B_FAILURE_MEMORY_DEPENDENCY_V1",
        "schema_version": 1,
        "package_a_sealed_head": args.package_a_sealed_head,
        "historical_package_a_snapshot_sha256": (
            args.historical_snapshot_sha256
        ),
        "token_budget_contract_sha256": (
            contract.contract_sha256
        ),
        "active_snapshot_schema_id": snapshot.schema_id,
        "active_snapshot_sha256": snapshot.snapshot_sha256,
        "active_snapshot_external_directory": str(
            active_root.resolve()
        ),
        "a9_dependency_audit_external_path": str(
            audit_path.resolve()
        ),
        "a9_dependency_audit_sha256": sha256_bytes(
            audit_raw
        ),
        "a9_environment_replay_reused": True,
        "effect_authority": "UNTESTED",
        "previous_package_a_exposure": (
            "NOT_EXPOSED_PACKAGE_A"
        ),
        "memory_on_scientific_execution_completed": False,
        "performance_estimand": "NO_PERFORMANCE_ESTIMAND",
    }
    raw = canonical_json_bytes(payload)

    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=PACKAGE_B_DEPENDENCY_OUTPUT_EXISTS")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)

    print(
        "PACKAGE_B_ACTIVE_SNAPSHOT_SHA256="
        + snapshot.snapshot_sha256
    )
    print(
        "PACKAGE_B_TOKEN_BUDGET_CONTRACT_SHA256="
        + contract.contract_sha256
    )
    print("PACKAGE_B_A9_ENVIRONMENT_REPLAY_REUSED=true")
    print("PACKAGE_B_TASK_B0_DEPENDENCY_CLOSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
