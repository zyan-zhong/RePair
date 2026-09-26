import inspect
from pathlib import Path
import pytest
from transport_scope import executor_with_scope, remaining_attempts

def native(*, output_root, unit_identity, stage_id, condition_id, round_id, policy_version, projection, task_access, max_infrastructure_attempt_restarts=0):
    return max_infrastructure_attempt_restarts

def args(tmp_path, stage='G-A2'):
    return dict(output_root=tmp_path/'group'/'strong_group_runtime',unit_identity={},stage_id=stage,condition_id='A2',round_id='r',policy_version='p',projection={},task_access={})

def scope(tmp_path):
    return dict(output_root=str(tmp_path),round_id='r',parent_policy_id='p',max_infrastructure_attempt_restarts=2)

@pytest.mark.parametrize('stage',['G-A2','G-A3','C','X','R-PRE-PRIMARY-V2','R-POST-PRIMARY-V1'])
def test_omitted_budget_uses_frozen_authority(tmp_path,stage):
    wrapped=executor_with_scope(native,scope(tmp_path))
    assert wrapped(**args(tmp_path,stage))==2
    assert inspect.signature(wrapped)==inspect.signature(native)

def test_explicit_zero_preserved(tmp_path):
    assert executor_with_scope(native,scope(tmp_path))(**args(tmp_path),max_infrastructure_attempt_restarts=0)==0

@pytest.mark.parametrize('key,value',[('round_id','other'),('policy_version','other'),('output_root',Path('/unregistered'))])
def test_mismatched_scope_refused(tmp_path,key,value):
    kw=args(tmp_path);kw[key]=value
    with pytest.raises(ValueError):executor_with_scope(native,scope(tmp_path))(**kw)

def test_explicit_budget_cannot_expand(tmp_path):
    with pytest.raises(ValueError):executor_with_scope(native,scope(tmp_path))(**args(tmp_path),max_infrastructure_attempt_restarts=3)

def test_old_attempt_is_not_forgotten():
    assert remaining_attempts(2,1)==2
    with pytest.raises(ValueError):remaining_attempts(2,3)

def test_local_explicit_budget_passes(tmp_path):
    assert executor_with_scope(native,scope(tmp_path))(**args(tmp_path,'L-A0'),max_infrastructure_attempt_restarts=2)==2

def test_successor_pacing_uses_spent_ordinal(tmp_path):
    from types import SimpleNamespace
    from transport_scope import retry_pacing
    import json
    root=tmp_path/'calls';call=root/'c';call.mkdir(parents=True);delays=[];calls=[]
    orch=SimpleNamespace(execute_via_existing_p2=lambda *a,**k:calls.append(1))
    with retry_pacing(orch,SimpleNamespace(BACKOFF_SECONDS=(5,20)),offset_root=root,consumed=1,sleep=delays.append):
        orch.execute_via_existing_p2({},call,client_request_id='c')
        (call/'attempt_000.json').write_text(json.dumps({'logical_call_id':'c','transport_attempt_index':0,'retry_class':'SAFE_PRE_SEND'}))
        orch.execute_via_existing_p2({},call,client_request_id='c')
    assert delays==[5,20] and len(calls)==2

def test_pacing_rejects_ambiguous_retry(tmp_path):
    from types import SimpleNamespace
    from transport_scope import retry_pacing
    import json
    orch=SimpleNamespace(execute_via_existing_p2=lambda *a,**k:None)
    with retry_pacing(orch,SimpleNamespace(BACKOFF_SECONDS=(5,20)),sleep=lambda x:pytest.fail('waited')):
        orch.execute_via_existing_p2({},tmp_path,client_request_id='c')
        (tmp_path/'attempt_000.json').write_text(json.dumps({'logical_call_id':'c','transport_attempt_index':0,'retry_class':'NO_RETRY'}))
        with pytest.raises(ValueError,match='SAFE_RETRY'):orch.execute_via_existing_p2({},tmp_path,client_request_id='c')
