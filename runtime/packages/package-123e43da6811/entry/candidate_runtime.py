"""Publish actual accepted adapter identities before native OFF/OFF evaluation.

Publication does not promote a policy. Only the native promotion/tail owner may
pass next_policy_input_refs into a subsequent round.
"""
import copy
import io
import json
from pathlib import Path
import sys
import zipfile

from policy_binding.launch import canonical,sha,RUNTIME_SCHEMA,extend_lora_launch


def _io():
    from continuity_binding.api import read_ref,read_bytes_ref,write_once
    return read_ref,read_bytes_ref,write_once


def _simple(ref):
    return {'path':ref['path'],'sha256':ref['sha256']}


def _accepted(trained,source_registration):
    from entry.training import load_training_sources
    from training_binding.accepted_output import read_accepted_output
    load_training_sources(source_registration)
    return read_accepted_output(trained)


def _lifecycle(capsule_ref):
    _,read_bytes,_=_io()
    modules={}
    with zipfile.ZipFile(io.BytesIO(read_bytes(capsule_ref))) as archive:
        for name in ('policy_runtime_engine_profile','policy_runtime_engine_profile_receipt','policy_runtime_slurm_execution'):
            member='policy_runtime_lifecycle_source/'+name+'.py'
            if archive.namelist().count(member)!=1:
                raise ValueError('CANDIDATE_LIFECYCLE_SOURCE_CARDINALITY:'+member)
            raw=archive.read(member)
            namespace={'__name__':'_candidate_'+name,'__file__':capsule_ref['path']+'!/'+member}
            exec(compile(raw,namespace['__file__'],'exec'),namespace)
            modules[name]=namespace
    return modules


def publish_candidate(*,start,current_inputs_ref,trained,output_root,source_registration):
    read,read_bytes,write=_io()
    from continuity_binding.api import native_request
    native_request(start)
    inputs=read(current_inputs_ref)
    if inputs.get('schema_id')!='ROUND_ROLLOUT_INPUT_REFERENCES_V1' or inputs.get('request_sha256')!=start['request_sha256']:
        raise ValueError('CANDIDATE_CURRENT_INPUT_REQUEST')
    for key,field in (('runtime','policy_runtime_binding_sha256'),('profile','execution_profile_sha256')):
        read_bytes(inputs[key])
        if inputs[key]['sha256']!=start[field]: raise ValueError('CANDIDATE_CURRENT_INPUT_IDENTITY:'+key)
    current=read(inputs['runtime']);profile=read(inputs['profile'])
    if current['policy_runtime_manifest_sha256']!=start['parent_policy_artifact_sha256']:
        raise ValueError('CANDIDATE_CURRENT_PARENT_WEIGHTS')
    if trained.get('schema_id')!='CURRENT_NATIVE_TRAINING_EXECUTION_RESULT_V1' or any(
            trained.get(key)!=start[key] for key in ('round_id','request_sha256','parent_policy_id','parent_policy_artifact_sha256')):
        raise ValueError('CANDIDATE_TRAINING_CURRENT_REQUEST')
    if trained.get('training_execution_count')!=1 or trained.get('model_training_executed') is not True:
        raise ValueError('CANDIDATE_ACTUAL_COMPLETED_TRAINING_REQUIRED')
    if read(trained['result_ref'])!={k:v for k,v in trained.items() if k!='result_ref'}:
        raise ValueError('CANDIDATE_TRAINING_RESULT_REF')
    accepted=_accepted(trained,source_registration)
    contract=accepted['contract'];run=accepted['run_manifest']
    if contract['round_id']!=start['round_id'] or contract['parent']['policy_id']!=start['parent_policy_id']:
        raise ValueError('CANDIDATE_NATIVE_TRAINING_PARENT_ROUND')
    if accepted['authorization']['execution_attempt_id']!=start['execution_attempt_id']:
        raise ValueError('CANDIDATE_NATIVE_TRAINING_ATTEMPT')
    for key in ('adapter_path','adapter_bundle_sha256','final_trainable_parameter_sha256'):
        if trained[key]!=accepted[key]: raise ValueError('CANDIDATE_ACCEPTED_TRAINING_IDENTITY:'+key)
    for key in ('formal_run_manifest_ref','adapter_artifact_manifest_ref'):
        if trained[key]!=_simple(accepted[key]): raise ValueError('CANDIDATE_ACCEPTED_ARTIFACT_REF:'+key)
    parent_fields=contract['parent']
    if parent_fields['base_model_revision']!=current['tokenizer_revision']:
        raise ValueError('CANDIDATE_CURRENT_BASE_REVISION')
    root=Path(output_root).absolute()
    # Candidate identity is a deterministic byte-bound publication label, not a
    # selection or claim of promotion. Full adapter identity remains authoritative.
    policy_id='CURRENT-TRAINED-'+sha(canonical({'request_sha256':start['request_sha256'],
        'adapter_bundle_sha256':accepted['adapter_bundle_sha256']}))
    if accepted['adapter_bundle_sha256']==start['parent_policy_artifact_sha256']:
        raise ValueError('CANDIDATE_WEIGHTS_MUST_CHANGE')
    manifest=read(trained['adapter_artifact_manifest_ref'])
    config=read({'path':str(Path(accepted['adapter_path'])/'adapter_config.json'),
        'sha256':manifest['files']['adapter_config.json']['sha256']})
    if config['r']!=contract['peft']['r']:
        raise ValueError('CANDIDATE_ACCEPTED_PEFT_RANK')
    candidate={'schema_id':'CURRENT_OFFOFF_POLICY_BINDING_V1','kind':'LORA_ADAPTER',
        **{key:start[key] for key in ('round_id','request_sha256','execution_attempt_id','parent_policy_id','parent_policy_artifact_sha256')},
        'policy_id':policy_id,'artifact_sha256':accepted['adapter_bundle_sha256'],
        'artifact_root':accepted['adapter_path'],'artifact_manifest':trained['adapter_artifact_manifest_ref'],
        'base_model_repository':parent_fields['base_model_repository'],'base_model_revision':parent_fields['base_model_revision'],
        'adapter_rank':config['r'],'training_seed':contract['budget']['training_seed'],
        'logical_condition_id':policy_id,'checkpoint_instance_id':policy_id,
        'training_run_id':accepted['authorization']['execution_attempt_id'],
        'training_config_ref':trained['training_contract_ref'],
        'training_result_ref':trained['result_ref'],'current_parent_context':trained['current_parent_context'],
        'final_trainable_parameter_sha256':accepted['final_trainable_parameter_sha256']}
    from offoff_binding.materialize import _artifact
    _artifact(candidate)
    candidate_ref=write(root/'CANDIDATE_OFFOFF_POLICY.json',candidate)
    if current.get('schema_id')==RUNTIME_SCHEMA:
        parent=read(current['candidate_policy_ref'])
        if parent['policy_id']!=start['parent_policy_id'] or parent['artifact_sha256']!=start['parent_policy_artifact_sha256']:
            raise ValueError('CANDIDATE_PREVIOUS_POLICY_REF')
        _artifact(parent)
    else:
        if current.get('schema_id')!='CLEAN_PI0_LIVE_RUNTIME_BINDING_V2':
            raise ValueError('CANDIDATE_PARENT_RUNTIME_SCHEMA')
        parent={'schema_id':'CURRENT_OFFOFF_POLICY_BINDING_V1','kind':'BASE_MODEL',
            'policy_id':start['parent_policy_id'],'artifact_sha256':start['parent_policy_artifact_sha256'],
            'artifact_root':current['base_model_local_path'],'runtime_ref':inputs['runtime'],
            'artifact_manifest':{'path':parent_fields['base_model_artifact_manifest_path'],
                'sha256':parent_fields['base_model_artifact_manifest_sha256']},
            'base_model_repository':parent_fields['base_model_repository'],'base_model_revision':parent_fields['base_model_revision']}
        read_bytes(parent['artifact_manifest'])
    parent_ref=write(root/'PARENT_OFFOFF_POLICY.json',parent)
    runtime=copy.deepcopy(current)
    runtime.update(schema_id=RUNTIME_SCHEMA,schema_version=1,policy_id=policy_id,
        policy_runtime_manifest_sha256=accepted['adapter_bundle_sha256'],served_model_name=policy_id,
        base_served_model_name=current.get('base_served_model_name',current['served_model_name']),
        adapter_path=accepted['adapter_path'],adapter_bundle_sha256=accepted['adapter_bundle_sha256'],
        adapter_rank=config['r'],adapter_artifact_manifest_ref=trained['adapter_artifact_manifest_ref'],
        final_trainable_parameter_sha256=accepted['final_trainable_parameter_sha256'],
        candidate_policy_ref=candidate_ref,current_parent_context=trained['current_parent_context'],
        training_result_ref=trained['result_ref'],scientific_execution_authorized=False)
    runtime_ref=write(root/'CANDIDATE_POLICY_RUNTIME.json',runtime)
    profile.update(policy_version=policy_id,served_model_name=runtime['served_model_name'],
        continuation_request_contract=runtime['continuation_request_contract'])
    profile_ref=write(root/'CANDIDATE_POLICY_EXECUTION_PROFILE.json',profile)
    lifecycle=_lifecycle(source_registration['rollout_capsule_ref'])
    engine=read(inputs['engine_profile'])
    lifecycle['policy_runtime_engine_profile_receipt']['validate_engine_profile_receipt'](engine,runtime)
    engine_ref=write(root/'CANDIDATE_ENGINE_PROFILE.json',engine)
    launch=lifecycle['policy_runtime_engine_profile']['build_current_runtime_service_launch_contract'](
        runtime,engine,python_executable=sys.executable)
    launch=extend_lora_launch(launch,runtime)
    lifecycle['policy_runtime_slurm_execution']['validate_launch_contract'](launch)
    launch_ref=write(root/'CANDIDATE_SERVICE_LAUNCH_CONTRACT.json',launch)
    authority_ref=write(root/'CANDIDATE_POLICY_LAUNCH_AUTHORITY.json',{
        'schema_id':'ROUND_POLICY_NATIVE_LAUNCH_AUTHORITY_V1','parent_policy_id':policy_id,
        'parent_policy_artifact_sha256':accepted['adapter_bundle_sha256'],
        'runtime_binding_file_sha256':runtime_ref['sha256'],'launch_contract':launch_ref,
        'training_result_ref':trained['result_ref'],'rollout_capsule_ref':source_registration['rollout_capsule_ref']})
    result={'schema_id':'CURRENT_ACCEPTED_CANDIDATE_RUNTIME_PUBLICATION_V1',
        'round_id':start['round_id'],'request_sha256':start['request_sha256'],
        'parent_ref':parent_ref,'candidate_ref':candidate_ref,
        'next_policy_input_refs':{'runtime':runtime_ref,'profile':profile_ref,
            'policy_launch_authority':authority_ref,'engine_profile':engine_ref},
        'current_parent_context':trained['current_parent_context'],
        'training_result_ref':trained['result_ref'],'promotion_decision_made':False,
        'policy_service_started':False,'model_training_executed_by_publisher':False}
    result_ref=write(root/'CANDIDATE_RUNTIME_PUBLICATION.json',result)
    return dict(result,result_ref=result_ref)
