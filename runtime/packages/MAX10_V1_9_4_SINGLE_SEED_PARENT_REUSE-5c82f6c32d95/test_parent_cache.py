import copy
import pytest
from parent_cache import equivalent,cache_choice

def test_parent_inherits_promoted_candidate_or_retained_parent():
    inherited={'source_terminal_ref':{'path':'old','sha256':'a'*64},'source_arm':'candidate'}
    assert cache_choice('ROLLED_BACK',inherited,{'path':'new'},'parent')==inherited
    assert cache_choice('NO_TRAINING_UPDATE',inherited,None,None)==inherited
    assert cache_choice('PROMOTED',inherited,{'path':'new'},'candidate')=={'source_terminal_ref':{'path':'new'},'source_arm':'candidate'}

def test_equivalence_covers_every_semantic_field_and_fixed_seed():
    source={'weights':'a','tasks':['t'],'seeds':[17,31],'environment':'e','request':'r','budget':30}
    current={**source,'seeds':[17]}
    equivalent(source,current)
    for key in ('weights','tasks','environment','request','budget'):
        changed=copy.deepcopy(current);changed[key]='CHANGED'
        with pytest.raises(ValueError):equivalent(source,changed)
    with pytest.raises(ValueError):equivalent(source,{**current,'seeds':[31]})
    with pytest.raises(ValueError):equivalent(source,{**current,'extra':'unknown'})
