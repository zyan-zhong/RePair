import pytest
from process_effect import goal_vector,process_label,efficiency

SPEC={'metric_id':'terminal_dynamic_goal_condition_fraction_v1','groups':[{'count':2,'alternatives':[[['hot',['obj1'],False],['at',['obj1','goal'],False]],[['hot',['obj2'],False],['at',['obj2','goal'],False]]]}]}

def test_progress_requires_pointwise_verified_improvement_not_shorter_failure():
    source=goal_vector(SPEC,set())
    partial=goal_vector(SPEC,{('hot',('obj1',))})
    assert process_label(source,partial)=='P+'
    assert process_label(partial,source)=='P-'
    assert process_label(source,source)=='P0'
    mixed=goal_vector(SPEC,{('at',('obj1','goal'))})
    assert process_label(partial,mixed)=='PU'

def test_witness_alternatives_are_retained_separately():
    vector=goal_vector(SPEC,{('hot',('obj1',)),('at',('obj2','goal'))})
    assert vector==[[[True,False],[False,True]]]
    from goal_metric import completion
    assert completion(SPEC,{('hot',('obj1',)),('at',('obj2','goal'))})==(1,2)

def test_missing_or_different_progress_dimensions_abstain():
    assert process_label(None,[[[True]]])=='PU'
    assert process_label([[[False]]],[[[False,True]]])=='PU'

def test_efficiency_uses_recorded_counts_and_names_public_proxy():
    step={'action':'look','pre_observation':'same','resulting_observation':'same','pre_menu':['look'],'resulting_menu':['look']}
    row={'environment_transitions_from_source':[step,step],'policy_calls':[],
         'final_budget':{'environment_step_count':8},'strategy_execution':{'budget_limits':{'max_environment_steps':30}}}
    m=efficiency(row)
    assert m['environment_steps']==2 and m['remaining_environment_budget']==22
    assert m['consecutive_repeated_actions']==1 and m['no_public_change_actions']==2
    assert m['policy_calls']==0
