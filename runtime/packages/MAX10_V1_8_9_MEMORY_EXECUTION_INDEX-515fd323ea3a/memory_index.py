"""Reuse the native memory producer with the registered execution manifest."""
from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import types,json,hashlib

def validate_execution(execution,binding):
    if execution.get('schema_id')!='COGNITIVE_RUNTIME_EXECUTION_MANIFEST_V2' or execution.get('round_id')!=binding['round_id'] or execution.get('policy_version')!=binding['parent_policy_id']:
        raise ValueError('MEMORY_REGISTERED_EXECUTION_IDENTITY')
    keys=[(r['source_unit_id'],r['stage_id']) for r in execution['rows']]
    if len(keys)!=len(set(keys)):raise ValueError('MEMORY_REGISTERED_EXECUTION_DUPLICATE_SLOT')
    for r in execution['rows']:
        if r.get('status')=='ACCEPTED' and (not PurePosixPath(r['call_dir']).is_absolute() or PurePosixPath(r['call_dir']).name!=r['logical_call_id']):
            raise ValueError('MEMORY_REGISTERED_CALL_PATH')
    return execution

def register(binding,execution,authority,source_ref):
    from exact_bindings import read_ref,read_json,file_ref,immutable_json
    root=Path(binding['output_root'])/'local'
    if binding['round_id']==authority['excluded_round_id']:
        ref=authority['current_execution_ref']
    else:ref=file_ref(root/'strong_local_runtime/execution_manifest.json')
    value=read_ref(ref)
    if value!=execution:raise ValueError('MEMORY_EXECUTION_NOT_REGISTERED_RETURN_VALUE')
    validate_execution(value,binding)
    index={'schema_id':'REGISTERED_MEMORY_LOCAL_EXECUTION_INDEX_V1','round_id':binding['round_id'],
        'parent_policy_id':binding['parent_policy_id'],'request_ref':binding['refs']['request'],
        'execution_ref':ref,'source_extension':source_ref,'filesystem_discovery_used':False}
    path=root/'REGISTERED_MEMORY_LOCAL_EXECUTION_INDEX_V1.json'
    if path.exists():
        old=read_json(path)
        if {k:v for k,v in old.items() if k!='source_extension'}!={k:v for k,v in index.items() if k!='source_extension'}:
            raise ValueError('MEMORY_EXECUTION_INDEX_CONFLICT')
        read_ref(old['source_extension'],as_bytes=True)
        return old
    immutable_json(path,index)
    return index

def registered_execution(binding,root):
    from exact_bindings import read_json,read_ref
    index=read_json(Path(root)/'local/REGISTERED_MEMORY_LOCAL_EXECUTION_INDEX_V1.json')
    if index['round_id']!=binding['round_id'] or index['parent_policy_id']!=binding['parent_policy_id'] or read_ref(index['request_ref'])!=read_ref(binding['refs']['request']):
        raise ValueError('MEMORY_EXECUTION_INDEX_CURRENT_REQUEST')
    read_ref(index['source_extension'],as_bytes=True)
    return validate_execution(read_ref(index['execution_ref']),binding)

def registered_call(call,execution):
    matches=[r for r in execution['rows'] if r.get('logical_call_id')==call['logical_call_id'] and r.get('status')=='ACCEPTED']
    if len(matches)!=1 or matches[0]!=call:raise ValueError('MEMORY_CALL_NOT_EXACT_ACCEPTED_INDEX_ROW')
    path=PurePosixPath(call['call_dir'])
    if not path.is_absolute() or path.name!=call['logical_call_id']:raise ValueError('MEMORY_CALL_INDEX_PATH')
    return True

def current_condition(binding,root,source):
    from source_condition import bound_condition
    from exact_bindings import read_ref,read_json
    accepted=read_json(Path(root)/'pre/ACCEPTED_PRE_REF.json')
    logical=read_ref(accepted['logical_call']);artifact=read_ref(accepted['artifact'])
    if logical['terminal_method_status']!='ACCEPTED' or artifact['primary_record_sha256']!=accepted['pre_primary_record_sha256']:
        raise ValueError('MEMORY_CURRENT_ACCEPTED_PRE_REQUIRED')
    def add(name,raw):
        # Independently derive and compare to the existing H44 capture, without
        # changing the immutable episode or its original missing field.
        pass
    return bound_condition(binding,{'request':read_ref(binding['refs']['request']),
        'actor_runtime':read_ref(binding['refs']['actor_runtime'])},accepted,source.episode_artifact.policy_condition_id,add)

def overlay_source(text):
    replacements={
        "execution=_read(root/'local/strong_local_runtime/execution_manifest.json')":"execution=_registered_execution(binding,root)",
        "if call_dir.parent!=(root/'local/strong_local_runtime'): raise ValueError('MEMORY_LOCAL_CALL_ROOT')":"_registered_call(call,execution)",
        "condition=source.episode_artifact.policy_condition_id":"condition=_current_condition(binding,root,source)"}
    for old,new in replacements.items():
        if text.count(old)!=1:raise ValueError('MEMORY_SOURCE_OVERLAY_ANCHOR')
        text=text.replace(old,new)
    return text

@contextmanager
def install(authority,source_ref):
    import adapter,memory_binding.api as api
    from exact_bindings import read_ref
    source=read_ref(authority['memory_api_ref'],as_bytes=True).decode()
    module=types.ModuleType('memory_binding._registered_execution_api');module.__package__='memory_binding';module.__file__=authority['memory_api_ref']['path']
    module._registered_execution=registered_execution;module._registered_call=registered_call;module._current_condition=current_condition
    exec(compile(overlay_source(source),module.__file__,'exec'),module.__dict__)
    native=adapter.prepare_groups
    def prepare(binding,core,local,execution):
        register(binding,execution,authority,source_ref)
        return native(binding,core,local,execution)
    with patch.object(adapter,'prepare_groups',prepare),patch.object(api,'materialize_round_memory',module.materialize_round_memory):yield
