from pathlib import Path
import pytest
from group_recovery import durable_successor,pin_successor

def test_successor_is_one_exclusive_invocation_and_adopts(tmp_path):
    calls=[]
    def execute():
        calls.append(1);p=tmp_path/'calls'/'c';p.mkdir(parents=True);(p/'logical_call.json').write_text('{}');return {'status':'ACCEPTED'}
    assert durable_successor(tmp_path,'c',{'limit':2},execute,lambda p:{'status':'REUSED'})['status']=='ACCEPTED'
    assert durable_successor(tmp_path,'c',{'limit':2},execute,lambda p:{'status':'REUSED'})['status']=='REUSED'
    assert len(calls)==1

def test_partial_successor_never_resends(tmp_path):
    def execute():raise RuntimeError('crash after claim')
    with pytest.raises(RuntimeError):durable_successor(tmp_path,'c',{'limit':2},execute,lambda p:None)
    with pytest.raises(ValueError,match='PARTIAL'):durable_successor(tmp_path,'c',{'limit':2},lambda:pytest.fail('resent'),lambda p:None)

def test_changed_budget_cannot_restart(tmp_path):
    def execute():raise RuntimeError('crash')
    with pytest.raises(RuntimeError):durable_successor(tmp_path,'c',{'limit':2},execute,lambda p:None)
    with pytest.raises(ValueError,match='CHANGED'):durable_successor(tmp_path,'c',{'limit':3},lambda:pytest.fail('resent'),lambda p:None)

def test_new_authority_cannot_allocate_second_successor(tmp_path):
    pin_successor(tmp_path,{'new':'first','limit':2})
    pin_successor(tmp_path,{'new':'first','limit':2})
    with pytest.raises(ValueError,match='DIFFERENT_SUCCESSOR'):pin_successor(tmp_path,{'new':'second','limit':2})
