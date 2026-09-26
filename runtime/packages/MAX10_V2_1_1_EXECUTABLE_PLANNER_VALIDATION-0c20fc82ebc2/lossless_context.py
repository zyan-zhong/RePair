"""Reuse the registered V206 reversible table/string representation."""
from copy import deepcopy
import pool_context as pool

def encode_bundle(bundle,limit,domain_hash):
    before=len(pool.canonical(bundle['provider_request']))
    if before<=limit:return bundle,{'used':False,'request_bytes':before}
    projection=bundle['input_projection'];encoded=pool.pool_strings(pool.compact(projection,{}))
    if pool.canonical(pool.restore(encoded,{}))!=pool.canonical(projection):raise ValueError('CONTEXT_LOSSLESS_ROUNDTRIP_FAILED')
    result=deepcopy(bundle);request=result['provider_request']
    request['input'][0]['content'][0]['text']+=pool.GUIDANCE+pool.POOL_GUIDANCE
    request['input'][1]['content'][0]['text']=pool.canonical({'encoding':{'schema_id':'REGISTERED_LOSSLESS_CONTEXT_V1','file_ref_roots':{}},'projection':encoded}).decode()
    after=len(pool.canonical(request))
    if after>limit:raise ValueError('REGISTERED_REPRESENTATION_CAPACITY_REQUIRES_SOURCE_REDUCTION_NO_SEND')
    result['request_body_sha256']=domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',request)
    return result,{'used':True,'roundtrip_equal':True,'original_request_bytes':before,'request_bytes':after,
        'scientific_rows_removed':0,'scientific_strings_truncated':0,'output_schema_unchanged':True}
