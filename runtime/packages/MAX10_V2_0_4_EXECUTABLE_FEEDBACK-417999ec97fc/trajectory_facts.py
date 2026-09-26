"""Deterministic public trajectory facts, without causal or task-semantic inference."""
import json
from collections import Counter

def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def rle(rows):
    result=[]
    for row in rows:
        if result and result[-1]['value']==row:result[-1]['count']+=1
        else:result.append({'count':1,'value':row})
    return result

def project(verifier):
    views=[];view_ids={};patterns=[];pattern_ids={};branches=[]
    def intern(value,table,index):
        key=canonical(value)
        if key not in index:index[key]=len(table);table.append(value)
        return index[key]
    def view(observation,menu):return intern({'observation':observation,'menu':menu},views,view_ids)
    for branch in verifier['branch_records']:
        available=all(k in branch for k in ('environment_transitions_from_source','policy_calls','intervention_sequence','final_budget','terminal_success'))
        scientific=branch.get('evidence_complete') is True and branch.get('scientific_outcome_produced') is True
        events=[];calls=[];absent=0
        for t in branch.get('environment_transitions_from_source',[]):
            events.append({'role':t['role'],'action':t['action'],
                'before_view':view(t['pre_observation'],t['pre_menu']),
                'after_view':view(t['resulting_observation'],t['resulting_menu']),
                'environment_done':t['done'],'terminal_success_signal':t['won']})
        for item in branch.get('policy_calls',[]):
            call=item['policy_call'];raw=call['raw_response_text']
            try:
                parsed=json.loads(raw)
                action=parsed.get('action') if isinstance(parsed,dict) else None
                if not isinstance(action,str):action=None
            except (ValueError,TypeError):action=None
            missing=action is not None and action not in call['admissible_commands'];absent+=int(missing)
            calls.append({'view':view(call['observation'],call['admissible_commands']),
                'response_text':raw,'parsed_action':action,'parsed_action_absent_from_live_menu':missing,
                'interface_feedback_before':call['interface_feedback_before']})
        pattern={'intervention_steps':len(branch['intervention_sequence']) if available else None,
            'intervention_actions':[t['action'] for t in branch.get('intervention_sequence',[])],
            'continuation_environment_steps':len(events)-len(branch['intervention_sequence']) if available else None,
            'terminal_success':branch.get('terminal_success'),'terminal_reason':branch.get('terminal_reason'),
            'typed_option_stop_reason':branch.get('typed_option_stop_reason'),'final_budget':branch.get('final_budget'),
            'trajectory_fields_available':available,'scientifically_valid_branch':scientific,
            'parsed_actions_absent_from_live_menu':absent if available else None,
            'source_visible_history_at_first_policy_call':branch['policy_calls'][0]['policy_call']['executed_history'] if calls else [],
            'transitions_rle':rle(events),'policy_attempts_rle':rle(calls)}
        pattern_id=intern(pattern,patterns,pattern_ids)
        branches.append({k:branch.get(k) for k in ('branch_key_sha256','source_state_sha256','source_candidate_sha256','arm','continuation_seed','evidence_sha256','evidence_complete','scientific_outcome_produced','status')})
        branches[-1]['pattern_id']=pattern_id
    return {'schema_id':'PUBLIC_CAUSAL_CONTINUATION_FACTS_V1','round_id':verifier['round_id'],
        'source_environment_result_package_sha256':verifier['environment_result_package_sha256'],
        'source_access':'TRAIN_UPDATE','branch_count':len(branches),
        'planned_branch_count':verifier.get('planned_branch_count'),
        'missing_branch_record_count':max(0,verifier['planned_branch_count']-len(branches)) if 'planned_branch_count' in verifier else None,
        'branches':branches,'patterns':patterns,'public_views':views,
        'states':[{k:s[k] for k in ('source_state_sha256','source_task_id','public_task_goal','stable_effect')} for s in verifier['state_results']],
        'causal_effect_assignment_authorized':False,'training_supervision_authorized':False,
        'notes':'Zero-based view/pattern IDs; run-length counts preserve every selected event in order. Menu absence is an interface fact, not proof of a particular hidden prerequisite. Local action feedback does not imply causal BENEFIT.'}

def expand_branch(facts,key):
    branch=next(b for b in facts['branches'] if b['branch_key_sha256']==key)
    pattern=facts['patterns'][branch['pattern_id']];transitions=[]
    for run in pattern['transitions_rle']:
        t=run['value'];before=facts['public_views'][t['before_view']];after=facts['public_views'][t['after_view']]
        transitions.extend([{**t,'pre_observation':before['observation'],'pre_menu':before['menu'],
            'resulting_observation':after['observation'],'resulting_menu':after['menu']}] * run['count'])
    return {**pattern,'transitions':transitions}

def researcher_summary(facts):
    """Mechanical synopsis; full indexed facts remain stored in the evidence plane."""
    patterns=[];lookup={};branches=[]
    for branch in facts['branches']:
        p=facts['patterns'][branch['pattern_id']];runs=p['transitions_rle'];calls=p['policy_attempts_rle']
        interventions=[]
        remaining=p['intervention_steps'] or 0
        for run in runs:
            t=run['value']
            for _ in range(min(remaining,run['count'])):
                interventions.append({'action':t['action'],'before':facts['public_views'][t['before_view']]['observation'],
                    'after':facts['public_views'][t['after_view']]['observation']})
            remaining-=min(remaining,run['count'])
        bad=Counter()
        for run in calls:
            c=run['value']
            if c['parsed_action_absent_from_live_menu']:bad[c['parsed_action']]+=run['count']
        row={k:p[k] for k in ('intervention_steps','continuation_environment_steps','terminal_success','terminal_reason','typed_option_stop_reason','parsed_actions_absent_from_live_menu','trajectory_fields_available','scientifically_valid_branch')}
        row.update(intervention_public_feedback=interventions,
            executed_actions_rle=rle([r['value']['action'] for r in runs for _ in range(r['count'])]),
            inadmissible_parsed_actions=dict(bad),
            first_continuation_observation=facts['public_views'][calls[0]['value']['view']]['observation'] if calls else None,
            last_public_observation=facts['public_views'][runs[-1]['value']['after_view']]['observation'] if runs else None)
        key=canonical(row)
        if key not in lookup:lookup[key]=len(patterns);patterns.append(row)
        branches.append({'source_state_sha256':branch['source_state_sha256'],'arm':branch['arm'],
            'continuation_seed':branch['continuation_seed'],'pattern_id':lookup[key]})
    return {k:v for k,v in facts.items() if k not in ('patterns','branches','public_views','notes')} | {
        'patterns':patterns,'branches':branches,'notes':'Deterministic synopsis, not full raw trajectories. Complete executed action sequence and inadmissible parsed-action counts retained. Public feedback includes each intervention, first continuation and last executed observation; intermediate observation text and raw responses remain in the indexed full evidence. No inferred hidden prerequisite or new causal label.'}

def history_summary(facts):
    """All-branch state/arm aggregates for cross-round research memory."""
    summary=researcher_summary(facts);rows=[]
    for state in facts['states']:
        for arm in sorted({b['arm'] for b in summary['branches'] if b['source_state_sha256']==state['source_state_sha256']}):
            chosen=[b for b in summary['branches'] if b['source_state_sha256']==state['source_state_sha256'] and b['arm']==arm]
            patterns=[summary['patterns'][b['pattern_id']] for b in chosen]
            actions=Counter();illegal=Counter();max_runs={};feedback=[]
            for p in patterns:
                illegal.update(p['inadmissible_parsed_actions'])
                for r in p['executed_actions_rle']:
                    actions[r['value']]+=r['count'];max_runs[r['value']]=max(max_runs.get(r['value'],0),r['count'])
                if p['intervention_public_feedback'] not in feedback:feedback.append(p['intervention_public_feedback'])
            rows.append({'source_state_sha256':state['source_state_sha256'],'arm':arm,'branch_count':len(chosen),
                'scientifically_valid_branches':sum(p['scientifically_valid_branch'] for p in patterns),
                'trajectory_unavailable_branches':sum(not p['trajectory_fields_available'] for p in patterns),
                'successful_valid_branches':sum(p['terminal_success'] is True and p['scientifically_valid_branch'] for p in patterns),
                'intervention_steps_observed_total':sum(p['intervention_steps'] or 0 for p in patterns),
                'continuation_environment_steps_observed_total':sum(p['continuation_environment_steps'] or 0 for p in patterns),
                'terminal_reasons':dict(Counter(p['terminal_reason'] for p in patterns if isinstance(p['terminal_reason'],str))),
                'terminal_reason_unknown_branches':sum(not isinstance(p['terminal_reason'],str) for p in patterns),
                'executed_action_totals':dict(actions),'maximum_consecutive_action_runs':max_runs,
                'inadmissible_parsed_action_totals':dict(illegal),'distinct_intervention_public_feedback':feedback})
    return {'schema_id':'CLOSED_TRAIN_STATE_ARM_TRAJECTORY_AGGREGATES_V1','round_id':facts['round_id'],
        'source_environment_result_package_sha256':facts['source_environment_result_package_sha256'],
        'states':facts['states'],'state_arm_aggregates':rows,'branch_count':facts['branch_count'],
        'planned_branch_count':facts['planned_branch_count'],'missing_branch_record_count':facts['missing_branch_record_count'],
        'causal_effect_assignment_authorized':False,'training_supervision_authorized':False,
        'notes':'Totals aggregate ALL persisted branch records, not independent tasks. Missing records are explicitly counted when the verifier supplies the planned denominator. Maximum consecutive run counts are per branch. Prior task outcomes do not label current states. Full branch patterns and public observations remain in the registered facts index.'}
