"""The ledger's current-parent/current-profile rebind; sealed episodes stay intact."""
from pathlib import Path
import types


def resolve_condition(binding, request, runtime, profile, accepted, explicit):
    parent = binding.get('parent_policy_id')
    if not isinstance(parent,str) or not parent.strip() or any(x.get('parent_policy_id')!=parent for x in (request,accepted)) or profile.get('policy_version')!=parent:
        raise ValueError('SOURCE_CONDITION_PARENT_AUTHORITY_MISMATCH')
    rid=binding.get('round_id')
    if not isinstance(rid,str) or not rid or any(x.get('round_id')!=rid for x in (request,accepted)):
        raise ValueError('SOURCE_CONDITION_ROUND_AUTHORITY_MISMATCH')
    schema=runtime.get('schema_id')
    if profile.get('schema_id')!='ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1' or schema not in ('CLEAN_PI0_LIVE_RUNTIME_BINDING_V2','CURRENT_TRAINED_POLICY_RUNTIME_BINDING_V1'):
        raise ValueError('SOURCE_CONDITION_PROFILE_SCHEMA_MISMATCH')
    if schema=='CURRENT_TRAINED_POLICY_RUNTIME_BINDING_V1':
        if runtime.get('schema_version')!=1 or runtime.get('policy_id')!=parent:
            raise ValueError('SOURCE_CONDITION_TRAINED_PARENT_IDENTITY_MISMATCH')
        artifact=request.get('parent_policy_artifact_sha256')
        if not isinstance(artifact,str) or len(artifact)!=64 or any(runtime.get(k)!=artifact for k in ('adapter_bundle_sha256','policy_runtime_manifest_sha256')):
            raise ValueError('SOURCE_CONDITION_TRAINED_ARTIFACT_MISMATCH')
    contract=profile.get('continuation_request_contract')
    if not isinstance(contract,dict) or contract!=runtime.get('continuation_request_contract'):
        raise ValueError('SOURCE_CONDITION_CONTINUATION_CONTRACT_MISMATCH')
    profile_id=contract.get('profile_id')
    if not isinstance(profile_id,str) or not profile_id.strip():
        raise ValueError('SOURCE_CONDITION_PROFILE_ID_MISSING')
    if not profile.get('served_model_name') or profile['served_model_name']!=runtime.get('served_model_name'):
        raise ValueError('SOURCE_CONDITION_SERVED_MODEL_MISMATCH')
    condition=parent+'::'+profile_id
    if explicit is not None and explicit!=condition:
        raise ValueError('SOURCE_EXPLICIT_CONDITION_DIFFERS_FROM_CURRENT_AUTHORITY')
    return condition
