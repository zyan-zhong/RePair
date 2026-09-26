"""Finite public-observation predicates; no natural-language interpretation."""
import hashlib,json,re
from copy import deepcopy
SCHEMA='REGISTERED_PLANNER_TYPED_OPTION_CONTRACT_V1'
KINDS=['MENU_COMMAND_PREFIX','OBSERVATION_ALL_SUBSTRINGS','PUBLIC_TARGET_VISIBLE','PUBLIC_TARGET_CARRIED','PUBLIC_GOAL_COMPLETION']

def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()

def annex_schema():
    text={'type':'string','minLength':1}
    properties={'source_candidate_sha256':text,'source_state_sha256':text,'termination_condition':text,
        'dispatch_mode':{'type':'string','enum':['ORDERED_SEQUENCE']},
        'semantic_coverage':{'type':'string','enum':['FULL','UNREPRESENTABLE']},'coverage_explanation':text,
        'stop_predicates':{'type':'array','items':{'type':'object','additionalProperties':False,
            'properties':{'kind':{'type':'string','enum':KINDS},'arguments':{'type':'array','items':text,'minItems':1}},
            'required':['kind','arguments']}}}
    return {'type':'array','items':{'type':'object','additionalProperties':False,'properties':properties,'required':list(properties)}}

def validate_row(row,candidate):
    import jsonschema
    try:jsonschema.Draft202012Validator(annex_schema()['items']).validate(row)
    except jsonschema.ValidationError as exc:raise ValueError('TYPED_OPTION_ROW_SCHEMA') from exc
    for r,c in [('source_candidate_sha256','candidate_sha256'),('source_state_sha256','source_state_sha256'),('termination_condition','termination_condition')]:
        if row[r]!=candidate[c]:raise ValueError('TYPED_OPTION_FROZEN_CANDIDATE_MISMATCH:'+r)
    if row['semantic_coverage']!='FULL':raise ValueError('TYPED_OPTION_COMPLETE_SEMANTICS_MATERIALIZATION_REQUIRED:'+candidate['candidate_sha256'])
    if candidate['candidate_status']!='EXECUTABLE_SHORT_OPTION' or not candidate['option_actions']:raise ValueError('TYPED_OPTION_CANDIDATE_KIND')
    if any(candidate.get(k) is not True for k in ['live_menu_revalidation_required','all_intervention_actions_count_against_environment_budget']):raise ValueError('TYPED_OPTION_NATIVE_INVARIANT')
    for p in row['stop_predicates']:
        if p['kind']!='OBSERVATION_ALL_SUBSTRINGS' and len(p['arguments'])!=1:raise ValueError('TYPED_OPTION_PREDICATE_ARITY')
        if not all(x.strip() for x in p['arguments']):raise ValueError('TYPED_OPTION_EMPTY_PREDICATE')
        if p['kind']=='MENU_COMMAND_PREFIX' and not p['arguments'][0].endswith(' '):raise ValueError('TYPED_MENU_PREFIX_TOKEN_BOUNDARY_REQUIRED')
        if p['kind'].startswith('PUBLIC_TARGET') and not re.fullmatch('[a-z][a-z0-9_]*',p['arguments'][0]):raise ValueError('TYPED_PUBLIC_TARGET_TYPE')
    return row

def validate_annex(rows,candidates):
    selected={c['candidate_sha256']:c for c in candidates if c['candidate_status']=='EXECUTABLE_SHORT_OPTION'}
    if len(rows)!=len(selected) or {r['source_candidate_sha256'] for r in rows}!=set(selected):raise ValueError('TYPED_OPTION_SELECTED_PORTFOLIO_INCOMPLETE')
    for r in rows:validate_row(r,selected[r['source_candidate_sha256']])
    return rows

def bind_contract(candidate,row,registration_ref):
    validate_row(row,candidate)
    c={'schema_id':SCHEMA,'source_state_sha256':candidate['source_state_sha256'],
        'source_candidate_sha256':candidate['candidate_sha256'],'source_termination_condition':candidate['termination_condition'],
        'source_termination_condition_sha256':hashlib.sha256(candidate['termination_condition'].encode()).hexdigest(),
        'option_actions':list(candidate['option_actions']),'dispatch_mode':'ORDERED_SEQUENCE','max_intervention_steps':len(candidate['option_actions']),
        'stop_predicates':deepcopy(row['stop_predicates']),'registration_ref':deepcopy(registration_ref),
        'all_intervention_actions_count_against_environment_budget':True,'live_menu_revalidation_required_each_step':True,
        'stop_environment_done':True,'stop_next_action_not_admissible':True,'stop_actions_exhausted':True,
        'return_control_to_frozen_policy_after_option':True,'free_text_runtime_interpretation_allowed':False,
        'legacy_free_text_semantic_coverage':'FULL','coverage_explanation':row['coverage_explanation']}
    c['contract_sha256']=digest(c);return c

def validate_contract(c):
    if c.get('schema_id')!=SCHEMA or c.get('contract_sha256')!=digest({k:v for k,v in c.items() if k!='contract_sha256'}):raise ValueError('TYPED_OPTION_CONTRACT_SHA')
    if c['dispatch_mode']!='ORDERED_SEQUENCE' or not c['option_actions'] or c['max_intervention_steps']!=len(c['option_actions']):raise ValueError('TYPED_OPTION_SEQUENCE_CHANGED')
    for key in ['all_intervention_actions_count_against_environment_budget','live_menu_revalidation_required_each_step','stop_environment_done','stop_next_action_not_admissible','stop_actions_exhausted','return_control_to_frozen_policy_after_option']:
        if c[key] is not True:raise ValueError('TYPED_OPTION_INVARIANT:'+key)
    if c['free_text_runtime_interpretation_allowed'] is not False:raise ValueError('FREE_TEXT_EXECUTION_FORBIDDEN')
    return c

def decide(c,*,executed_actions,observation,menu,environment_done):
    c=validate_contract(c);executed=list(executed_actions);actions=c['option_actions']
    if type(environment_done) is not bool or executed!=actions[:len(executed)] or len(executed)>len(actions):raise ValueError('TYPED_OPTION_EXECUTED_PREFIX')
    if environment_done:return {'decision':'STOP','reason':'ENVIRONMENT_DONE'}
    public='\n'.join(line for line in observation.splitlines() if not line.strip().lower().startswith(('your task is','task:','goal:'))).casefold()
    for p in c['stop_predicates']:
        kind=p['kind'];args=p['arguments'];hit=False
        if kind=='MENU_COMMAND_PREFIX':hit=any(x.casefold().startswith(args[0].casefold()) for x in menu)
        elif kind=='OBSERVATION_ALL_SUBSTRINGS':hit=all(x.casefold() in public for x in args)
        elif kind=='PUBLIC_TARGET_VISIBLE':
            from option_adapter import _positive_visible_object
            hit=_positive_visible_object(public,args[0])
        elif kind=='PUBLIC_TARGET_CARRIED':
            from option_adapter import _carried
            hit=_carried(menu,public,args[0])
        elif kind=='PUBLIC_GOAL_COMPLETION':pass # Uses the mandatory public environment-done boundary, never reward/won.
        if hit:return {'decision':'STOP','reason':'REGISTERED_'+kind}
    if len(executed)==len(actions):return {'decision':'STOP','reason':'REGISTERED_ACTIONS_EXHAUSTED'}
    if actions[len(executed)] not in menu:return {'decision':'STOP','reason':'NEXT_REGISTERED_ACTION_NOT_ADMISSIBLE'}
    return {'decision':'EXECUTE','action':actions[len(executed)],'registered_action_index':len(executed)}

def install_dispatch(option,rows=None,registration_ref=None):
    if getattr(option,'_typed_registry_installed',False):
        if rows is not None:option._typed_registry={r['source_candidate_sha256']:r for r in rows};option._typed_ref=registration_ref
        return
    native_compile,native_validate,native_decide=option.compile_option,option.validate_contract,option.decide
    option._typed_registry={r['source_candidate_sha256']:r for r in rows or []};option._typed_ref=registration_ref
    def compile_option(candidate):
        if candidate['candidate_status']=='EXECUTABLE_SHORT_OPTION' and candidate['candidate_sha256'] in option._typed_registry:
            from pchsi.research_intelligence.human_f0f1_runtime import validate_candidate_content_hash_v1
            validate_candidate_content_hash_v1(candidate,expected_candidate_sha256=candidate['candidate_sha256'])
            contract=bind_contract(candidate,option._typed_registry[candidate['candidate_sha256']],option._typed_ref)
            return {'status':'COMPILED','reason':None,'contract':contract}
        return native_compile(candidate)
    option.compile_option=compile_option
    option.validate_contract=lambda c:validate_contract(c) if c.get('schema_id')==SCHEMA else native_validate(c)
    option.decide=lambda c,**kwargs:decide(c,**kwargs) if c.get('schema_id')==SCHEMA else native_decide(c,**kwargs)
    option._typed_registry_installed=True
