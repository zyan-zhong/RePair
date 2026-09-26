import pytest
from pchsi.analyzer.role_trace import build_cognitive_role_trace
from pchsi.analyzer.supervision_materializer import materialize_local_analyzer_supervision

def _access(training=True):
    return {
        "task_id":"t","gamefile_sha256":"d"*64,
        "access_class":"DEV_VISIBLE","dataset_split":"dev",
        "teacher_call_permitted":True,"training_permitted":training,
        "select_evaluation_permitted":False,"confirmatory_permitted":False,
    }

def _request():
    return {
        "task_id":"t","gamefile_sha256":"d"*64,
        "analysis_objective":"FAILURE_DIAGNOSIS","round_id":"r","policy_version":"p",
        "evidence_pack_sha256":"a"*64,"provider":"OpenAI","model":"m","model_version":"v",
        "prompt_sha256":"b"*64,"request_id":"req","raw_request_sha256":"c"*64,
        "raw_request_pointer":"raw/request.json","raw_response_sha256":"e"*64,
        "raw_response_pointer":"raw/response.json","prompt_template_id":"tpl",
        "output_schema_id":"ANALYZER_LOCAL_RESULT_V2","output_schema_sha256":"f"*64,
        "reasoning_config_sha256":"1"*64,"parse_status":"ACCEPTED",
        "input_tokens":10,"output_tokens":20,"latency_ms":100.0,"cost_usd":0.01,
        "task_access_manifest_sha256":"2"*64,
    }

def _adj():
    return {"adjudicated_output_sha256":"3"*64,
            "human_disposition":"ACCEPT","crosscheck_sha256":None}

def test_trace_rejects_task_access_mismatch_and_preserves_cost_lineage():
    bad=_request(); bad["task_id"]="other"
    with pytest.raises(ValueError,match="task_id"):
        build_cognitive_role_trace(_access(),bad,_adj(),role="ANALYZER",
                                   environment_outcome_sha256=None)
    trace=build_cognitive_role_trace(_access(),_request(),_adj(),role="ANALYZER",
                                     environment_outcome_sha256=None)
    assert trace["request_id"]=="req"
    assert trace["input_tokens"]==10 and trace["cost_usd"]==0.01

def test_nontraining_trace_is_preserved_but_marked_ineligible():
    trace=build_cognitive_role_trace(_access(False),_request(),_adj(),role="ANALYZER",
                                     environment_outcome_sha256=None)
    row=materialize_local_analyzer_supervision([trace])["rows"][0]
    assert row["training_eligible"] is False
    assert row["training_exclusion_reason"].startswith("ACCESS_CLASS:")
