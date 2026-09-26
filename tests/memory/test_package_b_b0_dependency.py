from __future__ import annotations

from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.dev_descriptive_snapshot_v2 import (
    audit_calibrated_snapshot_v2,
)
from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
)


DEPENDENCY = Path(
    "configs/memory/package_b_failure_memory_dependency_v1.json"
)
CONTRACT = Path(
    "configs/memory/failure_memory_token_budget_contract_v1.json"
)


def test_b0_exact_dependency_binding_is_rehashable():
    payload = strict_json_loads(
        DEPENDENCY.read_bytes()
    )
    assert isinstance(payload, dict)

    assert payload["schema_id"] == (
        "PACKAGE_B_FAILURE_MEMORY_DEPENDENCY_V1"
    )
    assert payload["package_a_sealed_head"] == (
        "d6257c2e28f35f400d60b5ac835e1ebf70762dd5"
    )
    assert payload[
        "historical_package_a_snapshot_sha256"
    ] == (
        "df271ba7527ebaee104a888d82533832"
        "ada0a4aab8735f717767e5d1b1d51cc4"
    )
    assert payload["effect_authority"] == "UNTESTED"
    assert payload["previous_package_a_exposure"] == (
        "NOT_EXPOSED_PACKAGE_A"
    )
    assert (
        payload["memory_on_scientific_execution_completed"]
        is False
    )
    assert payload["performance_estimand"] == (
        "NO_PERFORMANCE_ESTIMAND"
    )

    contract = FailureMemoryTokenBudgetContractV1.from_json(
        CONTRACT.read_bytes()
    )
    assert payload["token_budget_contract_sha256"] == (
        contract.contract_sha256
    )

    snapshot_root = Path(
        payload["active_snapshot_external_directory"]
    )
    assert snapshot_root.is_dir()
    snapshot = audit_calibrated_snapshot_v2(
        snapshot_directory=snapshot_root,
        expected_snapshot_sha256=payload[
            "active_snapshot_sha256"
        ],
    )
    assert snapshot.token_budget_contract_sha256 == (
        contract.contract_sha256
    )

    audit_path = Path(
        payload["a9_dependency_audit_external_path"]
    )
    assert audit_path.is_file()
    assert sha256_file(audit_path) == (
        payload["a9_dependency_audit_sha256"]
    )
    a9 = strict_json_loads(audit_path.read_bytes())
    assert a9["dependency_status"] == "REUSE_ALLOWED"
    assert a9["environment_replay_rerun_required"] is False
    assert a9["policy_inference_rerun_required"] is False
