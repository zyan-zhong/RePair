from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.clean_f0f1_manifest import (
    FROZEN_PAIRED_SEEDS,
    build_clean_f0f1_branch_bindings,
    build_clean_f0f1_execution_manifest,
)
import pytest
import pchsi.research_intelligence.human_f0f1_runtime as runtime


def _state(position: int = 0) -> dict[str, object]:
    return {
        "source_state_sha256": f"{position + 1:064x}",
        "research_candidate_id": f"{position + 101:064x}",
        "source_candidate_sha256": f"{position + 201:064x}",
        "candidate_artifact_path": f"/tmp/candidate-{position}.json",
        "candidate_artifact_file_sha256": "a" * 64,
        "replay_source_path": f"/tmp/replay-{position}.json",
        "replay_source_file_sha256": "b" * 64,
        "registered_repair_action": "open fridge 1",
    }


def test_clean_f0f1_manifest_population_is_state_count_times_five_times_two() -> None:
    manifest = build_clean_f0f1_execution_manifest(
        round_id="CLEAN-HUMAN-REFERENCE-R1-PI0",
        implementation_commit="d" * 40,
        handoff_sha256="1" * 64,
        field_adjudication_file_sha256="2" * 64,
        runtime_binding_path="/tmp/runtime.json",
        runtime_binding_file_sha256="3" * 64,
        active_snapshot_sha256="4" * 64,
        token_budget_contract_sha256="5" * 64,
        policy_model="Qwen2.5-3B-Instruct-PI0-CLEAN",
        policy_version="PI0_CLEAN",
        states=(_state(0), _state(1), _state(2)),
    )
    assert manifest["seed_schedule"] == list(FROZEN_PAIRED_SEEDS)
    assert manifest["state_count"] == 3
    assert manifest["pair_count"] == 15
    assert manifest["branch_count"] == 30
    bindings = build_clean_f0f1_branch_bindings(manifest)
    assert len(bindings) == 30
    assert {row["branch"] for row in bindings} == {"F0", "F1"}


def test_clean_branch_binding_accepts_round_adaptive_registered_universe() -> None:
    manifest = build_clean_f0f1_execution_manifest(
        round_id="CLEAN-HUMAN-REFERENCE-R1-PI0",
        implementation_commit="d" * 40,
        handoff_sha256="1" * 64,
        field_adjudication_file_sha256="2" * 64,
        runtime_binding_path="/tmp/runtime.json",
        runtime_binding_file_sha256="3" * 64,
        active_snapshot_sha256="4" * 64,
        token_budget_contract_sha256="5" * 64,
        policy_model="Qwen2.5-3B-Instruct-PI0-CLEAN",
        policy_version="PI0_CLEAN",
        states=tuple(_state(i) for i in range(13)),
    )
    binding = build_clean_f0f1_branch_bindings(manifest)[12 * 10]
    checked = runtime.validate_branch_binding_v1(binding)
    assert checked["state_position"] == 12
    assert checked["policy_model"] == "Qwen2.5-3B-Instruct-PI0-CLEAN"
    assert checked["policy_version"] == "PI0_CLEAN"
    assert manifest["state_budget_mode"] == "FROZEN_REGISTERED_UNIVERSE"
    assert manifest["max_selected_states"] == 13
    assert manifest["state_count"] == 13
    assert manifest["pair_count"] == 65
    assert manifest["branch_count"] == 130
    assert manifest["stable_direction_min_pairs"] == 4
    assert manifest["outcome_adaptive_reselection_allowed"] is False


def test_clean_f0f1_state_budget_has_no_fixed_12_state_cap() -> None:
    manifest = build_clean_f0f1_execution_manifest(
        round_id="CLEAN-HUMAN-REFERENCE-R1-PI0",
        implementation_commit="d" * 40,
        handoff_sha256="1" * 64,
        field_adjudication_file_sha256="2" * 64,
        runtime_binding_path="/tmp/runtime.json",
        runtime_binding_file_sha256="3" * 64,
        active_snapshot_sha256="4" * 64,
        token_budget_contract_sha256="5" * 64,
        policy_model="Qwen2.5-3B-Instruct-PI0-CLEAN",
        policy_version="PI0_CLEAN",
        states=tuple(_state(i) for i in range(17)),
    )
    assert manifest["state_budget_mode"] == "FROZEN_REGISTERED_UNIVERSE"
    assert manifest["max_selected_states"] == 17
    assert manifest["state_count"] == 17
    assert manifest["pair_count"] == 85
    assert manifest["branch_count"] == 170

def test_clean_f0f1_runtime_has_no_historical_pi1_identity_hardcode() -> None:
    repo = Path(__file__).resolve().parents[2]
    runtime_text = (repo / "src/pchsi/research_intelligence/human_f0f1_runtime.py").read_text()
    runner_text = (repo / "scripts/research_intelligence/run_human_reference_f0f1_branch_v2.py").read_text()
    aggregator_text = (repo / "scripts/research_intelligence/aggregate_human_reference_f0f1_v2.py").read_text()
    forbidden = ("P4-R1-Q2-BAD-TRAIN17", "PI1_BAD", "state_count\")!=12", "pair_count\")!=60")
    for token in forbidden:
        assert token not in runtime_text
        assert token not in runner_text
        assert token not in aggregator_text
    assert "228f3274693a22667ef2123254625b95b9bbd50d" in runtime_text


def test_clean_f0f1_budget_config_matches_runtime_constants() -> None:
    import json
    repo = Path(__file__).resolve().parents[2]
    value = json.loads(
        (repo / "configs/research_intelligence/clean_reference_f0f1_budget_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert value["schema_id"] == "CLEAN_REFERENCE_F0F1_BUDGET_V1"
    assert value["max_selected_states"] is None
    assert value["max_branch_runs"] is None
    assert value["state_budget_mode"] == "FROZEN_REGISTERED_UNIVERSE"
    assert value["branch_budget_mode"] == (
        "DERIVE_STATE_COUNT_X_PAIRED_REPETITIONS_X_ARMS"
    )
    assert value["paired_seeds"] == list(FROZEN_PAIRED_SEEDS)
    assert value["stable_direction_min_pairs"] == 4
    assert value["outcome_adaptive_reselection_allowed"] is False
    assert value["effect_authority"] == "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY"
    assert value["historical_task_specific_portfolio_reuse"] is False
