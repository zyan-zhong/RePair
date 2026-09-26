"""Independent preregistered process and efficiency sidecars; no training gate."""
from pathlib import Path
from collections import Counter
import hashlib,json
from goal_metric import from_game,completion,state_facts

METRIC='PAIRED_TERMINAL_DYNAMIC_GOAL_VECTOR_DOMINANCE_V1'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(Path(p).read_bytes())}
def read(r):
    raw=Path(r['path']).read_bytes()
    if sha(raw)!=r.get('sha256',r.get('file_sha256')):raise ValueError('PROCESS_SOURCE_CHANGED')
    return json.loads(raw)
def write(p,v):
    p=Path(p);raw=canonical(v)+b'\n';p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        if p.read_bytes()!=raw:raise ValueError('PROCESS_IMMUTABLE_CONFLICT')
    else:
        with p.open('xb') as stream:stream.write(raw)
    return ref(p)

def goal_vector(spec,facts):
    return [[[(p,tuple(args)) in facts if not neg else (p,tuple(args)) not in facts for p,args,neg in alt]
             for alt in group['alternatives']] for group in spec['groups']]

def process_label(f0,f1):
    if f0 is None or f1 is None:return 'PU'
    shape=lambda v:[[len(a) for a in group] for group in v]
    if shape(f0)!=shape(f1):return 'PU'
    a=[x for g in f0 for alt in g for x in alt];b=[x for g in f1 for alt in g for x in alt]
    if not a or any(type(v) is not bool for v in a+b):return 'PU'
    better=any(y>x for x,y in zip(a,b));worse=any(y<x for x,y in zip(a,b))
    return 'PU' if better and worse else 'P+' if better else 'P-' if worse else 'P0'

def efficiency(branch):
    steps=branch['environment_transitions_from_source'];calls=branch['policy_calls']
    repeats=sum(a['action']==b['action'] for a,b in zip(steps,steps[1:]))
    nochange=sum(s['pre_observation']==s['resulting_observation'] and s['pre_menu']==s['resulting_menu'] for s in steps)
    states=[sha(canonical([s['resulting_observation'],s['resulting_menu']])) for s in steps]
    result={'environment_steps':len(steps),'policy_calls':len(calls),'consecutive_repeated_actions':repeats,
        'no_public_change_actions':nochange,'public_state_revisits':len(states)-len(set(states)),
        'remaining_environment_budget':branch['strategy_execution']['budget_limits']['max_environment_steps']-branch['final_budget']['environment_step_count']}
    # Wire-provenance counts, when present, are measurements, not price estimates.
    for name in ['prompt_tokens','completion_tokens']:
        values=[c['policy_call'].get(name) for c in calls]
        result[name]=sum(values) if all(type(v) is int for v in values) else None
    return result

def register(plan,run_root,implementation_ref):
    rows={}
    for item in plan['branch_bindings']:
        b=item['binding'];state=b['source_state_sha256']
        if state in rows:continue
        source_ref={'path':b['replay_source_path'],'sha256':b['replay_source_file_sha256']};source=read(source_ref)
        game_ref={'path':source['exact_gamefile'],'sha256':source['source_gamefile_sha256']}
        game=read(game_ref)
        try:
            spec=from_game(game);row={'status':'REGISTERED','goal_spec':spec,'goal_spec_sha256':sha(canonical(spec))}
        except ValueError as exc:row={'status':'UNSUPPORTED_GOAL_SPEC','reason':str(exc)}
        rows[state]={**row,'source_ref':source_ref,'game_ref':game_ref}
    value={'schema_id':'PREREGISTERED_CAUSAL_PROCESS_METRIC_V1','metric_id':METRIC,'states':rows,
        'implementation_ref':implementation_ref,'endpoint':'native branch terminal under unchanged budget',
        'comparison':'strict pointwise dominance over all preregistered grounded goal alternatives; mixed=PU',
        'milestones_scope':'native dynamic terminal goal predicates only; other intermediate milestones not claimed',
        'registered_before_branch_submission':True,'primary_terminal_classifier_changed':False,
        'private_facts_visible_to_policy_or_pre':False,'progress_training_authorized':False}
    return write(Path(run_root)/'PROCESS_METRIC_REGISTRATION.json',value)

def progress_worker(connection,create_request_bytes,*,capture_path,registration_ref,source_state,branch_key):
    """V193 private observer extended to the full step sequence; messages pass intact."""
    registration=read(registration_ref);row=registration['states'][source_state]
    read(registration['implementation_ref']);game=read(row['game_ref']);spec=row['goal_spec']
    from pchsi.evaluation.alfworld_worker import real_alfworld_worker_main
    from pchsi.evaluation.alfworld_worker_protocol import worker_message_from_bytes,ResetResult,StepResult,WorkerTerminalStatus,WorkerFailure
    from textworld.envs.pddl.pddl import PddlEnv
    from unittest.mock import patch
    create=worker_message_from_bytes(create_request_bytes)
    if create.exact_gamefile!=row['game_ref']['path']:raise ValueError('PROCESS_WORKER_GAME_IDENTITY')
    relevant={(p,tuple(args)) for g in spec['groups'] for alt in g['alternatives'] for p,args,neg in alt}
    snapshot={};records=[];closed=False;failure=None;gather=PddlEnv._gather_infos
    def observe(env):
        nonlocal failure
        gather(env)
        try:
            if env.request_infos.policy_commands or env.request_infos.intermediate_reward or 'walkthrough' in env.request_infos.extras:raise ValueError('PROCESS_ORACLE_INFO_REQUESTED')
            facts=state_facts(env._pddl_state)&relevant;n,d=completion(spec,facts)
            if (n==d)!=bool(env.state['won']):raise ValueError('PROCESS_NATIVE_GOAL_CONFLICT')
            snapshot.clear();snapshot.update(goal_vector=goal_vector(spec,facts),facts=sorted((p,list(a)) for p,a in facts),
                completed_goal_predicates=n,total_goal_predicates=d,native_won=bool(env.state['won']))
        except Exception as exc:
            # A secondary measurement failure cannot fabricate a primary label.
            failure=type(exc).__name__+':'+str(exc);snapshot.clear()
    class Connection:
        def recv_bytes(self):return connection.recv_bytes()
        def close(self):return connection.close()
        def send_bytes(self,raw):
            nonlocal closed,failure
            msg=worker_message_from_bytes(raw)
            if isinstance(msg,(ResetResult,StepResult)):
                records.append({'environment_step_count':0 if isinstance(msg,ResetResult) else len(records),
                    'observation_sha256':sha(msg.observation.encode()),**snapshot})
            if isinstance(msg,WorkerTerminalStatus):closed=msg.status=='CLOSED'
            if isinstance(msg,WorkerFailure):failure='PUBLIC_WORKER_FAILURE'
            connection.send_bytes(raw)
    with patch.object(PddlEnv,'_gather_infos',observe):real_alfworld_worker_main(Connection(),create_request_bytes)
    write(capture_path,{'schema_id':'RESTRICTED_CAUSAL_GOAL_TRACE_V1','registration_ref':registration_ref,
        'source_state_sha256':source_state,'branch_key_sha256':branch_key,'records':records,
        'complete':closed and failure is None,'failure':failure,'public_protocol_unchanged':True})

def install_branch_observer(module,registration_ref):
    from functools import partial
    from unittest.mock import patch
    from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
    registration=read(registration_ref);native=module._execute_locked
    def execute(binding,output_dir,**kw):
        capture=Path(output_dir)/'restricted_progress/TRACE.json';row=registration['states'][binding['source_state_sha256']]
        original_start=SpawnedAlfworldAdapter.start;original_put=module.put_json
        def start(**options):return original_start(**options,worker_target=partial(progress_worker,
            capture_path=str(capture),registration_ref=registration_ref,source_state=binding['source_state_sha256'],branch_key=binding['branch_key_sha256']))
        def put(path,value):
            if Path(path).name=='BRANCH_TERMINAL.json':
                value['process_capture_ref']=ref(capture) if capture.is_file() else None
                value['process_registration_ref']=registration_ref
                value['evidence_sha256']=module.sha(module.canonical({k:v for k,v in value.items() if k!='evidence_sha256'}))
            return original_put(path,value)
        with patch.object(module,'put_json',put):
            if row['status']=='REGISTERED':
                with patch.object(SpawnedAlfworldAdapter,'start',start):return native(binding,output_dir,**kw)
            return native(binding,output_dir,**kw)
    module._execute_locked=execute
    return lambda:setattr(module,'_execute_locked',native)

def validated_vectors(branch,registration_ref):
    if branch.get('process_registration_ref')!=registration_ref:return None
    capture_ref=branch.get('process_capture_ref')
    if capture_ref is None:return None
    trace=read(capture_ref);reg=read(registration_ref);state=branch['source_state_sha256'];spec=reg['states'][state].get('goal_spec')
    if not trace['complete'] or spec is None:return None
    if trace['branch_key_sha256']!=branch['branch_key_sha256'] or trace['source_state_sha256']!=state or trace['registration_ref']!=registration_ref:raise ValueError('PROCESS_TRACE_IDENTITY')
    records=trace['records'];source=branch['strategy_execution'];index=source['source_budget']['environment_step_count']
    steps=branch['environment_transitions_from_source']
    if len(records)!=branch['final_budget']['environment_step_count']+1:raise ValueError('PROCESS_TRACE_POPULATION')
    if records[index]['observation_sha256']!=sha(source['source_observation'].encode()):raise ValueError('PROCESS_SOURCE_OBSERVATION')
    for offset,step in enumerate(steps,1):
        if records[index+offset]['observation_sha256']!=step['resulting_observation_sha256']:raise ValueError('PROCESS_STEP_OBSERVATION')
    for i,record in enumerate(records):
        if record['environment_step_count']!=i:raise ValueError('PROCESS_STEP_INDEX')
        facts={(p,tuple(args)) for p,args in record['facts']}
        if goal_vector(spec,facts)!=record['goal_vector'] or completion(spec,facts)!=(record['completed_goal_predicates'],record['total_goal_predicates']):raise ValueError('PROCESS_VECTOR_RECOMPUTATION')
    if records[-1]['native_won']!=branch['terminal_success']:raise ValueError('PROCESS_TERMINAL_PARITY')
    return {'source':records[index]['goal_vector'],'terminal':records[-1]['goal_vector'],
        'completed_goal_predicates':records[-1]['completed_goal_predicates'],'capture_ref':capture_ref}

def summarize(plan,verifier,run_root):
    registration_ref=plan['process_metric_registration_ref'];read(registration_ref)
    branches={b['evidence_sha256']:b for b in verifier['branch_records']};rows=[];pool=[]
    for pair in verifier['pair_results']:
        if not pair['complete']:continue
        f0=branches[pair['f0_evidence_sha256']];f1=branches[pair['f1_evidence_sha256']]
        v0=validated_vectors(f0,registration_ref);v1=validated_vectors(f1,registration_ref)
        label=process_label(v0['terminal'],v1['terminal']) if v0 and v1 and v0['source']==v1['source'] else 'PU'
        e0=efficiency(f0);e1=efficiency(f1)
        delta={k:e1[k]-e0[k] if e0[k] is not None and e1[k] is not None else None for k in e0}
        row={'source_state_sha256':pair['source_state_sha256'],'replicate_index':pair['replicate_index'],
            'f0_evidence_sha256':pair['f0_evidence_sha256'],'f1_evidence_sha256':pair['f1_evidence_sha256'],
            'terminal_effect':pair.get('effect',pair.get('pair_effect')),'f0_success':f0['terminal_success'],'f1_success':f1['terminal_success'],
            'progress_effect':label,'f0_goal_vectors':v0,'f1_goal_vectors':v1,'f0_efficiency':e0,'f1_efficiency':e1,'delta_f1_minus_f0':delta}
        rows.append(row)
        if not f0['terminal_success'] and not f1['terminal_success'] and label=='P+':pool.append(row)
    root=Path(run_root)/'process'
    pool_ref=write(root/'VERIFIED_PROGRESS_POSITIVE.json',{'schema_id':'VERIFIED_PROGRESS_POSITIVE_RESEARCH_POOL_V1',
        'registration_ref':registration_ref,'rows':pool,'training_authorized':False,'stable_terminal_benefit_claimed':False,
        'new_independent_sample_claimed':False,'unit':'paired seed observation; no stable effect claim'})
    return write(root/'PROCESS_EFFECT_SUMMARY.json',{'schema_id':'INDEPENDENT_CAUSAL_PROCESS_SUMMARY_V1',
        'registration_ref':registration_ref,'plan_sha256':plan['plan_sha256'],
        'verifier_sha256':verifier['environment_result_package_sha256'],'counts':dict(Counter(r['progress_effect'] for r in rows)),
        'rows':rows,'progress_positive_research_pool_ref':pool_ref,'terminal_classifier_changed':False,'training_gate_changed':False})
