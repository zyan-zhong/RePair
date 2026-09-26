import json

import pytest

from pchsi.cognitive_runtime.output_validation import validate_stage_output
from pchsi.cognitive_runtime.projections import (
    canonical_group_current_evidence_sha256s,
)


def _projection(memory=False):
    pack_sha="f"*64
    local_sha="b"*64
    projection={
        "group_id":"1"*64,
        "group_manifest_sha256":"a"*64,
        "a1_local_result_sha256s":[local_sha],
        "a1_local_results":[{
            "local_result_sha256":local_sha,
            "evidence_pack_sha256":pack_sha,
            "error_instances":[{
                "supporting_evidence_refs":[{
                    "artifact_sha256":pack_sha,
                    "evidence_kind":"TRAJECTORY_CALL",
                    "local_selector":"trajectory:0",
                    "authority":"DETERMINISTIC_FACT",
                }],
                "counterevidence_refs":[],
                "mechanism_hypotheses":[],
            }],
            "local_repairs":[],
        }],
        "group_synthesis_input":{
            "group_synthesis_input_sha256":"2"*64,
        },
        "source_contexts":[{
            "local_result_sha256":local_sha,
            "error_instance_id":"e1",
            "source_state_sha256":"c"*64,
            "menu_sha256":"d"*64,
            "admissible_commands":["open fridge 1"],
        }],
        "memory_pack_sha256":None,
    }
    projection["current_evidence_sha256s"]=canonical_group_current_evidence_sha256s(
        projection
    )
    if memory:
        projection["memory_pack_sha256"]="e"*64
        projection["memory_pack"]={"pack_sha256":"e"*64}
    return projection


def _output(evidence_sha, group_id="9"*64):
    return {
        "schema_id":"ANALYZER_GROUP_RESULT_V2",
        "schema_version":2,
        "group_id":group_id,
        "group_manifest_sha256":"a"*64,
        "mechanism_hypotheses":[{
            "hypothesis_id":"h1",
            "statement":"candidate mechanism",
            "evidence_sha256s":[evidence_sha],
            "uncertainty":"dev",
        }],
        "source_conditioned_proposals":[],
        "source_conditioned_repair_sha256s":[],
        "group_result_sha256":"0"*64,
    }


def test_canonical_universe_includes_a1_typed_evidence_pack_identity():
    projection=_projection()
    assert "f"*64 in projection["current_evidence_sha256s"]


def test_group_runtime_replaces_model_group_id_with_registered_identity():
    artifact=validate_stage_output(
        stage_id="G-A2",
        text=json.dumps(_output("f"*64)),
        raw_response_sha256="8"*64,
        projection=_projection(),
    )
    assert artifact["group_id"]=="1"*64


def test_group_runtime_accepts_visible_a1_typed_evidence_identity():
    artifact=validate_stage_output(
        stage_id="G-A2",
        text=json.dumps(_output("f"*64)),
        raw_response_sha256="8"*64,
        projection=_projection(),
    )
    assert artifact["mechanism_hypotheses"][0]["evidence_sha256s"]==["f"*64]


def test_group_runtime_rejects_unregistered_mechanism_evidence():
    with pytest.raises(ValueError,match="mechanism evidence outside"):
        validate_stage_output(
            stage_id="G-A2",
            text=json.dumps(_output("7"*64)),
            raw_response_sha256="8"*64,
            projection=_projection(),
        )


def test_group_runtime_allows_exact_memory_pack_identity_for_a3():
    artifact=validate_stage_output(
        stage_id="G-A3",
        text=json.dumps(_output("e"*64)),
        raw_response_sha256="8"*64,
        projection=_projection(memory=True),
    )
    assert artifact["group_id"]=="1"*64


def test_group_runtime_rejects_nonmemory_historical_like_sha():
    with pytest.raises(ValueError,match="mechanism evidence outside"):
        validate_stage_output(
            stage_id="G-A3",
            text=json.dumps(_output("6"*64)),
            raw_response_sha256="8"*64,
            projection=_projection(memory=True),
        )
