from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads
from pchsi.memory.scientific_decision import STAGE_1B, STAGE_2, STAGE_3

SCRIPTS = Path(__file__).parents[2] / "scripts" / "memory"


def helper_module():
    path = Path(__file__).with_name("scientific_authority_test_helpers.py")
    spec = importlib.util.spec_from_file_location("_paper_authority_helper", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def test_paper_export_and_q4_q5_handoff(tmp_path: Path) -> None:
    helper = helper_module()
    authorities = {}
    meta = None
    for stage, name in ((STAGE_1B, "stage1b"), (STAGE_2, "stage2"), (STAGE_3, "stage3")):
        authority, current = helper.build_authority(tmp_path / name, stage=stage)
        authorities[name] = authority
        if meta is None:
            meta = current
        else:
            assert current == meta
    stage0 = tmp_path / "stage0.json"
    write_json(stage0, {
        "schema_id": "FAILURE_MEMORY_STAGE0_ROLE_RETRIEVAL_RESULT_V1",
        "schema_version": 1, "row_count": 90, "policy_exposure_count": 0,
        "analyzer_reference_positive_count": 5,
        "analyzer_recall_at_3": {"numerator": 5, "denominator": 5},
        "researcher_train_record_count": 3,
    })
    a0 = tmp_path / "a0.json"
    write_json(a0, {"schema_id":"FORMAL_A0_RESULT_AUTHORITY_V1","authority":"LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY","effect_counts":{"Benefit":0,"Harm":0,"Neutral":9}})
    b = tmp_path / "b.json"
    write_json(b, {"schema_id":"FORMAL_B_MINIMAL_Q3_RESULT_AUTHORITY_V1","authority":"FORMAL_B_Q3_RETRIEVAL_APPLICABILITY_SAFETY_ONLY","registered_safety_stress_metrics":{"row_count":30,"coverage":{"numerator":0,"denominator":30},"correct_exposure_count":0,"wrong_exposure_count":0,"unsafe_exposure_count":0,"abstention_count":30}})
    matrix = tmp_path / "matrix.json"
    statuses = {"Q1":"SUPPORTED","Q2":"NOT_SUPPORTED","Q3":"SUPPORTED","Q4":"OPEN","Q5":"DEFERRED_OPTIONAL_EXTENSION"}
    matrix_value = {"schema_id":"FAILURE_MEMORY_Q1_Q5_MATRIX_V1","schema_version":1,"rows":[{"question_id":q,"status":s,"authorized_summary":"bounded summary","evidence_sha256s":[],"forbidden_claims":[],"required_next_authorities":[]} for q,s in statuses.items()],"scientific_completion_rule":"TESTS_AND_INTERFACE_SMOKES_NEVER_REPLACE_REAL_OUTCOMES","matrix_sha256":"0"*64}
    matrix_payload = {
        "rows": matrix_value["rows"],
        "scientific_completion_rule": matrix_value[
            "scientific_completion_rule"
        ],
    }
    matrix_value["matrix_sha256"] = hashlib.sha256(
        b"FAILURE_MEMORY_Q1_Q5_MATRIX_V1\0"
        + canonical_json_bytes(matrix_payload)
    ).hexdigest()
    write_json(matrix, matrix_value)
    paper = tmp_path / "paper"
    subprocess.run([sys.executable, str(SCRIPTS/"export_memory_paper_evidence_v2.py"), "--stage0-result",str(stage0),"--a0-result",str(a0),"--b-result",str(b),"--stage1b-authority",str(authorities["stage1b"]),"--stage2-authority",str(authorities["stage2"]),"--stage3-authority",str(authorities["stage3"]),"--q1-q5-matrix",str(matrix),"--expected-fixed-head",meta["fixed_head"],"--expected-scientific-program-sha256",meta["program_sha"],"--output-dir",str(paper)],check=True)
    assert (paper/"paper_tables"/"memory_representation_ablation.csv").is_file()
    assert (paper/"PAPER_EVIDENCE_MANIFEST_V1.json").is_file()
    handoff = tmp_path / "handoff"
    subprocess.run([sys.executable,str(SCRIPTS/"build_memory_q4_q5_handoff_v1.py"),"--stage0-result",str(stage0),"--a0-result",str(a0),"--b-result",str(b),"--stage1b-authority",str(authorities["stage1b"]),"--stage2-authority",str(authorities["stage2"]),"--stage3-authority",str(authorities["stage3"]),"--q1-q5-matrix",str(matrix),"--paper-evidence-manifest",str(paper/"PAPER_EVIDENCE_MANIFEST_V1.json"),"--expected-fixed-head",meta["fixed_head"],"--expected-scientific-program-sha256",meta["program_sha"],"--output-dir",str(handoff)],check=True)
    closure = strict_json_loads((handoff/"FAILURE_MEMORY_MODULE_CLOSURE_V1.json").read_bytes())
    assert closure["failure_memory_implementation_closed"] is True
    assert closure["scope_boundary"]["hierarchical_analyzer_implemented"] is False
    assert closure["q1_q5_statuses"]["Q4"] == "OPEN"
    assert closure["q1_q5_statuses"]["Q5"] == "DEFERRED_OPTIONAL_EXTENSION"
