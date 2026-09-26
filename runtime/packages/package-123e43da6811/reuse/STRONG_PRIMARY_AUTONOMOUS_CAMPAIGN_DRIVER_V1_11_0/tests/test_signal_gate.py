import pytest
from signal_gate import validate_strategy_census

def good():
    return {'STRATEGY_ROW_COUNT':2,'VERIFIED_BENEFIT_ROW_COUNT':2,'STRATEGY_TARGET_TOKEN_COUNT':20,
    'STRATEGY_LOSS_BEARING_TOKEN_COUNT':20,'ACTION_TARGET_TOKEN_COUNT':4,'ACTION_LOSS_BEARING_TOKEN_COUNT':4,
    'PROMPT_MASKED_TOKEN_COUNT':30,'TOTAL_LOSS_BEARING_TOKEN_COUNT':24,'ACTION_ONLY_STRATEGY_ROW_COUNT':0,
    'NON_VERIFIED_STRATEGY_ROW_COUNT':0}

def test_full_dual_view_census_passes():
    assert validate_strategy_census(good())['authorized'] is True

def test_action_only_is_rejected():
    x=good(); x['ACTION_ONLY_STRATEGY_ROW_COUNT']=1
    with pytest.raises(ValueError,match='ACTION_ONLY'):
        validate_strategy_census(x)

def test_zero_strategy_loss_is_rejected():
    x=good(); x['STRATEGY_LOSS_BEARING_TOKEN_COUNT']=0
    with pytest.raises(ValueError,match='STRATEGY_LOSS'):
        validate_strategy_census(x)
