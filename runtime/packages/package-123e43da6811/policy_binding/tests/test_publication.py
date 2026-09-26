"""Actual native artifact formats with explicitly synthetic weight bytes; no GPU."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[4]
V17=ROOT/'work/v17'
REPO=V17/'native_bba_full'
CAP=ROOT/'work/v16/reference/PCHSI_CAMPAIGN_AUTHORITY_DRIVEN_FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_V1_23_2/V123133_MEMORY_AWARE_GENERIC_ROLLOUT_LIVE_SOURCE_CAPSULE.zip'
H44=ROOT/'work/reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4'
sys.path.insert(0,str(V17));sys.path.insert(0,str(REPO/'src'))
sys.path.insert(0,str(V17/'training_binding/tests'))
from policy_binding.launch import canonical,sha,extend_lora_launch
from continuity_binding.api import write_once,read_ref


def ref(path): return {'path':str(path.absolute()),'sha256':sha(path.read_bytes())}


def fixture(tmp_path,monkeypatch):
    from test_training_entry import _accepted_artifacts
    from test_materializer import _native
    from training_binding.accepted_output import read_accepted_output
    from entry import candidate_runtime,training
    _native()
    refs,out=_accepted_artifacts(tmp_path,monkeypatch,fixture_rank=16)
    # The fixture has already loaded actual native Generic sources; skip only
    # production Git/source registration bootstrapping, never artifact validation.
    monkeypatch.setattr(training,'load_training_sources',lambda registration:None)
    accepted=read_accepted_output(refs);parent=accepted['contract']['parent']
    with zipfile.ZipFile(CAP) as archive:
        runtime=json.loads(archive.read('CLEAN_PI0_LIVE_RUNTIME_BINDING_V2.json'))
        bound=json.loads(archive.read('ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json'))
    runtime.update(tokenizer_revision=parent['base_model_revision'])
    runtime_ref=write_once(tmp_path/'runtime.json',runtime)
    profile={'schema_id':'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1','schema_version':1,
        'profile_kind':'ROUND_BOUND_I1_EXECUTION_PROFILE_V1','arm_id':'I1_STRUCTURED_SERIALIZATION_CONSTRAINT_V1',
        'policy_version':parent['policy_id'],'served_model_name':runtime['served_model_name'],
        'continuation_request_contract':runtime['continuation_request_contract']}
    profile_ref=write_once(tmp_path/'profile.json',profile)
    from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
    start=RoundRolloutCollectionRequestV1(round_id=accepted['contract']['round_id'],
        execution_attempt_id=accepted['authorization']['execution_attempt_id'],parent_policy_id=parent['policy_id'],
        parent_policy_artifact_sha256=runtime['policy_runtime_manifest_sha256'],
        policy_runtime_binding_sha256=runtime_ref['sha256'],execution_profile_sha256=profile_ref['sha256'],
        train_update_manifest_sha256='1'*64,round_memory_runtime_authority_sha256='2'*64,
        round_start_memory_snapshot_sha256='3'*64,token_budget_contract_sha256='4'*64,
        execution_namespace='SOFTWARE-FIXTURE',rollout_seed=17).to_dict()
    inputs=write_once(tmp_path/'inputs.json',{'schema_id':'ROUND_ROLLOUT_INPUT_REFERENCES_V1',
        'request_sha256':start['request_sha256'],'runtime':runtime_ref,'profile':profile_ref,
        'engine_profile':write_once(tmp_path/'engine.json',bound['engine_profile_authority'])})
    trained={'schema_id':'CURRENT_NATIVE_TRAINING_EXECUTION_RESULT_V1',
        **{key:start[key] for key in ('round_id','request_sha256','parent_policy_id','parent_policy_artifact_sha256')},
        'training_execution_count':1,'model_training_executed':True,'current_parent_context':refs,**refs,
        **{key:accepted[key] for key in ('adapter_path','adapter_bundle_sha256','final_trainable_parameter_sha256')},
        **{key:{'path':accepted[key]['path'],'sha256':accepted[key]['sha256']} for key in ('formal_run_manifest_ref','adapter_artifact_manifest_ref')}}
    trained['result_ref']=write_once(tmp_path/'training-result.json',trained)
    return candidate_runtime,dict(start=start,current_inputs_ref=inputs,trained=trained,
        output_root=tmp_path/'published',source_registration={'rollout_capsule_ref':ref(CAP)}),accepted


def test_native_accepted_artifact_chain_publishes_real_lora_launch_and_idempotent_refs(tmp_path,monkeypatch):
    publisher,args,accepted=fixture(tmp_path,monkeypatch)
    result=publisher.publish_candidate(**args)
    assert publisher.publish_candidate(**args)==result
    runtime=read_ref(result['next_policy_input_refs']['runtime'])
    candidate=read_ref(result['candidate_ref'])
    assert candidate['artifact_sha256']==runtime['policy_runtime_manifest_sha256']==accepted['adapter_bundle_sha256']
    authority=read_ref(result['next_policy_input_refs']['policy_launch_authority'])
    launch=read_ref(authority['launch_contract']);command=launch['launch_command']
    assert command[command.index('--served-model-name')+1]!=runtime['served_model_name']
    assert command[command.index('--lora-modules')+1]==runtime['served_model_name']+'='+accepted['adapter_path']
    assert command[command.index('--max-lora-rank')+1]==str(runtime['adapter_rank'])
    assert result['promotion_decision_made'] is False
    assert result['current_parent_context']==args['trained']['current_parent_context']
    assert set(result['next_policy_input_refs'])=={'runtime','profile','policy_launch_authority','engine_profile'}
    # H4.4 may choose an allocation-local port; every scientific identity stays.
    moved=dict(runtime,policy_base_url='http://127.0.0.1:39217')
    modules=publisher._lifecycle(args['source_registration']['rollout_capsule_ref'])
    base=modules['policy_runtime_engine_profile']['build_current_runtime_service_launch_contract'](
        moved,read_ref(result['next_policy_input_refs']['engine_profile']),python_executable=sys.executable)
    routed=extend_lora_launch(base,moved)
    assert routed['trained_adapter_binding']==launch['trained_adapter_binding']
    assert routed['launch_command'][routed['launch_command'].index('--port')+1]=='39217'
    Path(accepted['adapter_path'],'adapter_model.safetensors').write_bytes(b'changed weights')
    with pytest.raises(ValueError,match='SHA_MISMATCH'):
        publisher.publish_candidate(**args)


def test_publication_rejects_other_current_round_before_writes(tmp_path,monkeypatch):
    publisher,args,accepted=fixture(tmp_path,monkeypatch)
    args['trained']=dict(args['trained'],round_id='future')
    with pytest.raises(ValueError,match='TRAINING_CURRENT_REQUEST'):
        publisher.publish_candidate(**args)
    assert not args['output_root'].exists()


def test_h44_exact_launch_hook_is_inherited_to_gpu_style_child(tmp_path,monkeypatch):
    publisher,args,accepted=fixture(tmp_path,monkeypatch)
    result=publisher.publish_candidate(**args)
    from memory_binding.worker_bootstrap import worker_environment
    environment=worker_environment(REPO)
    environment['PCHSI_CURRENT_H44_REGISTERED_ROOT']=str(H44)
    runtime_path=result['next_policy_input_refs']['runtime']['path']
    engine_path=result['next_policy_input_refs']['engine_profile']['path']
    code=f'''import json,sys
from pathlib import Path
sys.path.insert(0,{str(H44/'vendor')!r})
from policy_runtime_engine_profile import build_current_runtime_service_launch_contract
runtime=json.loads(Path({runtime_path!r}).read_bytes())
profile=json.loads(Path({engine_path!r}).read_bytes())
launch=build_current_runtime_service_launch_contract(runtime,profile,python_executable=sys.executable)
assert '--enable-lora' in launch['launch_command']
assert launch['trained_adapter_binding']['adapter_bundle_sha256']==runtime['adapter_bundle_sha256']
'''
    process=subprocess.run([sys.executable,'-B','-c',code],env=environment,capture_output=True,text=True)
    assert process.returncode==0,process.stdout+process.stderr


def test_next_rollout_materializer_embeds_published_lora_launch(tmp_path,monkeypatch):
    publisher,args,accepted=fixture(tmp_path,monkeypatch)
    result=publisher.publish_candidate(**args)
    helper=ROOT/'work/v16/rollout_adapter/tests/test_adapter.py'
    spec=importlib.util.spec_from_file_location('_registered_rollout_fixture',helper)
    fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)
    spec=fixture_module.fixture(tmp_path/'rollout_inputs')
    from rollout_adapter import materializer
    from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1,RoundRolloutExecutionBindingV1
    from dataclasses import fields
    original=json.loads(Path(spec['request']['path']).read_bytes())
    values={field.name:original[field.name] for field in fields(RoundRolloutCollectionRequestV1)}
    candidate=read_ref(result['candidate_ref']);refs=result['next_policy_input_refs']
    values.update(parent_policy_id=candidate['policy_id'],parent_policy_artifact_sha256=candidate['artifact_sha256'],
        policy_runtime_binding_sha256=refs['runtime']['sha256'],execution_profile_sha256=refs['profile']['sha256'],request_sha256=None)
    request=RoundRolloutCollectionRequestV1(**values)
    formal=json.loads(Path(spec['execution_binding']['path']).read_bytes())
    values={field.name:formal[field.name] for field in fields(RoundRolloutExecutionBindingV1)}
    values['request_sha256']=request.request_sha256
    values['binding_sha256']=None
    execution=RoundRolloutExecutionBindingV1(**values)
    spec['request']=write_once(tmp_path/'next-request.json',request.to_dict())
    spec['execution_binding']=write_once(tmp_path/'next-execution.json',execution.to_dict())
    spec['input_refs']=write_once(tmp_path/'next-inputs.json',{
        'schema_id':'ROUND_ROLLOUT_INPUT_REFERENCES_V1','request_sha256':request.request_sha256,**refs})
    materialized=materializer.materialize(spec,tmp_path/'next-rollout')
    with zipfile.ZipFile(materialized['capsule_path']) as archive:
        binding=json.loads(archive.read('ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json'))
        assert '--enable-lora' in binding['service_launch_contract']['launch_command']
        assert binding['service_launch_contract']['trained_adapter_binding']['adapter_bundle_sha256']==candidate['artifact_sha256']
        assert binding['runtime_authority']['runtime_binding_file_sha256']==refs['runtime']['sha256']
