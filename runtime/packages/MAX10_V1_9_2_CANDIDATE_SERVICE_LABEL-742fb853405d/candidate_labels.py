"""Native service label from full policy and artifact identity; no truncation."""
import json,hashlib,types

def service_label(policy_id,adapter_sha):
    if not isinstance(policy_id,str) or not policy_id:raise ValueError('CURRENT_POLICY_ID_REQUIRED')
    if not isinstance(adapter_sha,str) or len(adapter_sha)!=64 or any(c not in '0123456789abcdef' for c in adapter_sha):raise ValueError('CURRENT_ADAPTER_SHA_REQUIRED')
    raw=json.dumps({'current_policy_id':policy_id,'adapter_bundle_sha256':adapter_sha},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def load_publisher(ref):
    from exact_bindings import read_ref
    raw=read_ref({'path':ref['path'],'file_sha256':ref.get('file_sha256',ref.get('sha256'))},as_bytes=True);source=raw.decode('utf8')
    old="'logical_condition_id':policy_id,'checkpoint_instance_id':policy_id,"
    if source.count(old)!=1:raise ValueError('CANDIDATE_LABEL_SOURCE_ANCHOR')
    new="'logical_condition_id':_service_label(policy_id,accepted['adapter_bundle_sha256']),'checkpoint_instance_id':_service_label(policy_id,accepted['adapter_bundle_sha256']),"
    module=types.ModuleType('_registered_candidate_labels');module.__file__=ref['path'];module._service_label=service_label
    exec(compile(source.replace(old,new),ref['path'],'exec'),module.__dict__)
    return module.publish_candidate

def adapter_capacity(server,parent,candidate):
    # max_loras is the frozen per-batch capability, not the registry size.
    value=dict(server)
    count=sum(item['kind']=='LORA_ADAPTER' for item in (parent,candidate))
    value['max_cpu_loras']=max(value['max_cpu_loras'],count)
    return value

def load_registered_inputs(ref):
    from exact_bindings import read_ref
    source=read_ref({'path':ref['path'],'file_sha256':ref.get('file_sha256',ref.get('sha256'))},as_bytes=True).decode('utf8')
    old="    server['max_loras'] = max(server['max_loras'],count)\n    server['max_cpu_loras'] = max(server['max_cpu_loras'],count)"
    if source.count(old)!=1:raise ValueError('SELECT_CAPACITY_SOURCE_ANCHOR')
    module=types.ModuleType('_registered_select_capacity');module.__file__=ref['path'];module.__package__='offoff_binding';module._adapter_capacity=adapter_capacity
    exec(compile(source.replace(old,'    server = _adapter_capacity(server,parent,candidate)'),ref['path'],'exec'),module.__dict__)
    return module.materialize_registered_inputs
