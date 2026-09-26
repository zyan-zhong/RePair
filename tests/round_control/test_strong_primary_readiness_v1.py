from __future__ import annotations

from pathlib import Path

from pchsi.round_control.strong_primary_readiness import (
    inspect_strong_primary_binding_readiness,
)


def test_current_repo_has_analyzer_and_role_neutral_contract_but_not_fake_primary():
    repo=Path(__file__).resolve().parents[2]
    result=inspect_strong_primary_binding_readiness(repo_root=repo)
    assert result.analyzer_primary_runtime_ready is True
    assert result.role_neutral_primary_contract_ready is True
    assert result.planner_pre_primary_transport_ready is True
    assert result.planner_post_primary_transport_ready is True
    assert result.local_shadow_checkpoint_ready is False
    assert result.human_gate_dependency_absent_for_primary is True
    assert result.execution_authorized is False
    assert result.ready_for_strong_primary_local_shadow is False
