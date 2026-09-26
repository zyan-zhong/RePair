from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def method_failure(result):
    """Persisted method error is identical for the first return and cache reuse."""
    path=Path(result['call_dir'])/'validation_error.json'
    if path.is_file():
        error=json.loads(path.read_bytes())
        if error.get('error_type') and error.get('message'):
            return error['error_type']+':'+error['message']
    return result.get('method_failure_reason') or 'OUTPUT_DID_NOT_PASS_NATIVE_VALIDATION'

def compatible_bundle(bundle, projection, attempt, failure, contract, domain_hash):
    if type(attempt) is not int or not 1<=attempt<=contract['new_method_attempt_limit']:
        raise ValueError('REVIEW_METHOD_ATTEMPT_LIMIT')
    result=deepcopy(bundle);request=result['provider_request']
    schema=request['text']['format']['schema']
    identities=[{'packet_id':i['packet_id'],'fragment_id':i['fragment_id'],
        'plan_conditions':list(i['original_candidate_pair'].keys() & {'A2','A3'}) if i['original_candidate_pair'] else []}
        for i in projection['items']]
    for row in identities:row['plan_conditions'].sort()
    instruction='''\nREGISTERED JSON SERIALIZATION CONTRACT:
Return exactly one complete JSON object, no markdown, no comments, no padding.
The root has only the key "reviews". Return exactly one review per listed input
fragment, exactly once. Return only the listed plan conditions for each fragment.
Keep complete concise sentences, uncertainty, task-level and intermediate strategy,
and all necessary public phases; do not pad fields to their length ceilings.
Do not repeat equivalent fields or duplicate reviews. Stop after the final }.
Use MENU_COMMAND_PREFIX only for a token-boundary prefix ending in a space.
For an EXACT command do not repeat the whole command as a prefix predicate.
No truncated JSON or missing required fields will be accepted. All original
source, goal, candidate, initial-action and public-program validators still apply.
The scientific evidence is unchanged. This is an output-format recovery only.
'''
    instruction+='Expected output identities: '+canonical(identities).decode()+'\n'
    instruction+='Required JSON schema (validated locally without relaxation): '+json.dumps(schema,sort_keys=True,separators=(',',':'))+'\n'
    instruction+='Registered format attempt: '+str(attempt)+'\n'
    if failure:instruction+='Previous format failure: '+str(failure)+'\nRegenerate the complete JSON from the same original evidence.\n'
    request['input'][0]['content'][0]['text']+=instruction
    request['text']['format']={'type':'json_object'}
    if len(canonical(request))+request['max_output_tokens']>contract['context_window_tokens']:
        raise ValueError('REVIEW_METHOD_WIRE_CAPACITY')
    result['request_body_sha256']=domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',request)
    result['registered_review_serialization']={'contract':contract,'attempt':attempt,
        'original_request_sha256':bundle.get('request_body_sha256'),'scientific_input_unchanged':True,
        'native_output_schema_unchanged':True,'provider_format_changed':'json_schema_to_json_object'}
    return result

def complete_review(text, projection, schema):
    import jsonschema
    from strategy_planner import validate_review
    from review_representation import normalize,group_context_reviews
    value=json.loads(text);jsonschema.Draft202012Validator(schema).validate(value)
    expected={i['fragment_id']:i for i in projection['items']}
    if len(value['reviews'])!=len(expected) or {r['fragment_id'] for r in value['reviews']}!=set(expected):
        return group_context_reviews(value,projection['items'],schema)
    reviews=[];changes=[]
    for row in value['reviews']:
        item=expected[row['fragment_id']];current,delta=normalize(row)
        validate_review(current,packet_id=item['packet_id'],context=item['exact_source_context'],pair=item['original_candidate_pair'])
        reviews.append(current);changes.extend(delta)
    result={**value,'reviews':reviews};jsonschema.Draft202012Validator(schema).validate(result)
    return result,changes

def execute_review(native,options,core,contract,implementation_ref,trace_path):
    """Exact cache adoption; bounded changed-format calls through the native U API."""
    from exact_bindings import immutable_json,file_ref,read_json
    renderer=options['api']['render_stage_request']
    bundle=renderer(stage_id=options['stage_id'],projection=options['projection'])
    identity={k:options[k] for k in ['unit_identity','stage_id','condition_id','round_id','policy_version','domain_hash']}
    old_id=core.u.expected_logical_call_id(**identity,request_body_sha256=bundle['request_body_sha256'])
    original=Path(options['runtime_root'])/old_id;old=None
    if original.exists() or original.is_symlink():
        old=native(**options)
        if old['status']!='SEMANTIC_INVALID' or old.get('hard_stop'):return old
    schema=bundle['provider_request']['text']['format']['schema']
    contract_sha=core.domain_hash(contract['schema_id'],contract)
    root=Path(options['runtime_root']).parent/'registered_review_boundary'/contract_sha
    immutable_json(root/'BOUNDARY_CONTRACT.json',{'contract':contract,'implementation_ref':implementation_ref})
    previous_failure=None
    for attempt in range(1,contract['new_method_attempt_limit']+1):
        def render(**kw):
            base=renderer(**kw)
            return compatible_bundle(base,kw['projection'],attempt,previous_failure,contract,core.domain_hash)
        def validate(*,stage_id,text,raw_response_sha256,projection):
            value,changes=complete_review(text,projection,schema)
            value={**value,'representation_validation':{'schema_id':'STRICT_LOCAL_SOURCE_REVIEW_VALIDATION_V1',
                'raw_response_sha256':raw_response_sha256,'normalization_changes':changes,
                'contract_ref':file_ref(root/'BOUNDARY_CONTRACT.json')}}
            return {**value,'review_sha256':core.domain_hash('REGISTERED_STRATEGY_SOURCE_REVIEWS_V1',value)}
        effective=render(stage_id=options['stage_id'],projection=options['projection'])
        call_id=core.u.expected_logical_call_id(**identity,request_body_sha256=effective['request_body_sha256'])
        immutable_json(root/'bindings'/(call_id+'.json'),{'original_request_sha256':bundle['request_body_sha256'],
            'original_call_ref':file_ref(original/'logical_call.json') if old else None,
            'effective_request_sha256':effective['request_body_sha256'],'attempt':attempt,
            'input_projection_unchanged':True,'provider_output_budget_unchanged':True,
            'schema_ref':file_ref(Path(options['runtime_root']).parent/'REVIEW_SCHEMA.json'),
            'contract_ref':file_ref(root/'BOUNDARY_CONTRACT.json')})
        api={**options['api'],'render_stage_request':render}
        with patch.object(core.orch,'render_stage_request',render),patch.object(core.orch,'validate_stage_output',validate):
            result=native(**{**options,'runtime_root':root/'calls','api':api})
        with Path(trace_path).open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'old_logical_call_id':old_id,'attempt':attempt,'result':result,
                'binding_ref':file_ref(root/'bindings'/(call_id+'.json'))})+'\n')
        if result['status']!='SEMANTIC_INVALID' or result.get('hard_stop'):return result
        previous_failure=method_failure(result)
    return result
