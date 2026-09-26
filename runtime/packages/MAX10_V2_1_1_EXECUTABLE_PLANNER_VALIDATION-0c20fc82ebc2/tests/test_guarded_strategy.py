from copy import deepcopy
import pytest
from guarded_strategy import Engine,validate_program

def rule(text,uses=1,kind='EXACT',suffix='',when=None):
    return {'when_all':when or [],'command':{'kind':kind,'text':text,'suffix':suffix},'max_uses':uses}

def predicate(kind,arg):return {'kind':kind,'arguments':[arg],'negate':False}

def test_phase_plan_uses_live_events_and_never_chooses_ambiguous_command():
    program=[{'purpose':'Acquire target','complete_when_any':[predicate('MENU_COMMAND_PREFIX','move pan ')],
              'rules':[rule('take pan ',kind='PREFIX_SUFFIX'),rule('open cabinet 1')]},
             {'purpose':'Process prerequisite','complete_when_any':[predicate('OBSERVATION_ALL_SUBSTRINGS','You clean')],
              'rules':[rule('clean pan ',kind='PREFIX_SUFFIX'),rule('go to sinkbasin 1')]},
             {'purpose':'Place target','complete_when_any':[],
              'rules':[rule('move pan ',kind='PREFIX_SUFFIX',suffix=' to stoveburner 1')]}]
    e=Engine(program,'look')
    assert e.decide([], 'source', ['look'],False)['action']=='look'
    assert e.decide(['look'],'closed',['open cabinet 1'],False)['action']=='open cabinet 1'
    assert e.decide(['look','open cabinet 1'],'open',['take pan 2 from cabinet 1'],False)['action']=='take pan 2 from cabinet 1'
    actions=['look','open cabinet 1','take pan 2 from cabinet 1']
    assert e.decide(actions,'held',['move pan 2 to cabinet 1','go to sinkbasin 1'],False)['action']=='go to sinkbasin 1'
    actions+=['go to sinkbasin 1']
    assert e.decide(actions,'sink',['clean pan 2 with sinkbasin 1'],False)['action']=='clean pan 2 with sinkbasin 1'
    actions+=['clean pan 2 with sinkbasin 1']
    assert e.decide(actions,'You clean the pan',['move pan 2 to stoveburner 1'],False)['action']=='move pan 2 to stoveburner 1'
    assert e.decide(actions+['move pan 2 to stoveburner 1'],'done',[],True)['reason']=='ENVIRONMENT_DONE'
    ambiguous=Engine([{'purpose':'take','complete_when_any':[],'rules':[rule('take pan ',kind='PREFIX_SUFFIX')]}],'look')
    ambiguous.decide([],'s',['look'],False)
    assert ambiguous.decide(['look'],'s',['take pan 1 from table 1','take pan 2 from table 1'],False)['reason']=='AMBIGUOUS_REGISTERED_MENU_RULE'

def test_failed_phase_does_not_claim_completion_or_repeat_exhausted_rule():
    e=Engine([{'purpose':'prerequisite','complete_when_any':[],'rules':[rule('look')]}],'look')
    e.decide([],'same',['look'],False)
    e.decide(['look'],'same',['look'],False)
    assert e.decide(['look','look'],'same',['look'],False)['reason']=='NO_REGISTERED_RULE_APPLICABLE'
    assert e.phase==0

def test_program_rejects_unbounded_or_hidden_predicates():
    p=[{'purpose':'x','complete_when_any':[],'rules':[rule('look',0)]}]
    with pytest.raises(ValueError):validate_program(p)
    p[0]['rules'][0]['max_uses']=1
    p[0]['complete_when_any']=[predicate('PRIVATE_FACT','target')]
    with pytest.raises(ValueError):validate_program(p)

def test_guard_cannot_advance_after_unrecorded_action():
    e=Engine([],'look');e.decide([],'s',['look'],False)
    with pytest.raises(ValueError,match='EXECUTED_PREFIX'):e.decide(['other'],'s',['look'],False)
