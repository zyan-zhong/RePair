#!/usr/bin/env python3
"""Recompute manuscript aggregates from the included anonymous numerical data.

This does not execute new policy, research-model, or environment calls.
Python 3.10+; standard library only.
"""
from pathlib import Path
import collections, hashlib, json, statistics
from fractions import Fraction

ROOT=Path(__file__).resolve().parent
def load(name): return json.loads((ROOT/'evidence'/name).read_bytes())
def main():
    data=load('selection_pairs.json');rows=data['rows']
    assert data['split']=='TRAIN_SELECT' and data['seeds']==[17]
    assert data['memory']==data['harness']=='OFF'
    assert len(rows)==len({r['task_id'] for r in rows})==355
    stats={}
    for arm in ('parent','candidate'):
        cells=[r[arm] for r in rows]
        assert all(c['seed']==17 and 0<=c['goal_numerator']<=c['goal_denominator'] and c['goal_denominator']>0 for c in cells)
        stats[arm]={
            'success':sum(c['success'] for c in cells),
            'tasks':len(cells),
            'mean_goal_fraction':statistics.mean(c['goal_numerator']/c['goal_denominator'] for c in cells),
            'terminations':dict(collections.Counter(c['termination_reason'] for c in cells)),
            'out_of_menu_calls':sum(c['inadmissible'] for c in cells),
            'format_failure_calls':sum(c['protocol_failures'] for c in cells),
            'mean_environment_steps':statistics.mean(c['steps'] for c in cells),
            'mean_policy_calls':statistics.mean(c['calls'] for c in cells),
            'adjacent_repeated_executed_actions':sum(c['repeated_adjacent_actions'] for c in cells),
        }
    joint=collections.Counter((r['parent']['success'],r['candidate']['success']) for r in rows)
    goal_deltas=[Fraction(r['candidate']['goal_numerator'],r['candidate']['goal_denominator'])-Fraction(r['parent']['goal_numerator'],r['parent']['goal_denominator']) for r in rows]
    goal_changes={'better':sum(x>0 for x in goal_deltas),'worse':sum(x<0 for x in goal_deltas),'equal':sum(x==0 for x in goal_deltas)}
    assert goal_changes=={'better':5,'worse':6,'equal':344}
    states=load('causal_states.json')['states'];effects=collections.Counter();success_calls=[]
    for value in states.values():
        a={r['seed']:r for r in value['arms']['F0']};b={r['seed']:r for r in value['arms']['F1']}
        assert set(a)==set(b)=={17,31,47,73,101}
        n=collections.Counter((a[k]['success'],b[k]['success']) for k in a)
        effect=('BENEFIT' if n[(False,True)]>=4 and n[(True,False)]==0 else
                'HARM' if n[(True,False)]>=4 and n[(False,True)]==0 else
                'NEUTRAL_SUCCESS' if n[(True,True)]>=4 else
                'NEUTRAL_FAILURE' if n[(False,False)]>=4 else 'UNCERTAIN')
        effects[effect]+=1
        success_calls.extend(x['policy_calls'] for x in b.values() if x['success'])
    labels=load('native_label_counts.json');training=load('training_configuration.json')
    assert labels['ACTION_LOSS_BEARING_TOKEN_COUNT']+labels['STRATEGY_LOSS_BEARING_TOKEN_COUNT']==training['dataset']['one_pass_target_loss_token_count']
    assert labels['TOTAL_LOSS_BEARING_TOKEN_COUNT']*training['budget']['epochs']==training['budget']['target_loss_token_budget']
    assert stats['parent']['success']==stats['candidate']['success']==3
    assert joint=={(False,False):351,(True,True):2,(False,True):1,(True,False):1}
    assert effects=={'BENEFIT':4,'NEUTRAL_FAILURE':1}
    assert len(success_calls)==20 and all(n==0 for n in success_calls)
    coverage=load('supervision_coverage.json')['sources']
    assert len(coverage)==4
    assert sorted(r['program_actions_per_repetition'][0] for r in coverage)==[2,4,4,6]
    assert all(r['native_views']=={'I1_EXECUTION_ACTION':1,'STRATEGY_AUXILIARY':1} for r in coverage)
    assert all(r['successful_F1_repetitions']==5 and r['successful_F1_policy_calls']==[0]*5 for r in coverage)
    assert sum(r['native_label_token_counts']['I1_EXECUTION_ACTION'] for r in coverage)==51
    assert sum(r['native_label_token_counts']['STRATEGY_AUXILIARY'] for r in coverage)==2546
    result={'selection':stats,'joint_success_counts':{f'{int(k[0])}{int(k[1])}':v for k,v in sorted(joint.items())},
            'causal_state_effects':dict(effects),'successful_F1_branches_without_policy_calls':len(success_calls),
            'training_rows':training['dataset']['row_count'],'optimizer_steps':training['budget']['optimizer_steps'],
            'paired_goal_changes':goal_changes,'supervision_sources':len(coverage),
            'checks_passed':True}
    print(json.dumps(result,indent=2))
    return result
if __name__=='__main__':main()
