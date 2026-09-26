from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

import pytest

from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
    LIBRARY_TOTAL_CANDIDATES_V1,
    SINGLE_RECORD_CANDIDATES_V1,
)


SCRIPT = (
    Path(__file__).parents[2]
    / "scripts/memory/build_memory_final_live_inputs_v1.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "_fm_final_token_budget_binding_test",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _contract() -> FailureMemoryTokenBudgetContractV1:
    # 20/20 records are covered by the smallest frozen candidate.
    fm1 = tuple([100] * 20)
    fm2 = tuple([80] * 20)
    packs = tuple([200] * 20)
    return FailureMemoryTokenBudgetContractV1(
        schema_id="FAILURE_MEMORY_TOKEN_BUDGET_CONTRACT_V1",
        schema_version=1,
        source_panel_manifest_sha256="1" * 64,
        calibration_failure_panel_sha256="2" * 64,
        analyzer_prompt_sha256="3" * 64,
        analyzer_model="test-analyzer",
        tokenizer_id="test-tokenizer",
        tokenizer_revision="test-revision",
        calibration_failure_count=30,
        valid_calibration_record_count=20,
        fm1_token_counts=fm1,
        fm2_token_counts=fm2,
        library_pack_token_counts=packs,
        single_record_candidates=SINGLE_RECORD_CANDIDATES_V1,
        library_total_candidates=LIBRARY_TOTAL_CANDIDATES_V1,
        coverage_target=0.90,
        single_record_hard_ceiling=256,
        library_total_hard_ceiling=384,
        max_record_count=3,
        fm1_truncation_policy="FORBIDDEN",
        fm1_llm_compression_policy="FORBIDDEN",
        fm1_posthoc_excerpt_policy="FORBIDDEN",
        performance_estimand="NO_PERFORMANCE_ESTIMAND",
        memory_on_execution_used=False,
    )


def test_token_budget_resolver_matches_semantic_contract_sha_not_file_sha(
    tmp_path: Path,
) -> None:
    module = _load()
    contract = _contract()
    path = tmp_path / "token_budget_contract.json"
    raw = contract.canonical_bytes()
    path.write_bytes(raw)

    assert contract.contract_sha256 is not None
    assert hashlib.sha256(raw).hexdigest() != contract.contract_sha256

    resolved = module._resolve_token_budget_contract_v1(
        files=(path,),
        expected_contract_sha256=contract.contract_sha256,
        override_env=None,
    )
    assert resolved == path


def test_token_budget_resolver_accepts_exact_path_override_by_semantic_sha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()
    contract = _contract()
    path = tmp_path / "token_budget_contract.json"
    path.write_bytes(contract.canonical_bytes())
    assert contract.contract_sha256 is not None

    monkeypatch.setenv("TEST_TOKEN_BUDGET_OVERRIDE", str(path))
    resolved = module._resolve_token_budget_contract_v1(
        files=(),
        expected_contract_sha256=contract.contract_sha256,
        override_env="TEST_TOKEN_BUDGET_OVERRIDE",
    )
    assert resolved == path


def test_token_budget_resolver_rejects_override_with_wrong_semantic_sha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()
    contract = _contract()
    path = tmp_path / "token_budget_contract.json"
    path.write_bytes(contract.canonical_bytes())

    monkeypatch.setenv("TEST_TOKEN_BUDGET_OVERRIDE", str(path))
    with pytest.raises(
        SystemExit,
        match="OVERRIDE_TOKEN_BUDGET_CONTRACT_SHA_MISMATCH",
    ):
        module._resolve_token_budget_contract_v1(
            files=(),
            expected_contract_sha256="f" * 64,
            override_env="TEST_TOKEN_BUDGET_OVERRIDE",
        )


def test_token_budget_resolver_allows_byte_identical_copies(
    tmp_path: Path,
) -> None:
    module = _load()
    contract = _contract()
    assert contract.contract_sha256 is not None

    first = tmp_path / "a.json"
    second = tmp_path / "longer-copy-name.json"
    raw = contract.canonical_bytes()
    first.write_bytes(raw)
    second.write_bytes(raw)

    resolved = module._resolve_token_budget_contract_v1(
        files=(second, first),
        expected_contract_sha256=contract.contract_sha256,
        override_env=None,
    )
    assert resolved == first


def test_token_budget_resolver_fails_when_semantic_contract_not_found(
    tmp_path: Path,
) -> None:
    module = _load()
    contract = _contract()
    path = tmp_path / "token_budget_contract.json"
    path.write_bytes(contract.canonical_bytes())

    with pytest.raises(
        SystemExit,
        match="TOKEN_BUDGET_CONTRACT_NOT_FOUND",
    ):
        module._resolve_token_budget_contract_v1(
            files=(path,),
            expected_contract_sha256="f" * 64,
            override_env=None,
        )
