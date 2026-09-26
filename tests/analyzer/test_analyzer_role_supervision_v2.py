import pytest
from pchsi.analyzer.role_trace import build_cognitive_role_trace
from pchsi.analyzer.supervision_materializer import materialize_local_researcher_supervision

def _access(teacher=True):
 return {"task_id":"t","gamefile_sha256":"d"*64,"access_class":"DEV_VISIBLE",
         "dataset_split":"dev","teacher_call_permitted":teacher,
         "training_permitted":True,"select_evaluation_permitted":False,
         "confirmatory_permitted":False}

def _req():
 return {"task_id":"t","gamefile_sha256":"d"*64,
 "analysis_objective":"FAILURE_DIAGNOSIS","round_id":"r","policy_version":"p",
 "evidence_pack_sha256":"a"*64,"provider":"OpenAI","model":"m","model_version":"v",
 "prompt_sha256":"b"*64,"request_id":"req","raw_request_sha256":"c"*64,
 "raw_request_pointer":"req.json","raw_response_sha256":"e"*64,
 "raw_response_pointer":"resp.json","prompt_template_id":"tpl",
 "output_schema_id":"ANALYZER_LOCAL_RESULT_V2","output_schema_sha256":"f"*64,
 "reasoning_config_sha256":"1"*64,"parse_status":"ACCEPTED",
 "input_tokens":1,"output_tokens":2,"latency_ms":3.0,"cost_usd":0.01,
 "task_access_manifest_sha256":"2"*64}

def _adj():
 return {"adjudicated_output_sha256":"3"*64,"human_disposition":"ACCEPT",
         "crosscheck_sha256":None}

def test_access_and_researcher_dependency():
 with pytest.raises(ValueError,match="teacher_call_permitted"):
  build_cognitive_role_trace(_access(False),_req(),_adj(),role="ANALYZER",
                             environment_outcome_sha256=None)
 with pytest.raises(ValueError):
  materialize_local_researcher_supervision([],{},{},"x")
