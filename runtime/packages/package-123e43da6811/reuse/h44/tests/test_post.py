import os,shutil,json
from pathlib import Path
from types import SimpleNamespace
from io_utils import canonical,sha,put_json,read_json
from strong_post import execute_post


def setup_post(tmp_path):
    source=Path(os.environ['PCHSI_TEST_EVIDENCE_ROOT'])
    shutil.copytree(source/'pre_root',tmp_path/'input/pre_root')
    shutil.copytree(source/'native_execution_gate',tmp_path/'input/native_execution_gate')
    request=read_json(source/'current_rollout/ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json')
    handoff=read_json(source/'pre_root/V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json')
    plan={'round_id':request['round_id'],'source_request':request,'handoff':handoff,
      'states':handoff['selected_states'],'scope_notice':read_json(source/'native_execution_gate/HYPOTHESIS_SCOPE_NOTICE_V1.json')}
    plan['plan_sha256']=sha(canonical(plan));put_json(tmp_path/'EXECUTION_PLAN.json',plan)
    verifier={'schema_id':'CURRENT_ROUND_INDEPENDENT_F0F1_VERIFIER_V1','plan_sha256':plan['plan_sha256'],
      'scientifically_complete_pair_count':1,'selected_state_count':len(plan['states']),
      'stable_effect_counts':{'BENEFIT':0,'HARM':0,'NEUTRAL':len(plan['states']),'UNCERTAIN':0},
      'state_results':[],'pair_results':[],'branch_records':[]}
    verifier['environment_result_package_sha256']=sha(canonical(verifier))
    put_json(tmp_path/'verifier/ENVIRONMENT_RESULT_PACKAGE.json',verifier)
    return plan,verifier


def test_actual_post_orchestrator_schema_validator_and_native_no_train(tmp_path,monkeypatch):
    import pchsi.cognitive_runtime.orchestrator as o
    plan,verifier=setup_post(tmp_path);calls=[]
    def fake_p2(bundle,call_dir,*,client_request_id):
        calls.append(client_request_id);projection=bundle['input_projection']
        payload={'schema_id':'API_RESEARCHER_POST_PRIMARY_V1','schema_version':1,'round_id':plan['round_id'],
          'primary_pre_record_sha256':projection['primary_pre_record_sha256'],
          'environment_result_package_sha256':projection['environment_result_package_sha256'],
          'protocol_audit':'valid test fixture','observed_outcome':'neutral','numerator':0,'denominator':len(plan['states']),
          'unexpected_evidence':[],'hypothesis_status':'UNRESOLVED','alternative_explanations':['A2 was not run'],
          'researcher_training_recommendation':'NO_TRAIN','researcher_promotion_recommendation':'HOLD',
          'lesson':'no positive verified data','next_round_implication':'retain parent','primary_record_sha256':'0'*64}
        response={'id':'response-fixture','model':bundle['provider_request']['model'],'status':'completed',
          'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(payload)}]}],
          'usage':{'input_tokens':10,'output_tokens':10,'output_tokens_details':{'reasoning_tokens':0}}}
        return SimpleNamespace(http_status=200,response_headers={},provider_http_request_id='fixture',raw_response=canonical(response))
    monkeypatch.setattr(o,'execute_via_existing_p2',fake_p2)
    result=execute_post(tmp_path,plan,verifier)
    assert result['training_recommendation']=='NO_TRAIN' and len(calls)==1
    no=read_json(tmp_path/'post/NO_TRAINING_UPDATE_V1.json')
    assert no['candidate_policy_created'] is False
    assert no['training_execution_count']==0
    assert no['parent_policy_retained'] is True
    assert no['scientific_attempt_consumed'] is True
    again=execute_post(tmp_path,plan,verifier)
    assert again['provider_calls']==0 and len(calls)==1
    assert result['round_closed'] is False and result['full_max10_released'] is False


def test_all_invalid_never_becomes_scientific_no_train(tmp_path):
    plan,verifier=setup_post(tmp_path)
    verifier['scientifically_complete_pair_count']=0;verifier.pop('environment_result_package_sha256')
    verifier['environment_result_package_sha256']=sha(canonical(verifier))
    result=execute_post(tmp_path,plan,verifier)
    assert result['status']=='PROTOCOL_OR_INFRA_INVALID_NO_SCIENTIFIC_NO_TRAIN'
    assert not (tmp_path/'post/NO_TRAINING_UPDATE_V1.json').exists()


def test_train_post_materializes_exact_pending_training_handoff_without_optimizer(tmp_path,monkeypatch):
    import pchsi.cognitive_runtime.orchestrator as o
    plan,verifier=setup_post(tmp_path)
    verifier['stable_effect_counts']={'BENEFIT':1,'HARM':0,'NEUTRAL':len(plan['states'])-1,'UNCERTAIN':0}
    verifier['state_results']=[
        {
            'source_state_sha256': plan['states'][0]['source_state_sha256'],
            'source_candidate_sha256': plan['states'][0].get('source_candidate_sha256','b'*64),
            'stable_effect':'BENEFIT','four_of_five_stable':True,
        }
    ]
    verifier.pop('environment_result_package_sha256')
    verifier['environment_result_package_sha256']=sha(canonical(verifier))
    calls=[]
    def fake_p2(bundle,call_dir,*,client_request_id):
        calls.append(client_request_id);projection=bundle['input_projection']
        payload={'schema_id':'API_RESEARCHER_POST_PRIMARY_V1','schema_version':1,'round_id':plan['round_id'],
          'primary_pre_record_sha256':projection['primary_pre_record_sha256'],
          'environment_result_package_sha256':projection['environment_result_package_sha256'],
          'protocol_audit':'valid test fixture','observed_outcome':'benefit','numerator':1,'denominator':len(plan['states']),
          'unexpected_evidence':[],'hypothesis_status':'UNRESOLVED','alternative_explanations':['A2 was not run'],
          'researcher_training_recommendation':'TRAIN','researcher_promotion_recommendation':'HOLD',
          'lesson':'verified benefit exists','next_round_implication':'materialize verified training evidence',
          'primary_record_sha256':'0'*64}
        response={'id':'response-fixture-train','model':bundle['provider_request']['model'],'status':'completed',
          'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(payload)}]}],
          'usage':{'input_tokens':10,'output_tokens':10,'output_tokens_details':{'reasoning_tokens':0}}}
        return SimpleNamespace(http_status=200,response_headers={},provider_http_request_id='fixture',raw_response=canonical(response))
    monkeypatch.setattr(o,'execute_via_existing_p2',fake_p2)
    result=execute_post(tmp_path,plan,verifier)
    assert result['training_recommendation']=='TRAIN' and len(calls)==1
    handoff=read_json(tmp_path/'post/CURRENT_VERIFIED_TRAINING_HANDOFF_V1.json')
    assert handoff['post_primary_record_sha256']==result['post_sha256']
    assert handoff['environment_result_package_sha256']==verifier['environment_result_package_sha256']
    assert handoff['verified_benefit_state_count']==1
    assert handoff['training_execution_authorized'] is False
    assert handoff['training_execution_count']==0
    assert handoff['human_scientific_decision_required'] is False
    assert result['training_handoff_sha256']==handoff['handoff_sha256']
