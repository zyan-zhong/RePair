import json
import pytest

from pchsi.cognitive_runtime.output_validation import validate_stage_output
from pchsi.reference_loop.canonical import domain_hash


def _current():
    value = {
        "schema_id":"ANALYZER_X_CURRENT_EVIDENCE_MANIFEST_V1",
        "schema_version":1,
        "group_manifest_sha256":"a"*64,
        "allowed_evidence_sha256s":["a"*64,"b"*64],
        "current_evidence_manifest_sha256":"0"*64,
    }
    value["current_evidence_manifest_sha256"]=domain_hash(
        "ANALYZER_X_CURRENT_EVIDENCE_MANIFEST_V1",
        value,
        excluded_field="current_evidence_manifest_sha256",
    )
    return value


def _historical(stage):
    memory = None if stage=="G-A2" else "c"*64
    value = {
        "schema_id":"ANALYZER_X_HISTORICAL_EVIDENCE_MANIFEST_V1",
        "schema_version":1,
        "target_stage_id":stage,
        "memory_pack_sha256":memory,
        "allowed_evidence_sha256s":[] if memory is None else [memory],
        "historical_evidence_manifest_sha256":"0"*64,
    }
    value["historical_evidence_manifest_sha256"]=domain_hash(
        "ANALYZER_X_HISTORICAL_EVIDENCE_MANIFEST_V1",
        value,
        excluded_field="historical_evidence_manifest_sha256",
    )
    return value


def _projection(stage):
    current=_current()
    historical=_historical(stage)
    p = {
        "target_stage_id":stage,
        "target_artifact_sha256":"d"*64,
        "target_artifact":{"group_manifest_sha256":"a"*64},
        "current_evidence_manifest_sha256":current[
            "current_evidence_manifest_sha256"
        ],
        "current_evidence_manifest":current,
        "historical_evidence_manifest_sha256":historical[
            "historical_evidence_manifest_sha256"
        ],
        "historical_evidence_manifest":historical,
        "memory_pack_sha256":historical["memory_pack_sha256"],
    }
    if stage=="G-A3":
        p["memory_pack"]={
            "schema_id":"FAILURE_MEMORY_ROLE_PACK_V1",
            "pack_sha256":"c"*64,
        }
    return p


def _output(stage):
    return {
        "schema_id":"ANALYZER_CROSSCHECK_RESULT_V1",
        "schema_version":1,
        "target_artifact_sha256":"d"*64,
        "disposition":"ACCEPT",
        "supporting_evidence_sha256s":["a"*64],
        "contradiction_evidence_sha256s":[],
        "residual_case_ids":[],
        "current_evidence_sha256s":["a"*64],
        "historical_evidence_sha256s":[] if stage=="G-A2" else ["c"*64],
        "crosscheck_sha256":"0"*64,
    }


def test_x_a2_accepts_registered_current_evidence_only():
    artifact=validate_stage_output(
        stage_id="X",
        text=json.dumps(_output("G-A2")),
        raw_response_sha256="e"*64,
        projection=_projection("G-A2"),
    )
    assert artifact["disposition"]=="ACCEPT"


def test_x_a3_accepts_exact_registered_memory_identity():
    artifact=validate_stage_output(
        stage_id="X",
        text=json.dumps(_output("G-A3")),
        raw_response_sha256="e"*64,
        projection=_projection("G-A3"),
    )
    assert artifact["historical_evidence_sha256s"]==["c"*64]


def test_x_rejects_unregistered_current_evidence():
    value=_output("G-A2")
    value["current_evidence_sha256s"]=["f"*64]
    with pytest.raises(ValueError,match="unregistered current"):
        validate_stage_output(
            stage_id="X",
            text=json.dumps(value),
            raw_response_sha256="e"*64,
            projection=_projection("G-A2"),
        )


def test_x_rejects_historical_evidence_on_a2():
    value=_output("G-A2")
    value["historical_evidence_sha256s"]=["c"*64]
    with pytest.raises(ValueError,match="unregistered historical"):
        validate_stage_output(
            stage_id="X",
            text=json.dumps(value),
            raw_response_sha256="e"*64,
            projection=_projection("G-A2"),
        )


def test_x_accept_requires_current_evidence():
    value=_output("G-A2")
    value["current_evidence_sha256s"]=[]
    with pytest.raises(ValueError,match="ACCEPT requires current"):
        validate_stage_output(
            stage_id="X",
            text=json.dumps(value),
            raw_response_sha256="e"*64,
            projection=_projection("G-A2"),
        )


def test_x_rejects_memory_mismatch_on_a3():
    projection=_projection("G-A3")
    projection["memory_pack_sha256"]="f"*64
    with pytest.raises(ValueError,match="historical Memory mismatch"):
        validate_stage_output(
            stage_id="X",
            text=json.dumps(_output("G-A3")),
            raw_response_sha256="e"*64,
            projection=projection,
        )
