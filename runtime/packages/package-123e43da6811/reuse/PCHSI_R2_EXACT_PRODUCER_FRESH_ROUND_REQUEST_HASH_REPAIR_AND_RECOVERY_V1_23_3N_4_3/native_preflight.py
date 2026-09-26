"""Reuse native pure-input builders in an isolated CPU subprocess. No models."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
from recovery_core import equal_or_new,load_json,sha_file,checked,checked_timeout_retry,require_file
from fresh_round_contract import load_current_request,validate_request_against_capsule,profile_from_binding,schedule_for_attempt
from formal_rollout_support import find_capsule_file_by_sha
from runtime_surface_preflight import validate_runtime_surface

def run(capsule_root:Path,worktree:Path,request_path:Path,plan_path:Path,output:Path):
    binding=load_json(capsule_root/'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json')
    head=checked(['git','-C',str(worktree),'rev-parse','HEAD'])
    if head!=binding['implementation_head']:raise ValueError('NATIVE_WORKTREE_HEAD_MISMATCH')
    surface_receipt=validate_runtime_surface(worktree,capsule_root)
    sys.path.insert(0,str(worktree/'src'))
    request=load_current_request(request_path)
    train=binding['train_update_authority'];mem=binding['memory_authority'];runtime=binding['runtime_authority']
    manifest=find_capsule_file_by_sha(capsule_root,expected_sha256=train['manifest_sha256'],suffixes=('.jsonl',))
    rp=find_capsule_file_by_sha(capsule_root,expected_sha256=runtime['runtime_binding_file_sha256'],suffixes=('.json',))
    mp=find_capsule_file_by_sha(capsule_root,expected_sha256=mem['runtime_identity_file_sha256'],suffixes=('.json',))
    _,profile=profile_from_binding(binding)
    validate_request_against_capsule(request,binding,rp,mp,profile)
    from pchsi.round_control.clean_execution_binding import load_clean_train_pool_records,build_clean_train_schedule
    from pchsi.evaluation.run_schedule import execution_attempt_id
    from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
    plan=load_json(plan_path)
    records=load_clean_train_pool_records(manifest_path=manifest,expected_manifest_sha256=train['manifest_sha256'],
        train_root=Path(train['train_root']),expected_pool='TRAIN_UPDATE',expected_count=train['row_count'])
    base=build_clean_train_schedule(records=records,train_pool='TRAIN_UPDATE',seed=train['rollout_seed'])
    schedule=schedule_for_attempt(base,plan['fresh_execution_attempt_ordinal'],execution_attempt_id)
    if len(schedule)!=plan['total_schedule_count']:raise ValueError('NATIVE_SCHEDULE_COUNT_MISMATCH')
    if plan['activation_id']!=request.execution_attempt_id:raise ValueError('NATIVE_REQUEST_PLAN_ACTIVATION')
    runtime_value=load_json(rp)
    model=Path(runtime_value['base_model_local_path'])
    if not model.is_dir():raise ValueError('NATIVE_MODEL_DIRECTORY_MISSING:'+str(model))
    launch=binding['service_launch_contract']['launch_command']
    if not isinstance(launch,list) or not launch or not all(isinstance(x,str) for x in launch):raise ValueError('NATIVE_LAUNCH_ARGV_INVALID')
    if not Path(launch[0]).is_file():raise ValueError('NATIVE_SERVICE_PYTHON_MISSING')
    # Existing allocation contract builder, not a duplicated resource validator.
    spec=importlib.util.spec_from_file_location('n4_existing_alloc',capsule_root/'allocation_preflight.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    slurm=load_json(capsule_root/'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1.json')
    allocation=load_json(capsule_root/'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_ALLOCATION_PREFLIGHT_V1.json')
    if module.build_allocation_preflight_contract(slurm)!=allocation:raise ValueError('NATIVE_ALLOCATION_CONTRACT_MISMATCH')
    schedule_bytes=json.dumps([{'scientific_cell_id':s.scientific_cell_id,'execution_attempt_id':s.execution_attempt_id,'task_id':s.cell.task_id,'task_index':s.cell.task_index} for s in schedule],sort_keys=True,separators=(',',':')).encode()
    result={'schema_id':'NATIVE_R2_CPU_PREFLIGHT_V1','status':'PASS','implementation_head':head,
        'request_file_sha256':sha_file(request_path),'request_sha256':request.request_sha256,
        'current_round_id':request.round_id,'archived_capsule_round_id':binding['round_id'],
        'current_request_is_independent_authority':True,'archived_binding_mutated':False,
        'scheduled_count':len(schedule),'schedule_identity_sha256':hashlib.sha256(schedule_bytes).hexdigest(),
        'fresh_execution_attempt_ordinal':plan['fresh_execution_attempt_ordinal'],
        'profile_file_sha256':request.execution_profile_sha256,'runtime_surface_preflight':surface_receipt,'git_preflight_mode':'BOUNDED_RUNTIME_SURFACES','model_loaded':False,'environment_calls':0,'provider_calls':0}
    equal_or_new(output,result)
    print('NATIVE_REQUEST_CAPSULE_SCOPE_PREFLIGHT=PASS',flush=True)
    print('NATIVE_TASK_FILE_AND_SCHEDULE_PREFLIGHT=PASS',flush=True)
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--capsule-root',type=Path,required=True);a.add_argument('--worktree',type=Path,required=True);a.add_argument('--request',type=Path,required=True);a.add_argument('--plan',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    n=a.parse_args();run(n.capsule_root,n.worktree,n.request,n.plan,n.output)
