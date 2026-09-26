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
    if profile.get('schema_id')!='ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1' or runtime.get('schema_id')!='CLEAN_PI0_LIVE_RUNTIME_BINDING_V2':
        raise ValueError('SOURCE_CONDITION_PROFILE_SCHEMA_MISMATCH')
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


def bound_condition(binding, values, accepted, explicit, add):
    from exact_bindings import read_ref,canonical
    # This filename is the producer's typed protocol slot, under this round's
    # already registered root. The request independently binds its exact bytes.
    request=read_ref(binding['refs']['request'])
    runtime=read_ref(binding['refs']['actor_runtime'])
    if request!=values['request'] or runtime!=values['actor_runtime']:
        raise ValueError('SOURCE_CONDITION_INPUT_VALUES_CHANGED')
    if binding['refs']['actor_runtime']['file_sha256']!=request['policy_runtime_binding_sha256']:
        raise ValueError('SOURCE_CONDITION_RUNTIME_REQUEST_BINDING_MISMATCH')
    profile_ref={'path':str(Path(binding['state_root'])/'round_evidence/ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json'),
                 'file_sha256':request['execution_profile_sha256']}
    profile_raw=read_ref(profile_ref,as_bytes=True)
    import json
    profile=json.loads(profile_raw)
    condition=resolve_condition(binding,request,runtime,profile,accepted,explicit)
    add('current_rollout/ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json',profile_raw)
    add('native_preparation/SOURCE_POLICY_CONDITION_BINDING_V1.json',canonical({
        'schema_id':'SOURCE_POLICY_CONDITION_BINDING_V1', 'round_id':binding['round_id'],
        'parent_policy_id':binding['parent_policy_id'], 'source_policy_condition':condition,
        'derivation':'current_parent_policy_version::registered_continuation_profile_id',
        'profile_ref':profile_ref,'request_ref':binding['refs']['request'],
        'actor_runtime_ref':binding['refs']['actor_runtime'],
        'accepted_pre_logical_call_id':accepted['accepted_pre_logical_call_id'],
        'source_bundle_rewritten':False,'scientific_selection_changed':False}))
    return condition


def capture_function(ref):
    from exact_bindings import read_ref
    raw=read_ref({'path':ref['path'],'file_sha256':ref['sha256']},as_bytes=True)
    source=raw.decode()
    old="        condition = episode.policy_condition_id\n        if not condition:\n            raise BindingError('REGISTERED_SOURCE_POLICY_CONDITION_MISSING')"
    if source.count(old)!=1: raise ValueError('SOURCE_CONDITION_OVERLAY_SOURCE_DRIFT')
    source=source.replace(old,"        condition = _bound_condition(binding, values, accepted, episode.policy_condition_id, add)")
    module=types.ModuleType('_registered_source_condition');module.__file__=ref['path'];module._bound_condition=bound_condition
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    return module.materialize_capture
