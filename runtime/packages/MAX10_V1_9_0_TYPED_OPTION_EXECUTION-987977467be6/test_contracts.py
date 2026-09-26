import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from typed_options import bind_contract,validate_contract,decide,validate_annex

def candidate():
    return {'source_state_sha256':'a'*64,'candidate_sha256':'b'*64,'candidate_status':'EXECUTABLE_SHORT_OPTION',
        'option_actions':['go to drawer 1','go to drawer 2'],'termination_condition':'Stop on a take affordance or menu change.',
        'live_menu_revalidation_required':True,'all_intervention_actions_count_against_environment_budget':True}

def row(c=None):
    c=c or candidate()
    return {'source_candidate_sha256':c['candidate_sha256'],'source_state_sha256':c['source_state_sha256'],
        'termination_condition':c['termination_condition'],'dispatch_mode':'ORDERED_SEQUENCE',
        'semantic_coverage':'FULL','coverage_explanation':'All clauses are represented by the take predicate and mandatory stops.',
        'stop_predicates':[{'kind':'MENU_COMMAND_PREFIX','arguments':['take cellphone ']}]}

def contract():return bind_contract(candidate(),row(),{'path':'/registered/index.json','file_sha256':'c'*64})

def test_complete_ordered_sequence_and_live_menu():
    c=contract()
    assert decide(c,executed_actions=[],observation='',menu=['go to drawer 1'],environment_done=False)['action']=='go to drawer 1'
    assert decide(c,executed_actions=['go to drawer 1'],observation='',menu=['go to drawer 2'],environment_done=False)['action']=='go to drawer 2'
    assert decide(c,executed_actions=[],observation='',menu=[],environment_done=False)['reason']=='NEXT_REGISTERED_ACTION_NOT_ADMISSIBLE'
    assert decide(c,executed_actions=c['option_actions'],observation='',menu=[],environment_done=False)['reason']=='REGISTERED_ACTIONS_EXHAUSTED'

def test_take_stop_and_no_wrong_object_stop():
    c=contract()
    assert decide(c,executed_actions=[],observation='',menu=['take cellphone 2 from desk 1'],environment_done=False)['decision']=='STOP'
    assert decide(c,executed_actions=[],observation='',menu=['take apple 1 from desk 1','go to drawer 1'],environment_done=False)['decision']=='EXECUTE'

def test_environment_done_precedes_action():
    assert decide(contract(),executed_actions=[],observation='',menu=['go to drawer 1'],environment_done=True)['reason']=='ENVIRONMENT_DONE'

@pytest.mark.parametrize('field,value',[('source_candidate_sha256','d'*64),('termination_condition','rewritten'),('semantic_coverage','PARTIAL')])
def test_mismatch_and_partial_rejected(field,value):
    r=row();r[field]=value
    with pytest.raises(ValueError):bind_contract(candidate(),r,{})

def test_unknown_predicate_and_empty_prefix_rejected():
    for p in [{'kind':'RUN_CODE','arguments':['anything']},{'kind':'MENU_COMMAND_PREFIX','arguments':['']}]:
        r=row();r['stop_predicates']=[p]
        with pytest.raises(ValueError):bind_contract(candidate(),r,{})

def test_goal_instruction_does_not_count_as_observation():
    r=row();r['stop_predicates']=[{'kind':'OBSERVATION_ALL_SUBSTRINGS','arguments':['cellphone']}]
    c=bind_contract(candidate(),r,{})
    assert decide(c,executed_actions=[],observation='Your task is to: find cellphone.\nYou see a desk.',menu=['go to drawer 1'],environment_done=False)['decision']=='EXECUTE'

def test_hash_and_prefix_tampering_rejected():
    c=contract();c['option_actions'].reverse()
    with pytest.raises(ValueError):validate_contract(c)
    with pytest.raises(ValueError):decide(contract(),executed_actions=['go to drawer 2'],observation='',menu=[],environment_done=False)

def test_annex_requires_exact_complete_short_option_set():
    c=candidate();validate_annex([row(c)],[c])
    for rows in [[],[row(c),row(c)]]:
        with pytest.raises(ValueError):validate_annex(rows,[c])

def test_current_frozen_registration_fixture():
    f=json.loads(Path(__file__).with_name('FROZEN_OPTION_REGISTRATION.json').read_bytes())
    validate_annex(f['execution_contracts'],f['candidates'])
    assert len(f['execution_contracts'])==2
    for c,r in zip(f['candidates'],f['execution_contracts']):
        bound=bind_contract(c,r,{})
        assert bound['option_actions']==c['option_actions']
        assert bound['source_termination_condition']==c['termination_condition']
