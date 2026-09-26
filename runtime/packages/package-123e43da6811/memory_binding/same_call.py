"""Typed boundary output in the original local Analyzer call, without new calls."""
from copy import deepcopy

FIELDS = ('activation','continuation','revalidation','release','termination',
          'non_applicability','policy_visible_state_change_trigger')


def extend_local_schema(schema):
    result = deepcopy(schema)
    properties = {key:{'type':'array','items':{'type':'string','minLength':1}}
                  for key in FIELDS}
    properties.update(revalidation_requirement={'type':'string','enum':['REQUIRED','NOT_REQUIRED','UNRESOLVED']},
        non_applicability_disposition={'type':'string','enum':['REGISTERED_CONDITIONS','UNRESOLVED_NO_REGISTERED_CONDITION']})
    boundary = {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    row = {'type':'object','properties':{
        'error_instance_id':{'type':'string','minLength':1},
        'status':{'type':'string','enum':['REGISTERED','UNRESOLVED']},
        'unresolved_reason':{'type':['string','null']},
        'applicability':{'anyOf':[boundary,{'type':'null'}]}},
        'required':['error_instance_id','status','unresolved_reason','applicability'],'additionalProperties':False}
    result['properties']['memory_boundary_registrations']={'type':'array','items':row}
    result['required'].append('memory_boundary_registrations')
    return result


def extend_local_prompt(prompt):
    return prompt + '''\n\nCURRENT FAILURE MEMORY BOUNDARY REGISTRATION (same Analyzer call):
For each error_instances entry provide exactly one memory_boundary_registrations entry.
Use the existing complete trajectory evidence to state general, observable activation,
release or termination, continuation, revalidation, non-applicability and state-change
conditions only when supported. These are registered unverified semantic conditions,
not verifier Benefit/Harm findings. Do not include exact task IDs, hashes, paths or
hidden answers in condition text. Preserve uncertainty: use status UNRESOLVED,
applicability null and an explicit unresolved_reason if supported activation and
release/termination conditions cannot be stated. Never invent generic conditions to
fill required slots. REGISTERED entries require nonempty activation and release or
termination; use explicit UNRESOLVED revalidation/non-applicability dispositions where
applicable. Host code binds origin and source refs to this same response; do not claim
human review, established procedural completeness, causal effect or Memory admission.
Return no extra provider request and leave existing analysis/repair decisions intact.
'''


def validate_boundaries(rows, local_result):
    if not isinstance(rows,list):
        raise ValueError('MEMORY_BOUNDARIES_REQUIRED')
    expected={x['error_instance_id'] for x in local_result['error_instances']}
    if len(rows)!=len(expected) or {x.get('error_instance_id') for x in rows}!=expected:
        raise ValueError('MEMORY_BOUNDARY_ERROR_COVERAGE')
    for row in rows:
        if set(row)!={'error_instance_id','status','unresolved_reason','applicability'}:
            raise ValueError('MEMORY_BOUNDARY_KEYS')
        if row['status']=='UNRESOLVED':
            if row['applicability'] is not None or not isinstance(row['unresolved_reason'],str) or not row['unresolved_reason'].strip():
                raise ValueError('MEMORY_UNRESOLVED_BOUNDARY_REASON')
            continue
        if row['status']!='REGISTERED' or row['unresolved_reason'] is not None:
            raise ValueError('MEMORY_BOUNDARY_STATUS')
        value=row['applicability']
        if not isinstance(value,dict) or set(value)!=set(FIELDS)|{'revalidation_requirement','non_applicability_disposition'}:
            raise ValueError('MEMORY_APPLICABILITY_KEYS')
        for key in FIELDS:
            if not isinstance(value[key],list) or any(not isinstance(x,str) or not x.strip() or any(c in x for c in ('\x00','\r','\n')) for x in value[key]):
                raise ValueError('MEMORY_BOUNDARY_TEXT:' + key)
        if not value['activation'] or not (value['release'] or value['termination']):
            raise ValueError('MEMORY_REQUIRED_BOUNDARIES')
        if value['revalidation_requirement'] not in {'REQUIRED','NOT_REQUIRED','UNRESOLVED'}:
            raise ValueError('MEMORY_REVALIDATION')
        if value['revalidation_requirement']=='REQUIRED' and not value['revalidation']:
            raise ValueError('MEMORY_REVALIDATION_REQUIRED')
        nonapp=value['non_applicability_disposition']
        if nonapp not in {'REGISTERED_CONDITIONS','UNRESOLVED_NO_REGISTERED_CONDITION'} or bool(value['non_applicability'])!=(nonapp=='REGISTERED_CONDITIONS'):
            raise ValueError('MEMORY_NONAPPLICABILITY')
    return rows
