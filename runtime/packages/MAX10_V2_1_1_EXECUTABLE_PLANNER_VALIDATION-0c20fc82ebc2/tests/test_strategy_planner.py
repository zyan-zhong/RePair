import copy
import hashlib
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from strategy_planner import validate_review, derive_universe, plan_schema, check_final_strategies


def dh(domain, obj, excluded_field=None):
    obj = {k:v for k,v in obj.items() if k != excluded_field}
    return hashlib.sha256(domain.encode()+b'\0'+json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def fixture():
    c={'schema_id':'ANALYZER_REPAIR_CANDIDATE_V1','candidate_status':'EXECUTABLE_EXACT_ACTION',
       'candidate_sha256':'a'*64,'source_state_sha256':'b'*64,'menu_sha256':'c'*64,
       'source_proposal_sha256':'d'*64,'exact_action':'drop distractor','option_actions':[], 'termination_condition':None}
    ctx={'source_state_sha256':'b'*64,'public_task_goal':'put some remotecontrol on sofa.',
         'observation':'holding newspaper', 'admissible_commands':['drop distractor','look']}
    pair={'state_index':0,'source_state_sha256':'b'*64,'source_context':{'menu_sha256':'c'*64},
          'A2':{'candidate':c,'candidate_sha256':c['candidate_sha256']},
          'A3':{'candidate':{**c,'candidate_sha256':'e'*64},'candidate_sha256':'e'*64}}
    row={'packet_id':'p','source_state_sha256':'b'*64,'public_task_goal_exact':ctx['public_task_goal'],
         'diagnosis':'target tracking and repeated distractor pickup','counterevidence':'not yet solved',
         'falsifiable_hypothesis':'tracking target and checked locations prevents return to distractor',
         'plans':[]}
    for condition in ['A2','A3']:
        row['plans'].append({'condition':condition,'original_candidate_sha256':pair[condition]['candidate_sha256'],
         'program':[],'viable':True,'rationale':'whole continuation is tested, not just drop',
         'strategy':{k:'public observable criterion' for k in ['principal_bottleneck','current_subgoal','expected_next_event',
            'expected_state_change','progress_criterion','recovery_trigger','fallback_condition'] }|{'action':'drop distractor'}})
    return ctx,pair,row


def test_exact_goal_and_live_source_action_required():
    ctx,pair,row=fixture()
    validate_review(row,packet_id='p',context=ctx,pair=pair)
    bad=copy.deepcopy(row);bad['public_task_goal_exact']='put some newspaper on sofa.'
    with pytest.raises(ValueError,match='GOAL'):validate_review(bad,packet_id='p',context=ctx,pair=pair)
    bad=copy.deepcopy(row);bad['plans'][0]['strategy']['action']='invented command'
    with pytest.raises(ValueError,match='MENU'):validate_review(bad,packet_id='p',context=ctx,pair=pair)


def test_derived_candidate_preserves_original_and_new_scope():
    ctx,pair,row=fixture();universe={'schema_id':'SOURCE_UNIVERSE','pair_table':[pair],'pair_universe_sha256':'f'*64}
    original=copy.deepcopy(universe)
    def build(**kw):return {**kw,'strategy_plan_sha256':dh('plan',kw)}
    def identity(candidate,plan):return dh('identity',{'candidate':candidate,'plan':plan})
    new,registry=derive_universe(universe,[row],{ctx['source_state_sha256']:ctx},'experiment',dh,build,identity)
    assert universe==original
    assert new['pair_universe_sha256']!=universe['pair_universe_sha256']
    assert new['pair_table'][0]['A2']['candidate_sha256']!=pair['A2']['candidate_sha256']
    assert new['pair_table'][0]['A2']['formal_x_dispositions']==[]
    assert registry['original_analyzer_x_review_applies_to_new_plan'] is False
    assert len(registry['plans'])==2
    altered=copy.deepcopy(row);altered['plans'][0]['strategy']['recovery_trigger']='different trigger'
    again,_=derive_universe(universe,[altered],{ctx['source_state_sha256']:ctx},'experiment',dh,build,identity)
    assert new['pair_table'][0]['A2']['selected_execution_identity_sha256']!=again['pair_table'][0]['A2']['selected_execution_identity_sha256']


def test_final_training_view_cannot_silently_change_executed_plan():
    ctx,pair,row=fixture();c=pair['A2']['candidate'];plan={'strategy':row['plans'][0]['strategy']}
    expected={'source_candidate_sha256':c['candidate_sha256'],'strategy':{**plan['strategy'],'evidence_refs':[]}}
    check_final_strategies([expected],{c['candidate_sha256']:plan})
    expected['strategy']['fallback_condition']='different unregistered behavior'
    with pytest.raises(ValueError,match='STRATEGY'):check_final_strategies([expected],{c['candidate_sha256']:plan})


def test_map_schema_has_no_scientific_success_or_promotion_field():
    schema=plan_schema()
    assert schema['additionalProperties'] is False
    assert not ({'benefit','promote','environment_effect'} & set(schema['properties']))
