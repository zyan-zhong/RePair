from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from pchsi.evaluation.raw_policy_prompt import ExecutedTransition
from pchsi.memory.formal_b_retrieval import (
    FormalBGoldDispositionV1,
    FormalBGoldPanelV1,
    FormalBGoldTargetV1,
    FormalBIndependentGoldAuthorityV1,
    FormalBIndependentGoldRowV1,
    FormalBPoolV1,
    FormalBQueryV1,
)


RUNNER = Path("scripts/memory/run_formal_b_offline_v1.py")


def _load_runner():
    if not RUNNER.is_file():
        pytest.fail("FORMAL_B_B2_RED_MISSING_OFFLINE_RUNNER")
    spec = importlib.util.spec_from_file_location(
        "_formal_b_offline_runner",
        RUNNER,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _helpers():
    path = Path("tests/memory/package_b_direct_test_helpers.py")
    spec = importlib.util.spec_from_file_location("_formal_b_runner_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _query(pool, group, lineage, char):
    gold = (
        FormalBGoldTargetV1(
            FormalBGoldDispositionV1.ABSTAIN_NO_APPLICABLE_MEMORY,
            None,
        )
        if lineage is None
        else FormalBGoldTargetV1(
            FormalBGoldDispositionV1.EXPOSE_CORRECT_MEMORY,
            lineage,
        )
    )
    visible = (
        "irrelevant state"
        if lineage is None
        else "activation visible failure mechanism"
    )
    return FormalBQueryV1(
        pool=pool,
        task_gamefile_group_id=group,
        observation=visible,
        executed_transitions=(
            ExecutedTransition("look", visible),
        ),
        admissible_commands=("look",),
        interface_feedback=None,
        gold_target=gold,
        independent_gold_artifact_sha256=char * 64,
    )


def test_b2_runner_executes_three_stage_panel_and_writes_frozen_outputs(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    final, snapshot, contract, contract_path, _ = (
        _helpers().published_snapshot(tmp_path)
    )

    from pchsi.memory.dev_snapshot_loader import (
        load_calibrated_dev_snapshot_v2,
    )
    loaded = load_calibrated_dev_snapshot_v2(
        snapshot_directory=final,
        expected_snapshot_sha256=snapshot.snapshot_sha256,
        token_budget_contract_path=contract_path,
        expected_token_budget_contract_sha256=contract.contract_sha256,
    )
    lineage = loaded.members[0].record.memory_lineage_id

    queries = (
        _query(
            FormalBPoolV1.RETRIEVER_CALIBRATION_DEV,
            "cal-pos",
            lineage,
            "1",
        ),
        _query(
            FormalBPoolV1.RETRIEVER_CALIBRATION_DEV,
            "cal-neg",
            None,
            "2",
        ),
        _query(
            FormalBPoolV1.RETRIEVER_SELECTION_VALIDATION,
            "val-pos",
            lineage,
            "3",
        ),
        _query(
            FormalBPoolV1.RETRIEVER_SELECTION_VALIDATION,
            "val-neg",
            None,
            "4",
        ),
        _query(
            FormalBPoolV1.REGISTERED_SAFETY_STRESS,
            "stress-pos",
            lineage,
            "5",
        ),
        _query(
            FormalBPoolV1.REGISTERED_SAFETY_STRESS,
            "stress-neg",
            None,
            "6",
        ),
    )
    gold_authority = FormalBIndependentGoldAuthorityV1(
        rows=tuple(
            FormalBIndependentGoldRowV1(
                query_id=query.query_id,
                gold_target=query.gold_target,
                independent_gold_artifact_sha256=(
                    query.independent_gold_artifact_sha256
                ),
            )
            for query in queries
        )
    )
    panel = FormalBGoldPanelV1(
        active_snapshot_sha256=snapshot.snapshot_sha256,
        independent_gold_authority_sha256=(
            gold_authority.authority_sha256
        ),
        queries=queries,
    )
    panel_path = tmp_path / "panel.json"
    panel_path.write_bytes(panel.canonical_bytes())
    gold_path = tmp_path / "gold-authority.json"
    gold_path.write_bytes(gold_authority.canonical_bytes())
    output = tmp_path / "result"

    monkeypatch.setenv(
        "PACKAGE_B_SCIENTIFIC_EXECUTION_APPROVAL",
        runner.APPROVAL,
    )

    runner.run(
        SimpleNamespace(
            panel=str(panel_path),
            gold_authority=str(gold_path),
            snapshot_directory=str(final),
            snapshot_sha256=snapshot.snapshot_sha256,
            token_budget_contract=str(contract_path),
            token_budget_contract_sha256=contract.contract_sha256,
            output_root=str(output),
        )
    )

    expected = {
        "B_RETRIEVER_CALIBRATION_V1.json",
        "B_RETRIEVER_SELECTION_VALIDATION_V1.json",
        "B_SELECTED_RETRIEVER_CONFIG_V1.json",
        "B_REGISTERED_SAFETY_STRESS_V1.json",
        "B_RESULT_SUMMARY_V1.json",
        "SHA256SUMS.txt",
    }
    assert {path.name for path in output.iterdir()} == expected

    selected = json.loads(
        (output / "B_SELECTED_RETRIEVER_CONFIG_V1.json").read_text()
    )
    summary = json.loads(
        (output / "B_RESULT_SUMMARY_V1.json").read_text()
    )
    stress = json.loads(
        (output / "B_REGISTERED_SAFETY_STRESS_V1.json").read_text()
    )
    assert selected["config_sha256"] == summary["selected_config"]["config_sha256"]
    assert (
        stress["selected_config"]["config_sha256"]
        == selected["config_sha256"]
    )
    assert selected["safety_stress_may_modify_config"] is False
    assert summary["causal_benefit_harm_authority"] is False


def test_b2_runner_refuses_without_explicit_science_approval(tmp_path, monkeypatch):
    runner = _load_runner()
    monkeypatch.delenv(
        "PACKAGE_B_SCIENTIFIC_EXECUTION_APPROVAL",
        raising=False,
    )
    with pytest.raises(
        SystemExit,
        match="FORMAL_B_SCIENTIFIC_EXECUTION_APPROVAL_MISSING",
    ):
        runner.run(
            SimpleNamespace(
                panel=str(tmp_path / "missing"),
                gold_authority=str(tmp_path / "missing-gold"),
                snapshot_directory=str(tmp_path / "missing"),
                snapshot_sha256="a" * 64,
                token_budget_contract=str(tmp_path / "missing"),
                token_budget_contract_sha256="b" * 64,
                output_root=str(tmp_path / "out"),
            )
        )
