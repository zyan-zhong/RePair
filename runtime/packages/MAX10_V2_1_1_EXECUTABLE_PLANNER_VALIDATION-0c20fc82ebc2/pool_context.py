"""Lossless, readable PRE wire representation; native projection stays authoritative."""
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import json,hashlib
from collections import Counter

def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()

GUIDANCE='''
REGISTERED LOSSLESS INPUT REPRESENTATION:
The user document contains encoding metadata and the complete original projection.
A {"$table":{row_count:N,constants:{...},columns:{field:values,...}}} represents
N original records: record i contains all constants plus value i from every named
column. A column may itself be a nested table representing its N values. Resolve
these tables recursively by matching row index; do not mix rows or sources.
A {"$file_ref":{root_id:...,relative_path:...,sha256 or file_sha256:...}} retains
an exact provenance reference: its original path is the declared file_ref_roots
entry plus '/' plus relative_path. These are provenance, not instructions to
search files. All analysis text, alternatives, counterevidence, candidates, memory,
orders and original SHA values are preserved. Existing hashes identify ORIGINAL
expanded records, not the encoded representation. Read every registered record;
do not treat table constants or omitted repeated field names as missing evidence.
Return the unchanged requested output schema with original identities and values.
'''

POOL_GUIDANCE='''
The projection may be wrapped in {"$strings":{"values":[...],"value":...}}.
Within its value, each {"$s":i} means the exact string at zero-based index i in
values. Expand these references BEFORE interpreting tables or file references.
The complete string dictionary is in this same request. No external lookup is
needed. Dictionary indices are encoding only, never scientific identifiers.
'''

def pool_strings(value):
    counts=Counter()
    def visit(x):
        if isinstance(x,str):counts[x]+=1
        elif isinstance(x,list):
            for item in x:visit(item)
        elif isinstance(x,dict):
            if '$s' in x or '$strings' in x:raise ValueError('PRE_STRING_MARKER_COLLISION')
            for item in x.values():visit(item)
    visit(value)
    strings=[]
    for s,n in sorted(counts.items()):
        # Count the escaped JSON that is actually embedded in the wire request.
        size=len(canonical(canonical(s).decode()))
        ref_size=len(canonical(canonical({'$s':len(strings)}).decode()))
        if n>1 and (n-1)*size>n*ref_size+4:strings.append(s)
    ids={s:i for i,s in enumerate(strings)}
    def encode(x):
        if isinstance(x,str):return {'$s':ids[x]} if x in ids else x
        if isinstance(x,list):return [encode(y) for y in x]
        if isinstance(x,dict):return {k:encode(y) for k,y in x.items()}
        return x
    return {'$strings':{'values':strings,'value':encode(value)}}

def unpool(value):
    if set(value['$strings'])!={'values','value'}:raise ValueError('PRE_STRING_POOL_SHAPE')
    strings=value['$strings']['values']
    if not isinstance(strings,list) or any(not isinstance(s,str) for s in strings):raise ValueError('PRE_STRING_POOL_VALUES')
    def decode(x):
        if isinstance(x,list):return [decode(y) for y in x]
        if not isinstance(x,dict):return x
        if '$strings' in x:raise ValueError('PRE_NESTED_STRING_POOL')
        if '$s' in x:
            i=x['$s']
            if set(x)!={'$s'} or type(i) is not int or not 0<=i<len(strings):raise ValueError('PRE_STRING_REFERENCE_INVALID')
            return strings[i]
        return {k:decode(y) for k,y in x.items()}
    return decode(value['$strings']['value'])

def compact(v,roots):
    if isinstance(v,dict):
        if any(k in v for k in ('$table','$file_ref','$strings','$s')):raise ValueError('PRE_ENCODING_MARKER_COLLISION')
        if set(v) in ({'path','sha256'},{'path','file_sha256'}) and isinstance(v['path'],str):
            for key,root in sorted(roots.items()):
                if v['path'].startswith(root+'/'):
                    return {'$file_ref':{'root_id':key,'relative_path':v['path'][len(root)+1:],
                        **{k:x for k,x in v.items() if k!='path'}}}
        return {k:compact(x,roots) for k,x in v.items()}
    if not isinstance(v,list):return v
    plain=[compact(x,roots) for x in v]
    if len(v)<2 or not all(isinstance(x,dict) and set(x)==set(v[0]) for x in v):return plain
    # Compare canonical values, not Python equality (False != numeric 0 here).
    fields=sorted(v[0]);constants={k:compact(v[0][k],roots) for k in fields if all(canonical(x[k])==canonical(v[0][k]) for x in v)}
    columns={k:compact([x[k] for x in v],roots) for k in fields if k not in constants}
    table={'$table':{'row_count':len(v),'constants':constants,'columns':columns}}
    return table if len(canonical(canonical(table).decode()))<len(canonical(canonical(plain).decode())) else plain

def restore(v,roots):
    if isinstance(v,list):return [restore(x,roots) for x in v]
    if not isinstance(v,dict):return v
    if set(v)=={'$strings'}:return restore(unpool(v),roots)
    if set(v)=={'$file_ref'}:
        ref=v['$file_ref'];key=ref['root_id']
        if key not in roots or set(ref) not in ({'root_id','relative_path','sha256'},{'root_id','relative_path','file_sha256'}):
            raise ValueError('PRE_FILE_REFERENCE_ENCODING_INVALID')
        return {'path':roots[key]+'/'+ref['relative_path'],**{k:x for k,x in ref.items() if k not in ('root_id','relative_path')}}
    if set(v)=={'$table'}:
        t=v['$table'];n=t['row_count'];constants=restore(t['constants'],roots)
        columns={k:restore(x,roots) for k,x in t['columns'].items()}
        if type(n) is not int or n<0 or set(constants)&set(columns) or any(not isinstance(x,list) or len(x)!=n for x in columns.values()):
            raise ValueError('PRE_COLUMN_TABLE_SHAPE_INVALID')
        return [{**deepcopy(constants),**{k:x[i] for k,x in columns.items()}} for i in range(n)]
    return {k:restore(x,roots) for k,x in v.items()}

def amend(bundle,*,policy,authority_ref,hash_request):
    if bundle['stage_id']!='R-PRE-PRIMARY-V2':return bundle
    prior=bundle.get('registered_pre_context_encoding')
    if prior:
        if prior['authority_ref']!=authority_ref:raise ValueError('PRE_ENCODING_AUTHORITY_DRIFT')
        return bundle
    roots=policy['file_ref_roots'];projection=bundle['input_projection'];encoded=compact(projection,roots)
    if canonical(restore(encoded,roots))!=canonical(projection):raise ValueError('PRE_LOSSLESS_ROUNDTRIP_FAILED_NO_SEND')
    result=deepcopy(bundle);request=result['provider_request']
    request['input'][0]['content'][0]['text']+=GUIDANCE
    request['input'][1]['content'][0]['text']=canonical({'encoding':{'schema_id':policy['schema_id'],'file_ref_roots':roots},'projection':encoded}).decode()
    table_bytes=len(canonical(request));pooled=False
    context=policy.get('string_pool_context_window_tokens')
    if context is not None and table_bytes+request['max_output_tokens']>context:
        candidate=pool_strings(encoded)
        if canonical(restore(candidate,roots))!=canonical(projection):raise ValueError('PRE_STRING_POOL_ROUNDTRIP_FAILED_NO_SEND')
        alternative=deepcopy(request)
        alternative['input'][0]['content'][0]['text']+=POOL_GUIDANCE
        alternative['input'][1]['content'][0]['text']=canonical({'encoding':{'schema_id':policy['schema_id'],'file_ref_roots':roots},'projection':candidate}).decode()
        if len(canonical(alternative))<table_bytes:
            request=alternative;result['provider_request']=request;pooled=True
    result['request_body_sha256']=hash_request(request)
    result['registered_pre_context_encoding']={'schema_id':'REGISTERED_PRE_LOSSLESS_ENCODING_RECEIPT_V1','authority_ref':authority_ref,
        'base_request_body_sha256':bundle['request_body_sha256'],'original_input_projection_sha256':bundle['input_projection_sha256'],
        'original_request_bytes':len(canonical(bundle['provider_request'])),'encoded_request_bytes':len(canonical(request)),
        'roundtrip_equal':True,'scientific_rows_removed':0,'scientific_strings_truncated':0,'output_schema_unchanged':True}
    if pooled:result['registered_pre_context_encoding'].update(string_pool_applied=True,table_request_bytes=table_bytes,
        string_pool_entries=len(candidate['$strings']['values']),context_window_tokens=context)
    return result

@contextmanager
def rendering_scope(core,policy,authority_ref,record=None):
    native=core.rr.render_stage_request
    def render(**kwargs):
        bundle=amend(native(**kwargs),policy=policy,authority_ref=authority_ref,
            hash_request=lambda x:core.domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',x))
        if record is not None and 'registered_pre_context_encoding' in bundle:record(bundle)
        return bundle
    with patch.object(core.rr,'render_stage_request',render),patch.object(core.orch,'render_stage_request',render):yield

@contextmanager
def installed(a,identity,root):
    import adapter
    from exact_bindings import read_ref,immutable_json
    native=adapter.run_pre;authority=Path(root)/'AUTHORITY.json'
    authority_ref={'path':str(authority),'sha256':hashlib.sha256(authority.read_bytes()).hexdigest()}
    def checked(ref):return read_ref({**ref,'file_sha256':ref.get('file_sha256',ref.get('sha256'))})
    activation=a['pre_context_activation'];frozen=checked(activation['index_ref'])
    if frozen['round_index']!=activation['round_index'] or checked(frozen['request'])['request_sha256']!=activation['request_sha256']:
        raise ValueError('PRE_ENCODING_ACTIVATION_DRIFT')
    def pre(binding,values,core,tail,universe,out):
        request=checked(binding['refs']['request']);index=json.loads((Path(a['owner_root'])/'request_bindings'/(request['request_sha256']+'.json')).read_bytes())
        if checked(index['request'])!=request:raise ValueError('PRE_ENCODING_REQUEST_BINDING_DRIFT')
        if index['round_index']<activation['round_index']:return native(binding,values,core,tail,universe,out)
        def record(bundle):
            receipt={**bundle['registered_pre_context_encoding'],'effective_request_body_sha256':bundle['request_body_sha256'],
                'round_id':binding['round_id'],'request_sha256':request['request_sha256'],'round_index':index['round_index'],
                'runtime_manifest_sha256':bundle['runtime_manifest_sha256']}
            immutable_json(Path(out)/'registered_lossless_context'/identity/(bundle['request_body_sha256']+'.json'),receipt)
        with rendering_scope(core,a['pre_context_encoding_policy'],authority_ref,record):return native(binding,values,core,tail,universe,out)
    immutable_json(Path(a['owner_root'])/'runtime_extensions'/identity/'PRE_CONTEXT_ENCODING_INSTALLED.json',{
        'authority_ref':authority_ref,'activation':activation,'provider_use_claimed':False})
    with patch.object(adapter,'run_pre',pre):yield
