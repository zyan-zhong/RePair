"""Expose the existing exact-action F1 primitive through H44's dispatch interface."""
from pathlib import Path
import hashlib,json,sys,types
SCHEMA='CURRENT_REGISTERED_EXACT_ACTION_CONTRACT_V1'

def contract_hash(value):
    raw=(json.dumps({k:v for k,v in value.items() if k!='contract_sha256'},sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    return hashlib.sha256(SCHEMA.encode()+b'\0'+raw).hexdigest()

def compile_exact(candidate):
    from pchsi.research_intelligence.human_f0f1_runtime import validate_candidate_content_hash_v1
    candidate=validate_candidate_content_hash_v1(candidate,expected_candidate_sha256=candidate['candidate_sha256'])
    c={'schema_id':SCHEMA,'schema_version':1,'source_state_sha256':candidate['source_state_sha256'],
       'source_candidate_sha256':candidate['candidate_sha256'],'candidate':candidate,
       'intervention_event_role':'REGISTERED_EXACT_ACTION_INTERVENTION','max_intervention_steps':1}
    c['contract_sha256']=contract_hash(c)
    return {'status':'COMPILED','reason':None,'contract':validate_exact(c)}

def validate_exact(c):
    from pchsi.research_intelligence.human_f0f1_runtime import validate_candidate_content_hash_v1
    expected={'schema_id','schema_version','source_state_sha256','source_candidate_sha256','candidate','intervention_event_role','max_intervention_steps','contract_sha256'}
    if set(c)!=expected or c['schema_id']!=SCHEMA or c['schema_version']!=1 or c['contract_sha256']!=contract_hash(c):raise ValueError('EXACT_ACTION_CONTRACT_IDENTITY')
    candidate=validate_candidate_content_hash_v1(c['candidate'],expected_candidate_sha256=c['source_candidate_sha256'])
    if candidate['source_state_sha256']!=c['source_state_sha256'] or candidate.get('candidate_status')!='EXECUTABLE_EXACT_ACTION':raise ValueError('EXACT_ACTION_CANDIDATE_BINDING')
    if c['max_intervention_steps']!=1 or c['intervention_event_role']!='REGISTERED_EXACT_ACTION_INTERVENTION':raise ValueError('EXACT_ACTION_BOUND_CHANGED')
    if not isinstance(candidate.get('exact_action'),str) or not candidate['exact_action'] or candidate.get('option_actions')!=[] or candidate.get('termination_condition') is not None:raise ValueError('EXACT_ACTION_REPRESENTATION_INVALID')
    for field in ['requires_environment_verification','live_menu_revalidation_required','all_intervention_actions_count_against_environment_budget']:
        if candidate.get(field) is not True:raise ValueError('EXACT_ACTION_INVARIANT:'+field)
    return dict(c)

def decide_exact(contract,*,executed_actions,observation,menu,environment_done):
    c=validate_exact(contract);candidate=c['candidate'];executed=list(executed_actions)
    if type(environment_done) is not bool:raise TypeError('environment_done must be bool')
    if executed not in ([],[candidate['exact_action']]):raise ValueError('EXACT_ACTION_EXECUTED_PREFIX_INVALID')
    if environment_done:return {'decision':'STOP','reason':'ENVIRONMENT_DONE'}
    if executed:return {'decision':'STOP','reason':'REGISTERED_EXACT_ACTION_COMPLETE'}
    from pchsi.research_intelligence.human_f0f1_runtime import validate_executable_exact_candidate_v1
    action=validate_executable_exact_candidate_v1(candidate,expected_candidate_sha256=c['source_candidate_sha256'],expected_source_state_sha256=c['source_state_sha256'],live_commands=menu)
    return {'decision':'EXECUTE','action':action,'registered_action_index':0}

def install_dispatch(root,manifest):
    root=Path(root)
    def original(name):
        path=root/(name+'.py');raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=manifest[name+'.py']:raise ValueError('EXACT_ACTION_SOURCE_DRIFT:'+name)
        m=types.ModuleType(name);m.__file__=str(path);return m,raw.decode()
    if 'option_adapter' in sys.modules:raise ValueError('EXACT_ACTION_INSTALL_BEFORE_DISPATCH_IMPORT')
    option,source=original('option_adapter');exec(compile(source,option.__file__,'exec'),option.__dict__)
    compile_old,validate_old,decide_old=option.compile_option,option.validate_contract,option.decide
    option.compile_option=lambda c:compile_exact(c) if c.get('candidate_status')=='EXECUTABLE_EXACT_ACTION' else compile_old(c)
    option.validate_contract=lambda c:validate_exact(c) if c.get('schema_id')==SCHEMA else validate_old(c)
    option.decide=lambda c,**kw:decide_exact(c,**kw) if c.get('schema_id')==SCHEMA else decide_old(c,**kw)
    sys.modules['option_adapter']=option
    branch,source=original('native_branch');old="'REGISTERED_SHORT_OPTION_INTERVENTION'"
    if source.count(old)!=1:raise ValueError('EXACT_ACTION_BRANCH_ROLE_SOURCE_DRIFT')
    source=source.replace(old,"contract.get('intervention_event_role', 'REGISTERED_SHORT_OPTION_INTERVENTION')")
    exec(compile(source,branch.__file__,'exec'),branch.__dict__);sys.modules['native_branch']=branch
    return option
