from copy import deepcopy

WINDOW_CONTRACT='''
REGISTERED ERROR WINDOW CONTRACT (existing validator semantics):
For each error instance, all four indices must name visible trajectory calls:
relevant_start_call_index <= critical_window_start_call_index <= trigger_call_index <= critical_window_end_call_index.
The critical window must include the trigger of this same error instance. Do not
choose a later escalation window that excludes the stated trigger. Represent
distinct supported errors separately; preserve uncertainty when evidence is
insufficient. Before returning JSON, check this relation for every error instance.
Do not mechanically sort indices, invent an earlier trigger, or discard supported
errors merely to pass validation. Use the existing abstention mechanism if needed.
Keep explanations concise and avoid repeating identical prose; retain every
required evidence reference, supported distinct error and memory boundary.
'''

def amend(bundle,*,global_ceiling,authority_ref,hash_request):
    if bundle['stage_id'] not in ('L-A0','L-A1'):return bundle
    if type(global_ceiling) is not int or global_ceiling<bundle['provider_request']['max_output_tokens']:
        raise ValueError('REGISTERED_OUTPUT_CEILING_INVALID')
    result=deepcopy(bundle);request=result['provider_request']
    request['input'][0]['content'][0]['text']+=WINDOW_CONTRACT
    request['max_output_tokens']=global_ceiling
    result['request_body_sha256']=hash_request(request)
    result['registered_request_amendment']={'schema_id':'REGISTERED_LOCAL_OUTPUT_CONTRACT_AMENDMENT_V1',
        'authority_ref':authority_ref,'base_request_body_sha256':bundle['request_body_sha256'],
        'base_runtime_manifest_sha256':bundle['runtime_manifest_sha256'],
        'base_stage_max_output_tokens':bundle['provider_request']['max_output_tokens'],
        'effective_stage_max_output_tokens':global_ceiling,'ceiling_source':'registered runtime global_max_output_tokens',
        'semantic_validator_unchanged':True,'source_selection_unchanged':True}
    return result
