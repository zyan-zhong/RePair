"""Readable TRAIN evidence from the existing typed producer outputs only."""
from copy import deepcopy
import json, hashlib

FORBIDDEN={'current_f0f1_outcomes','current_selected_f0f1_outcomes','future_pi2_evaluation',
    'future_policy_evaluation','current_human_pre','human_pre_record','human_selection',
    'human_selection_rationale','strong_model_benchmark_per_task_results',
    'benchmark_per_task_results','sealed_test_trajectory'}

def safe(value):
    if isinstance(value,dict):
        if FORBIDDEN.intersection(value):raise ValueError('PRE_FORBIDDEN_EVIDENCE_KEY')
        for x in value.values():safe(x)
    elif isinstance(value,(list,tuple)):
        for x in value:safe(x)

def require_later_round(binding,authority,*,current):
    if binding['round_id']==authority['excluded_round_id']:return False
    ordinal=current.get('round_index')
    if type(ordinal) is not int or ordinal<=authority['activation_after_round_index']:
        raise ValueError('PRE_NEXT_ROUND_AUTHORITY_REQUIRED')
    return True

def build_view(data):
    binding=data['binding'];rid=binding['round_id'];pid=binding['parent_policy_id']
    for x in (data['tail'],data['universe'],data['values']['request']):
        if x['round_id']!=rid or x['parent_policy_id']!=pid:raise ValueError('PRE_EVIDENCE_ROUND_POLICY_MISMATCH')
    if data['tail']['profile_sha256']!=data['capability']['profile_sha256'] or data['tail']['policy_profile_sha256']!=data['behavior']['policy_profile_sha256']:
        raise ValueError('PRE_PROFILE_BINDING_MISMATCH')
    sources={}
    for item in data['sources']:
        m=item['manifest'];pack=item['pack']
        if m['evidence_pack_sha256']!=pack['evidence_pack_sha256'] or m['round_id']!=rid:
            raise ValueError('PRE_SOURCE_PACK_BINDING_MISMATCH')
        task=pack['task_identity']
        if m['task_id']!=task['task_id'] or m['gamefile_sha256']!=task['gamefile_sha256']:
            raise ValueError('PRE_SOURCE_TASK_BINDING_MISMATCH')
        sources[item['source_unit_id']]=item
    contexts={};groups=[]
    for item in data['prepared']:
        g=item['group'];groups.append(g)
        for c in item['contexts']:
            item_source=sources[c['source_unit_id']];task=item_source['pack']['task_identity']
            if not c['public_task_goal'] or c['public_task_goal']!=task['public_task_goal']:
                raise ValueError('PRE_PUBLIC_GOAL_MISSING_OR_MISMATCH')
            family=task['task_type']
            if not family or family!=g['task_family']:raise ValueError('PRE_TASK_FAMILY_BINDING_MISMATCH')
            row={k:deepcopy(c[k]) for k in ('source_state_sha256','source_unit_id','source_call_index',
                'public_task_goal','observation','admissible_commands','menu_sha256','interface_feedback_before','budget_before')}
            row.update(task_id=task['task_id'],task_family=family,gamefile_sha256=task['gamefile_sha256'],
                evidence_pack_sha256=item_source['pack']['evidence_pack_sha256'])
            prior=contexts.get(c['source_state_sha256'])
            if prior is not None and prior!=row:raise ValueError('PRE_SOURCE_CONTEXT_CONFLICT')
            contexts[c['source_state_sha256']]=row
    for pair in data['universe']['pair_table']:
        c=contexts[pair['source_state_sha256']]
        for key in ('menu_sha256','admissible_commands'):
            if pair['source_context'][key]!=c[key]:raise ValueError('PRE_CANDIDATE_CONTEXT_CHANGED')
    accepted={};statuses=[]
    for call in data['calls']:
        result=call['result'];stage=call['stage']
        statuses.append({'stage_id':stage,'logical_call_id':result['logical_call_id'],'status':result['status']})
        if result['status']=='ACCEPTED':
            accepted.setdefault(stage,[]).append({'artifact':call['artifact'],'source_ref':call['artifact_ref']})
    census=data['values']['global_terminal']
    counts={k:census[k] for k in ('scheduled_count','success_count','failure_count','infrastructure_invalid_count','protocol_invalid_count')}
    if counts['scheduled_count']!=sum(counts[k] for k in counts if k!='scheduled_count'):
        raise ValueError('PRE_ROLLOUT_DENOMINATOR_MISMATCH')
    local=[]
    for sha,item in sorted(data['local_a1'].items()):
        a=item['artifact']
        if a['local_result_sha256']!=sha:raise ValueError('PRE_LOCAL_RESULT_MISMATCH')
        # Keep every hypothesis and evidence/counterevidence relation; omit only
        # redundant outer metadata, never slice strings or sample scientific rows.
        local.append({'local_result_sha256':sha,'source_ref':item['ref'],
            'abstained':a['abstained'],'abstain_reason':a['abstain_reason'],'error_instances':a['error_instances']})
    value={'schema_id':'REGISTERED_READABLE_PLANNER_PRE_EVIDENCE_V1','schema_version':1,
        'round_id':rid,'parent_policy_id':pid,'evidence_cutoff_sha256':binding['refs']['handoff']['file_sha256'],
        'analyzer_terminal_sha256':data['tail']['terminal_sha256'],
        'pair_universe_sha256':data['universe']['pair_universe_sha256'],
        'round_start_memory_snapshot_sha256':data['values']['request']['round_start_memory_snapshot_sha256'],
        'rollout_census':counts,'source_contexts':[contexts[k] for k in sorted(contexts)],
        'local_findings':local,'group_membership':groups,
        'group_findings':accepted.get('G-A2',[])+accepted.get('G-A3',[]),
        'component_attributions':accepted.get('C',[]),'crosschecks':accepted.get('X',[]),
        'capability_profile':data['capability'],'policy_behavior_profile':data['behavior'],
        'method_statuses':statuses,
        'missingness':{k:data['local_census'][k] for k in ('complete_groups','partial_groups','no_source_groups','censored_sources')},
        'scope':{'dataset':'TRAIN_UPDATE','causal_effect_authority':False,'promotion_authority':False,
            'current_f0f1_results_visible':False,'source_selection_changed':False,
            'all_registered_group_findings_included':True,'raw_trajectory_dump_included':False,
            'local_findings_scope':'SOURCE_CLOSED_A1_RESULTS_USED_BY_REGISTERED_GROUPS'}}
    safe(value)
    value['view_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    return value

def enrich_pair_view(pair_view,evidence):
    value=deepcopy(pair_view);contexts={r['source_state_sha256']:r for r in evidence['source_contexts']}
    for row in value['pair_table']:
        source=contexts[row['source_state_sha256']]
        if row.get('task_family') not in (None,source['task_family']):raise ValueError('PRE_PAIR_FAMILY_CONFLICT')
        row['task_family']=source['task_family']
    return value
