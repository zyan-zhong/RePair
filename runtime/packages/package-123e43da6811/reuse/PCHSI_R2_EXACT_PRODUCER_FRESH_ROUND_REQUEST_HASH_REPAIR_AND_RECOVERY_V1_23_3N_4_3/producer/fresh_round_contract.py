"""The only new scientific-input boundary: current request over immutable capsule.

No file discovery by filename heuristics, no copied runtime output, no model or
scheduler calls. Native request and execution-attempt identity functions remain
the authority. Used identically by worker, finalizer and CPU preflight.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Mapping
from safe_io import canonical_bytes, load_json, sha_file
import hashlib

REQUEST_NAME='ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json'

def load_current_request(path:Path, *, request_type=None):
    if request_type is None:
        from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
        request_type=RoundRolloutCollectionRequestV1
    value=load_json(path)
    if value.get('schema_id')!='ROUND_ROLLOUT_COLLECTION_REQUEST_V1':
        raise ValueError('CURRENT_REQUEST_SCHEMA')
    kwargs={k:v for k,v in value.items() if k not in {'schema_id','schema_version','selection_rule'}}
    request=request_type(**kwargs)
    if request.to_dict()!=value:
        raise ValueError('CURRENT_REQUEST_NONCANONICAL_FIELDS')
    return request

def request_from_plan(plan:Mapping[str,Any]):
    path=plan.get('current_round_request_path')
    expected=plan.get('current_round_request_file_sha256')
    if path is None and expected is None:return None
    if not isinstance(path,str) or not Path(path).is_absolute() or not isinstance(expected,str):
        raise ValueError('CURRENT_REQUEST_BINDING_INCOMPLETE')
    if sha_file(Path(path))!=expected:raise ValueError('CURRENT_REQUEST_FILE_SHA_CHANGED')
    request=load_current_request(Path(path))
    if request.execution_attempt_id!=plan.get('activation_id'):
        raise ValueError('CURRENT_REQUEST_ACTIVATION_MISMATCH')
    return request

def validate_attempt_ordinal(ordinal:object)->int:
    if type(ordinal) is not int or ordinal<0:
        raise ValueError('ATTEMPT_ORDINAL_MUST_BE_NONNEGATIVE_INTEGER')
    return ordinal

def schedule_for_attempt(schedule,ordinal:int,identity_builder:Callable):
    validate_attempt_ordinal(ordinal)
    # The existing schedule builder owns the task/scientific cell identities.
    return tuple(replace(row,attempt_ordinal=ordinal,
        execution_attempt_id=identity_builder(scheduled_cell_id=row.cell.scheduled_cell_id,
                                               attempt_ordinal=ordinal)) for row in schedule)

def validate_request_against_capsule(request,binding:Mapping[str,Any],
                                     runtime_path:Path,memory_path:Path,
                                     profile_artifact:Mapping[str,Any])->None:
    r=request if isinstance(request,Mapping) else request.to_dict()
    runtime=load_json(runtime_path);memory_identity=load_json(memory_path)
    train=binding['train_update_authority'];memory=binding['memory_authority']
    expected={
      'parent_policy_id':binding['parent_policy_id'],
      'parent_policy_artifact_sha256':runtime['policy_runtime_manifest_sha256'],
      'policy_runtime_binding_sha256':sha_file(runtime_path),
      'round_memory_runtime_authority_sha256':sha_file(memory_path),
      'round_start_memory_snapshot_sha256':memory['active_snapshot_sha256'],
      'token_budget_contract_sha256':memory['token_budget_contract_sha256'],
      'train_update_manifest_sha256':train['manifest_sha256'],
      'rollout_seed':train['rollout_seed'],
      'execution_profile_sha256':hashlib.sha256(canonical_bytes(dict(profile_artifact))).hexdigest(),
    }
    for key,value in expected.items():
        if r.get(key)!=value:raise ValueError('CURRENT_REQUEST_CAPSULE_MISMATCH:'+key)
    if sha_file(runtime_path)!=binding['runtime_authority']['runtime_binding_file_sha256']:
        raise ValueError('CAPSULE_RUNTIME_FILE_SHA_MISMATCH')
    if sha_file(memory_path)!=memory['runtime_identity_file_sha256']:
        raise ValueError('CAPSULE_MEMORY_FILE_SHA_MISMATCH')
    if memory_identity['active_snapshot_sha256']!=memory['active_snapshot_sha256']:
        raise ValueError('CAPSULE_MEMORY_SNAPSHOT_MISMATCH')

def profile_from_binding(binding):
    # Instantiate the same native class used by the original worker.
    from pchsi.evaluation.policy_attempt_adapter import BoundI1PolicyExecutionProfileV1
    data=binding['policy_execution_profile']
    profile=BoundI1PolicyExecutionProfileV1(served_model_name=data['served_model_name'],
         continuation_request_contract=data['continuation_request_contract'],
         policy_version=data['policy_version'])
    artifact={'schema_id':'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1','schema_version':1,
        'profile_kind':profile.profile_id,'arm_id':profile.arm_id,
        'policy_version':profile.policy_version,'served_model_name':profile.served_model_name,
        'continuation_request_contract':profile.continuation_request_contract}
    return profile,artifact
