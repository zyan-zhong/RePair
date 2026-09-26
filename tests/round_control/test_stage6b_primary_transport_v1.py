
from pathlib import Path
import json
from pchsi.cognitive_runtime.manifest import load_runtime_manifest
from pchsi.round_control.clean_role_actor_binding import strong_primary_local_shadow_bindings
from pchsi.round_control.strong_primary_readiness import inspect_strong_primary_binding_readiness

def test_stage6b_primary_runtime_contract():
    rows={r["stage_id"]:r for r in load_runtime_manifest()["stage_rows"]}
    pre=rows["R-PRE-PRIMARY-V1"]; post=rows["R-POST-PRIMARY-V1"]
    assert pre["required_projection_identity_fields"]==["blind_input_sha256","evidence_hydration_manifest_sha256","blind_input"]
    assert "human_pre_gate_satisfied" not in pre["required_projection_identity_fields"]
    assert "human_pre_record_sha256" not in post["required_projection_identity_fields"]
    assert "primary_pre_record_sha256" in post["required_projection_identity_fields"]

def test_stage6b_primary_schema_prompt_contract():
    repo=Path(__file__).resolve().parents[2]
    pre_prompt=(repo/"prompts/cognitive_runtime/RESEARCHER_PRE_PRIMARY_V1.txt").read_text()
    post_prompt=(repo/"prompts/cognitive_runtime/RESEARCHER_POST_PRIMARY_V1.txt").read_text()
    assert "frozen Human Reference Round" not in pre_prompt
    assert "Human PRE identity" not in post_prompt
    assert "primary_record_sha256" in pre_prompt
    pre=json.loads((repo/"configs/cognitive_runtime/schemas/strong_researcher_pre_primary_v1.json").read_text())
    post=json.loads((repo/"configs/cognitive_runtime/schemas/api_researcher_post_primary_v1.json").read_text())
    assert pre["$id"]=="STRONG_RESEARCHER_PRE_PRIMARY_V1" and "shadow_record_sha256" not in pre["properties"]
    assert "primary_record_sha256" in pre["properties"]
    assert post["$id"]=="API_RESEARCHER_POST_PRIMARY_V1" and "human_pre_record_sha256" not in post["properties"]
    assert "primary_pre_record_sha256" in post["properties"]

def test_stage6b_readiness_detects_transport_but_never_execution():
    repo=Path(__file__).resolve().parents[2]
    stage_ids={b.stage_id for b in strong_primary_local_shadow_bindings(repo)}
    assert {"L-A0","L-A1","G-A2","G-A3","C","X","R-PRE-PRIMARY-V1","R-POST-PRIMARY-V1"}<=stage_ids
    status=inspect_strong_primary_binding_readiness(repo_root=repo)
    assert status.analyzer_primary_runtime_ready
    assert status.planner_pre_primary_transport_ready
    assert status.planner_post_primary_transport_ready
    assert not status.execution_authorized
    assert not status.local_shadow_checkpoint_ready
    assert not status.ready_for_strong_primary_local_shadow
