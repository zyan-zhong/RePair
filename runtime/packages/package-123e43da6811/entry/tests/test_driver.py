"""CPU orchestration tests; native science is exercised in the subprocess case."""
from pathlib import Path
from types import SimpleNamespace,ModuleType
import copy
import json
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[4]
V17=ROOT/'work/v17'
sys.path[:0]=[str(V17),str(V17/'live_adapter'),str(V17/'native_bba_full/src')]
from entry import driver


def put(path,value):
    driver.immutable_json(path,value)
    return driver._native_ref(driver.file_ref(path))


def wiring(tmp_path,monkeypatch,recommendation,outcome):
    start={'round_id':'current','request_sha256':'a'*64,'parent_policy_id':'parent'}
    prior={'native_parent_context':'retained'}
    current={'request':{'path':'fixture-request','sha256':'b'*64},
        'execution_binding':{'path':'fixture-binding','sha256':'c'*64},
        'input_refs':{'path':'fixture-inputs','sha256':'d'*64},'current_index':None,
        'memory_state':{'path':'fixture-memory-state','sha256':'e'*64},
        'current_parent_context':prior,'round_index':4}
    obj=driver.ExistingComponentRoundDriver(bundle_root=tmp_path/'bundle',formal_root=tmp_path/'formal',
        owner_root=tmp_path/'owner',deployment={'entry_source_sha256':'f'*64,'scientific_repo_root':str(V17/'native_bba_full'),
            'rollout_settings':{'registered':'settings'},'training_source_registration':{'registered':'training'}},initial=start)
    put(obj.formal_root/'CAMPAIGN_STARTUP_AUTHORITY_V1.json',{'fixture':'authority'})
    monkeypatch.setattr(obj,'_binding',lambda value:copy.deepcopy(current))
    calls=[]
    def capture(label,result):
        def method(*args,**kwargs): calls.append((label,args,kwargs));return copy.deepcopy(result)
        return method
    monkeypatch.setattr(driver,'build_registered_spec',capture('spec',{'registered':'spec'}))
    manifest_ref=put(tmp_path/'fixture-materialized.json',{'fixture':'materialized'})
    monkeypatch.setattr(driver,'materialize',capture('materialize',{'manifest_path':manifest_ref['path']}))
    monkeypatch.setattr(driver,'await_rollout',capture('rollout',{'status':'VALID_CURRENT_ROUND_HANDOFF'}))
    input_ref=put(tmp_path/'inputs.json',{'fixture':'inputs'})
    monkeypatch.setattr(driver,'current_rollout_inputs',capture('inputs',input_ref))
    monkeypatch.setattr(driver,'build_source_binding',capture('source',{'source_registration':{'registered':'code'}}))
    monkeypatch.setattr(driver,'build_from_rollout_result',capture('binding',{'fixture':'binding'}))
    analyzer=ModuleType('adapter');analyzer.run_bound_round=capture('analyzer',{})
    monkeypatch.setitem(sys.modules,'adapter',analyzer)
    evidence={'post_artifact':put(tmp_path/'post.json',{'researcher_training_recommendation':recommendation})}
    monkeypatch.setattr(driver,'current_h44_evidence',capture('evidence',evidence))
    from continuity_binding import api
    monkeypatch.setattr(api,'validate_current_post',capture('post_validation',({'researcher_training_recommendation':recommendation},None)))
    trained={'schema_id':'ROUTING_ONLY_TRAINING_FIXTURE','actual_ref':'training'}
    training=ModuleType('entry.training_job');training.execute_current_training_job=capture('training',trained)
    monkeypatch.setitem(sys.modules,'entry.training_job',training)
    terminal_ref=put(tmp_path/'offoff.json',{'outcome':outcome})
    next_refs={'runtime':'real-runtime-ref','profile':'real-profile-ref','policy_launch_authority':'real-launch-ref','engine_profile':'real-engine-ref'}
    evaluated={'terminal_ref':terminal_ref,'next_policy_input_refs':next_refs,'current_parent_context':{'accepted':'new-parent-context'}}
    offoff=ModuleType('entry.offoff_job');offoff.execute_current_offoff_job=capture('offoff',evaluated)
    monkeypatch.setitem(sys.modules,'entry.offoff_job',offoff)
    from entry import tail
    monkeypatch.setattr(tail,'close_round_tail',capture('close',{'outcome':outcome}))
    monkeypatch.setattr(obj,'validate_result',capture('validate',True))
    return obj,start,current,calls,trained,evaluated,offoff


@pytest.mark.parametrize('recommendation,outcome',[('NO_TRAIN','NO_TRAINING_UPDATE'),('TRAIN','PROMOTED'),('TRAIN','ROLLED_BACK')])
def test_route_retains_actual_decisions_and_closed_recovery_does_not_resend(tmp_path,monkeypatch,recommendation,outcome):
    obj,start,current,calls,trained,evaluated,_=wiring(tmp_path,monkeypatch,recommendation,outcome)
    attempt=tmp_path/'attempt'
    result=obj.execute_round(start,attempt)
    labels=[row[0] for row in calls]
    assert labels.index('post_validation')<labels.index('close')
    close=next(row[2] for row in calls if row[0]=='close')
    if recommendation=='TRAIN':
        assert labels.index('post_validation')<labels.index('training')<labels.index('offoff')<labels.index('close')
        train=next(row[2] for row in calls if row[0]=='training')
        assert train['current_parent_context']==current['current_parent_context'] and train['round_index']==4
        assert close['training_result_ref']==evaluated['terminal_ref']
    else:
        assert 'training' not in labels and 'offoff' not in labels
        assert close['training_result_ref'] is None
    if outcome=='PROMOTED':
        assert close['next_policy_input_refs']==evaluated['next_policy_input_refs']
        assert result['current_parent_context']==evaluated['current_parent_context']
    else:
        assert close['next_policy_input_refs'] is None
        assert result['current_parent_context']==current['current_parent_context']
    assert next(row[2] for row in calls if row[0]=='inputs')['prior_input_refs']==current['input_refs']
    calls.clear()
    assert obj.recover_round(start,attempt)==result
    assert [row[0] for row in calls]==['validate']


def test_unclosed_recovery_reenters_same_component_owners_with_same_refs(tmp_path,monkeypatch):
    obj,start,current,calls,trained,evaluated,offoff=wiring(tmp_path,monkeypatch,'TRAIN','PROMOTED')
    actual=offoff.execute_current_offoff_job
    def interrupted(**kwargs): raise RuntimeError('fixture interruption before OFFOFF adoption')
    offoff.execute_current_offoff_job=interrupted
    attempt=tmp_path/'attempt'
    with pytest.raises(RuntimeError,match='fixture interruption'):
        obj.execute_round(start,attempt)
    assert not (attempt/'DRIVER_ROUND_RESULT.json').exists()
    first_train=next(row[2] for row in calls if row[0]=='training')
    offoff.execute_current_offoff_job=actual;calls.clear()
    result=obj.recover_round(start,attempt)
    assert next(row[2] for row in calls if row[0]=='training')==first_train
    assert result['outcome']=='PROMOTED'


def test_current_capsule_preserves_engine_and_trained_launch_through_no_train(tmp_path):
    start={'round_id':'r','request_sha256':'a'*64,'parent_policy_id':'trained','parent_policy_artifact_sha256':'b'*64}
    materialized={'root':str(tmp_path/'rollout'),'input_member_manifest':{},'capsule_member_sha256':{}}
    for role,field in (('runtime','policy_runtime_binding_sha256'),('memory','round_memory_runtime_authority_sha256'),('train_manifest','train_update_manifest_sha256')):
        member='inputs/'+role+'.json'
        ref=put(Path(materialized['root'])/'input_capsule'/member,{'current':role})
        materialized['input_member_manifest'][role]={'member':member,'sha256':ref['sha256']};start[field]=ref['sha256']
    materialized['execution_profile_ref']=put(tmp_path/'profile.json',{'current':'profile'})
    start['execution_profile_sha256']=materialized['execution_profile_ref']['sha256']
    engine={'engine_profile_sha256':'c'*64};launch={'actual':'LoRA command'}
    engine_ref=put(tmp_path/'engine.json',engine);launch_ref=put(tmp_path/'launch.json',launch)
    authority_ref=put(tmp_path/'authority.json',{'schema_id':'ROUND_POLICY_NATIVE_LAUNCH_AUTHORITY_V1',
        'parent_policy_id':start['parent_policy_id'],'parent_policy_artifact_sha256':start['parent_policy_artifact_sha256'],
        'runtime_binding_file_sha256':start['policy_runtime_binding_sha256'],'launch_contract':launch_ref})
    prior_ref=put(tmp_path/'prior.json',{'schema_id':'ROUND_ROLLOUT_INPUT_REFERENCES_V1','request_sha256':start['request_sha256'],
        'engine_profile':engine_ref,'policy_launch_authority':authority_ref})
    name='ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json'
    bound=put(Path(materialized['root'])/'input_capsule'/name,{'round_id':'r','parent_policy_id':'trained',
        'runtime_authority':{'runtime_binding_file_sha256':start['policy_runtime_binding_sha256']},
        'engine_profile_authority':engine,'service_launch_contract':launch})
    materialized['capsule_member_sha256'][name]=bound['sha256']
    produced=driver.read_ref(driver._file_ref(driver.current_rollout_inputs(materialized,start,tmp_path/'out',prior_input_refs=prior_ref)))
    assert produced['policy_launch_authority']==authority_ref
    assert driver.read_ref(driver._file_ref(produced['engine_profile']))==engine


def test_native_closed_validation_recovery_and_complete_next_registration(tmp_path):
    case=Path(__file__).with_name('native_driver_case.py')
    code=(f'import sys,os,runpy\nsys.path[:0]={[str(V17),str(V17/"live_adapter")]!r}\n'
        f'os.chdir({str(V17/"native_bba_full")!r})\n'
        'from memory_binding.source_overlay import install_memory_overlay\n'
        f'install_memory_overlay({str(V17/"native_bba_full")!r})\n'
        f'runpy.run_path({str(case)!r},init_globals={{"case_root":{str(tmp_path)!r}}})')
    result=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
