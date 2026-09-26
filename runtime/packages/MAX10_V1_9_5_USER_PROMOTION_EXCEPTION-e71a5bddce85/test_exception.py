import copy
import pytest
from promotion_exception import check_scope

def fixture():
    authorization={'schema_id':'USER_AUTHORIZED_CURRENT_CANDIDATE_PROMOTION_EXCEPTION_REQUEST_V1',
        'request_sha256':'request','candidate_policy_id':'candidate','original_automatic_terminal_ref':{'path':'original','sha256':'sha'},
        'human_scientific_decision_count':1,'automatic_promotion_claimed':False}
    terminal={'schema_id':'CURRENT_NATIVE_OFFOFF_TERMINAL_V1','request_sha256':'request','outcome':'ROLLED_BACK','human_scientific_decision_count':0,'benchmark_feedback_used':False}
    summary={'request_sha256':'request','candidate_policy_id':'candidate','memory_state':'OFF','harness_state':'OFF','evidence_access_class':'TRAIN_SELECT','benchmark_feedback_used':False}
    candidate={'request_sha256':'request','policy_id':'candidate','artifact_sha256':'new'}
    return authorization,terminal,summary,candidate,{'path':'original','sha256':'sha'}

def test_exact_user_exception():
    assert check_scope(*fixture()) is True

@pytest.mark.parametrize('which,key,value',[(0,'human_scientific_decision_count',0),(0,'automatic_promotion_claimed',True),
    (0,'candidate_policy_id','other'),(1,'request_sha256','other'),(1,'outcome','PROMOTED'),
    (2,'benchmark_feedback_used',True),(2,'memory_state','ON'),(3,'artifact_sha256',''),(3,'request_sha256','other')])
def test_scope_or_disclosure_cannot_drift(which,key,value):
    args=list(copy.deepcopy(fixture()));args[which][key]=value
    with pytest.raises(ValueError):check_scope(*args)

def test_wrong_original_terminal_rejected():
    args=list(fixture());args[-1]={'path':'elsewhere','sha256':'sha'}
    with pytest.raises(ValueError):check_scope(*args)

@pytest.mark.parametrize('terminal',[{'schema_id':'NO_TRAINING_UPDATE'},{'human_scientific_decision_count':0,'outcome':'ROLLED_BACK'},{'human_scientific_decision_count':0,'outcome':'PROMOTED'}])
def test_future_native_outcomes_keep_zero(terminal):
    from promotion_exception import scope_count
    assert scope_count({'request_sha256':'future'},terminal,{}, {'request_sha256':'current'},{'path':'exception'})==0

def test_exception_rejected_for_future_round():
    from promotion_exception import scope_count
    with pytest.raises(ValueError):scope_count({'request_sha256':'future'},{'human_scientific_decision_count':1},{}, {'request_sha256':'current'},{})

def test_campaign_final_summary_preserves_one_human_intervention():
    from promotion_exception import campaign_fields
    auth={'request_sha256':'current'};ref={'path':'auth'};terminal={'path':'manual'}
    result={'request_sha256':'current','terminal_ref':terminal,'promotion_exception_ref':ref,'human_scientific_decision_count':1,'automatic_promotion_claimed':False}
    fields=campaign_fields(result,ref,auth,terminal)
    assert fields['human_scientific_decision_count']==1 and fields['fully_unattended_scientific_selection_claimed'] is False
    assert campaign_fields(None,ref,auth,terminal)['human_scientific_decision_count']==0
    with pytest.raises(ValueError):campaign_fields({**result,'human_scientific_decision_count':0},ref,auth,terminal)
