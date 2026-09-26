"""Reproduce the live public guard failure and expose actual planner coverage."""
import copy,json
from pathlib import Path
import pytest
from guarded_strategy import Engine,predicate_hit
from strategy_planner import derive_universe
from test_strategy_planner import fixture,dh


def pred(target):
    return {'kind':'PUBLIC_TARGET_CARRIED','arguments':[target],'negate':False}


@pytest.mark.parametrize('target,instance,destination', [('pan',1,'sinkbasin 1'),('pen',3,'desk 2'),('cd',12,'shelf 1')])
def test_current_move_menu_proves_carriage_without_current_inventory_text(target,instance,destination):
    assert predicate_hit(pred(target),'You arrive at the destination.',
                         [f'move {target} {instance} to {destination}'])


@pytest.mark.parametrize('menu,observation', [
    (['take pan 1 from stoveburner 1'],'You see a pan 1.'),
    (['move saucepan 1 to table 1'],'You see a pan 1.'),
    (['move pan 1 towards table 1'],'Your task is to: carry a pan 1.'),
    (['look'],'You are not carrying anything.'),
])
def test_noncarriage_public_text_and_similar_object_names_do_not_satisfy_guard(menu,observation):
    assert not predicate_hit(pred('pan'),observation,menu)


def test_legacy_menu_and_explicit_inventory_remain_supported():
    assert predicate_hit(pred('pan'),'location',['put pan 2 in/on sinkbasin 1'])
    assert predicate_hit(pred('pan'),'You are carrying: a pan 2.',['look'])


def test_real_pan_strategy_executes_cleaning_instead_of_premature_parent_fallback():
    b=json.loads((Path(__file__).parents[1]/'fixtures/CARRIED_GUARD_REAL_BRANCH.json').read_bytes())['branch']
    s=b['strategy_execution'];plan=s['contract']['plan'];engine=Engine(plan['program'],plan['strategy']['action'])
    assert engine.decide([],s['source_observation'],s['source_commands'],False)['action']=='go to sinkbasin 1'
    fields={line.split('=',1)[0]:json.loads(line.split('=',1)[1]) for line in s['calls'][0]['base_prompt_text'].splitlines() if '=' in line}
    decision=engine.decide(['go to sinkbasin 1'],fields['CURRENT_OBSERVATION_JSON'],fields['VISIBLE_ADMISSIBLE_COMMANDS_JSON'],False)
    assert decision['decision']=='EXECUTE'
    assert decision['action']=='clean pan 1 with sinkbasin 1'


def test_final_pre_receives_computed_local_only_coverage_without_changing_scientific_plan():
    ctx,pair,review=fixture();original=copy.deepcopy(review)
    universe={'pair_table':[pair],'pair_universe_sha256':'f'*64}
    build=lambda **kw:{**kw,'strategy_plan_sha256':dh('plan',kw)}
    identity=lambda c,p:dh('id',{'candidate':c,'plan':p})
    result,_=derive_universe(universe,[review],{ctx['source_state_sha256']:ctx},'test',dh,build,identity)
    coverage=result['pair_table'][0]['A2'].get('execution_coverage')
    assert coverage is not None
    assert coverage['mode']=='INITIAL_ACTION_AND_POLICY_CUE_ONLY'
    assert coverage['phase_count']==0 and coverage['maximum_registered_actions']==1
    assert coverage['full_task_completion_claimed'] is False
    assert review==original


def test_existing_phases_can_search_then_use_newly_visible_tool_without_guessing_location():
    def predicate(kind,arg):return {'kind':kind,'arguments':[arg],'negate':False}
    def rule(text,kind='EXACT'):
        return {'when_all':[],'command':{'kind':kind,'text':text,'suffix':''},'max_uses':1}
    program=[{'purpose':'Discover the required tool using public destinations once each',
        'complete_when_any':[predicate('PUBLIC_TARGET_VISIBLE','desklamp')],
        'rules':[rule('go to desk 2'),rule('go to shelf 1')]},
        {'purpose':'Use the publicly revealed tool while holding the task object',
        'complete_when_any':[],
        'rules':[{'when_all':[pred('pen')],**{k:v for k,v in rule('use desklamp ','PREFIX_SUFFIX').items() if k!='when_all'}}]}]
    e=Engine(program,'take pen 1 from desk 1');actions=[]
    for obs,menu,expected in [
        ('You see a pen 1.',['take pen 1 from desk 1'],'take pen 1 from desk 1'),
        ('You pick up the pen 1.',['go to desk 2','go to shelf 1','move pen 1 to desk 1'],'go to desk 2'),
        ('On the desk 2, you see nothing.',['go to desk 2','go to shelf 1','move pen 1 to desk 2'],'go to shelf 1'),
        ('On the shelf 1, you see a desklamp 1.',['use desklamp 1','move pen 1 to shelf 1'],'use desklamp 1')]:
        decision=e.decide(actions,obs,menu,False)
        assert decision['decision']=='EXECUTE' and decision['action']==expected
        actions.append(expected)
    assert e.decide(actions,'Task complete.',[],True)['reason']=='ENVIRONMENT_DONE'
