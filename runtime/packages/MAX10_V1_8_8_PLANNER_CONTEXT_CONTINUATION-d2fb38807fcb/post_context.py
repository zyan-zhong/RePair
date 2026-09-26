"""Reuse H4.4's content projection; retain full verifier bytes for native audit."""
from copy import deepcopy
import ast, hashlib, json

def native_compactor(source):
    if hashlib.sha256(source['source'].encode()).hexdigest()!=source['sha256']:
        raise ValueError('REGISTERED_POST_COMPACTOR_SOURCE_MISMATCH')
    tree=ast.parse(source['source'])
    names={'_branch_index_row','_compact_environment'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes}!=names:raise ValueError('POST_COMPACTOR_FUNCTIONS_REQUIRED')
    def canon(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    ns={'sha':lambda b:hashlib.sha256(b).hexdigest(),'canonical':canon}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<registered H4.4 compactor>','exec'),ns)
    return ns['_compact_environment']

def compact_projection(projection,source):
    v=deepcopy(projection);env=projection['environment_result_package']
    if env['environment_result_package_sha256']!=projection['environment_result_package_sha256']:
        raise ValueError('POST_PROJECTION_VERIFIER_IDENTITY_MISMATCH')
    compact=native_compactor(source)(env)
    if (compact['state_results']!=env['state_results'] or compact['pair_results']!=env['pair_results']
            or compact['stable_effect_counts']!=env['stable_effect_counts']
            or len(compact['branch_evidence_index'])!=len(env['branch_records'])):
        raise ValueError('POST_COMPACTION_CHANGED_SCIENTIFIC_DENOMINATOR')
    v['environment_result_package']=compact
    return v

def validate_rejection(evidence):
    attempt=evidence['attempt'];meta=evidence['meta'];response=evidence['response'];logical=evidence['logical']
    if not (meta.get('http_status')==400 and response.get('error',{}).get('code')=='string_above_max_length'
            and response['error'].get('param')=='input[1].content[0].text'
            and attempt.get('bytes_transmission_state')=='CONFIRMED_SENT'
            and attempt.get('terminal_attempt_status')=='PROVIDER_REJECTED'
            and attempt.get('retry_class')=='NO_RETRY'
            and logical.get('terminal_method_status')=='INFRASTRUCTURE_UNAVAILABLE'
            and attempt.get('logical_call_id')==logical.get('logical_call_id')):
        raise ValueError('EXACT_POST_SIZE_REJECTION_REQUIRED_NO_RESEND')
    return True

def renderer(native,*,source,policy,record):
    def render(*,stage_id,projection,**kwargs):
        if stage_id!='R-POST-PRIMARY-V1':return native(stage_id=stage_id,projection=projection,**kwargs)
        model_view=compact_projection(projection,source)
        bundle=native(stage_id=stage_id,projection=model_view,**kwargs)
        raw=json.dumps(bundle['provider_request'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        if len(raw)>policy['max_provider_request_body_bytes']:
            raise ValueError('REGISTERED_POST_REQUEST_BUDGET_EXCEEDED_NO_SEND')
        record(bundle,model_view,len(raw))
        return bundle
    return render
