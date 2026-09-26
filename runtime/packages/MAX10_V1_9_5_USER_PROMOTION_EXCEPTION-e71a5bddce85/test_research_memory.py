import pytest
from research_memory import project,POST_FIELDS
def fixture():
    start={'round_id':'R2','request_sha256':'r2'}
    result={**start,'schema_id':'FORMAL_NATIVE_ROUND_RESULT_V1','outcome':'PROMOTED','benchmark_feedback_used':False}
    post={'schema_id':'API_RESEARCHER_POST_PRIMARY_V1','round_id':'R2',**{k:'preserved '+k for k in POST_FIELDS},'not_allowed_select_episode':'must not be projected'}
    memory={**start,'results':[{'status':'MATERIALIZED','native_disposition':{'disposition':'DESCRIPTIVE_ONLY'}}]}
    return dict(start=start,result=result,post=post,memory=memory)
def test_structured_lesson_is_exact_and_reference_only():
    args=fixture();value=project(**args)
    assert value['researcher_post']=={k:args['post'][k] for k in POST_FIELDS}
    assert value['analyzer_memory_dispositions']=={'DESCRIPTIVE_ONLY':1}
    assert value['research_reference_only'] and not value['policy_action_authorized'] and not value['training_supervision_authorized']
    assert 'not_allowed_select_episode' not in str(value)
@pytest.mark.parametrize('field,value',[('benchmark_feedback_used',True),('outcome','PROTOCOL_INFRA_INVALID'),('request_sha256','different')])
def test_invalid_or_wrong_round_not_memory(field,value):
    args=fixture();args['result'][field]=value
    with pytest.raises(ValueError):project(**args)

def test_blind_pre_hides_human_selection_and_audit_paths():
    from research_memory import researcher_view
    value={**project(**fixture()),'source_round_promotion_was_user_exception':True,'source_result_ref':{'path':'manual-user-exception'},'source_refs':{'path':'private'}}
    projected=researcher_view(value)
    assert projected['researcher_post']==value['researcher_post']
    assert not {'source_round_promotion_was_user_exception','source_result_ref','source_refs'}&set(projected)
