from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pchsi.research_intelligence.clean_f0f1_manifest import (
    build_clean_f0f1_branch_bindings,
    build_planner_bound_clean_f0f1_execution_manifest,
    build_research_planner_f0f1_handoff_v2,
)
from pchsi.research_intelligence.research_planner_reference_trace import (
    build_research_planner_verification_plan_v2,
    current_reference_budget_plan_v1,
)
from pchsi.research_intelligence import human_f0f1_runtime as runtime


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _state(index: int) -> dict[str, object]:
    return {
        "source_state_sha256": _sha(f"state:{index}"),
        "research_candidate_id": _sha(f"research:{index}"),
        "source_candidate_sha256": _sha(f"candidate:{index}"),
        "candidate_artifact_path": f"/tmp/candidate-{index}.json",
        "candidate_artifact_file_sha256": _sha(f"candidate-file:{index}"),
        "replay_source_path": f"/tmp/replay-{index}.json",
        "replay_source_file_sha256": _sha(f"replay-file:{index}"),
        "registered_repair_action": f"go to cabinet {index + 1}",
    }


def _plan(states):
    return build_research_planner_verification_plan_v2(
        round_id="CLEAN-HUMAN-REFERENCE-R1-PI0",
        parent_policy_id="PI0_CLEAN",
        evidence_cutoff_sha256=_sha("evidence"),
        resource_budget_manifest_sha256=_sha("resource"),
        selected_source_state_ids=[row["source_state_sha256"] for row in states],
        selected_candidate_ids=[row["source_candidate_sha256"] for row in states],
        paired_seeds=[17, 31, 47, 73, 101],
        stable_direction_min_pairs=4,
    )


@pytest.mark.parametrize("n_states", [7, 13, 20])
def test_planner_plan_drives_manifest_population_without_fixed_12(n_states):
    states = [_state(i) for i in range(n_states)]
    plan = _plan(states)
    handoff = build_research_planner_f0f1_handoff_v2(
        verification_plan=plan,
        states=states,
    )
    manifest = build_planner_bound_clean_f0f1_execution_manifest(
        verification_plan=plan,
        handoff=handoff,
        round_id="CLEAN-HUMAN-REFERENCE-R1-PI0",
        implementation_commit="d" * 40,
        field_adjudication_file_sha256=_sha("field"),
        runtime_binding_path="/tmp/runtime.json",
        runtime_binding_file_sha256=_sha("runtime"),
        active_snapshot_sha256=_sha("snapshot"),
        token_budget_contract_sha256=_sha("token-budget"),
        policy_model="Qwen2.5-3B-Instruct-PI0-CLEAN",
        policy_version="PI0_CLEAN",
        states=states,
    )
    assert manifest["state_count"] == n_states
    assert manifest["pair_count"] == n_states * 5
    assert manifest["branch_count"] == n_states * 5 * 2
    assert manifest["state_budget_authority"] == (
        "RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE"
    )
    assert manifest["legacy_fixed_12_state_authority_used"] is False
    bindings = build_clean_f0f1_branch_bindings(manifest)
    assert len(bindings) == n_states * 10
    assert runtime.validate_branch_binding_v1(bindings[0]) == bindings[0]


def test_manifest_rejects_state_set_not_selected_by_planner():
    states = [_state(i) for i in range(13)]
    plan = _plan(states)
    altered = list(states)
    altered[-1] = _state(99)
    handoff = build_research_planner_f0f1_handoff_v2(
        verification_plan=plan,
        states=states,
    )
    with pytest.raises(ValueError, match="execution states differ"):
        build_planner_bound_clean_f0f1_execution_manifest(
            verification_plan=plan,
            handoff=handoff,
            round_id="CLEAN-HUMAN-REFERENCE-R1-PI0",
            implementation_commit="d" * 40,
            field_adjudication_file_sha256=_sha("field"),
            runtime_binding_path="/tmp/runtime.json",
            runtime_binding_file_sha256=_sha("runtime"),
            active_snapshot_sha256=_sha("snapshot"),
            token_budget_contract_sha256=_sha("token-budget"),
            policy_model="Qwen2.5-3B-Instruct-PI0-CLEAN",
            policy_version="PI0_CLEAN",
            states=altered,
        )


def test_historical_reference_budget_helper_remains_reproducible():
    legacy = current_reference_budget_plan_v1()
    assert legacy.registered_state_budget == 12
    assert legacy.total_branch_run_budget == 120
