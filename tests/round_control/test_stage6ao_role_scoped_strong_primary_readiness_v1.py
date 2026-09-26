from pathlib import Path
import json

from pchsi.round_control.role_authority import (
    AuthorityPhaseV1,
    ResearchRoleV1,
    resolve_authority_plan,
)
from pchsi.round_control.strong_primary_readiness import (
    _stage6ak_local_analyzer_ready,
    inspect_strong_primary_binding_readiness,
)


def test_stage6ak_checkpoint_is_role_scoped_local_analyzer(tmp_path):
    ckpt = tmp_path / "ckpt.json"
    result = tmp_path / "result.json"
    ckpt.write_text(json.dumps({
        "schema_id":"LOCAL_ANALYZER_BOOTSTRAP_CHECKPOINT_AUTHORITY_V1",
        "schema_version":1,
        "role":"LOCAL_ANALYZER",
        "status":"BOOTSTRAP_CHECKPOINT_FROZEN",
        "checkpoint_role":"BOOTSTRAP_WARM_START_NOT_TAKEOVER",
        "shadow_qualification_required":True,
        "takeover_authorized":False,
        "strong_primary_launch_blocking":False,
        "adapter_dir":"/tmp/a",
        "adapter_artifact_manifest_sha256":"a"*64
    }), encoding="utf-8")
    result.write_text(json.dumps({
        "schema_id":"STAGE6AK_LOCAL_ANALYZER_FULL_BOOTSTRAP_RESULT_AUTHORITY_V1",
        "schema_version":1,
        "status":"PASS",
        "bootstrap_checkpoint_frozen":True,
        "local_analyzer_shadow_readiness_gate_authorized":True,
        "local_analyzer_takeover_authorized":False,
        "strong_primary_launch_blocking":False
    }), encoding="utf-8")
    assert _stage6ak_local_analyzer_ready(
        checkpoint_manifest=ckpt,
        result_authority=result,
    )


def test_strong_primary_shadows_only_analyzer(monkeypatch):
    import pchsi.round_control.role_authority as module
    monkeypatch.setattr(
        module,
        "validate_takeover_evaluation",
        lambda value: value,
    )
    evaluation = {
        "strong_research_planner_primary_eligible": True,
        "local_training_and_shadow_eligible": True,
    }
    plan = resolve_authority_plan(
        phase=AuthorityPhaseV1.STRONG_PRIMARY_LOCAL_SHADOW,
        takeover_evaluation=evaluation,
    )
    assert plan.primary_actor(ResearchRoleV1.ANALYZER) == "STRONG"
    assert plan.primary_actor(ResearchRoleV1.RESEARCH_PLANNER_PRE) == "STRONG"
    assert plan.primary_actor(ResearchRoleV1.RESEARCH_PLANNER_POST) == "STRONG"
    assert plan.shadow_actors(ResearchRoleV1.ANALYZER) == ("LOCAL",)
    assert plan.shadow_actors(ResearchRoleV1.RESEARCH_PLANNER_PRE) == ()
    assert plan.shadow_actors(ResearchRoleV1.RESEARCH_PLANNER_POST) == ()


def test_actual_stage6ak_authority_closes_role_scoped_readiness():
    repo = Path(__file__).resolve().parents[2]
    ckpt = (
        repo
        / "docs/project/strong_primary_takeover_v1/stage6ak/"
        "LOCAL_ANALYZER_BOOTSTRAP_CHECKPOINT_AUTHORITY_V1.json"
    )
    result = (
        repo
        / "docs/project/strong_primary_takeover_v1/stage6ak/"
        "STAGE6AK_RESULT_AUTHORITY_V1.json"
    )
    state = inspect_strong_primary_binding_readiness(
        repo_root=repo,
        local_checkpoint_manifest=ckpt,
        local_result_authority=result,
        execution_authorized=True,
    )
    assert state.analyzer_primary_runtime_ready is True
    assert state.planner_pre_primary_transport_ready is True
    assert state.planner_post_primary_transport_ready is True
    assert state.role_neutral_primary_contract_ready is True
    assert state.local_shadow_checkpoint_ready is True
    assert state.human_gate_dependency_absent_for_primary is True
    assert state.ready_for_strong_primary_local_shadow is True
