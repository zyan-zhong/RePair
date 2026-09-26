from __future__ import annotations
POS=('STRATEGY_ROW_COUNT','VERIFIED_BENEFIT_ROW_COUNT','STRATEGY_TARGET_TOKEN_COUNT','STRATEGY_LOSS_BEARING_TOKEN_COUNT','ACTION_TARGET_TOKEN_COUNT','ACTION_LOSS_BEARING_TOKEN_COUNT','PROMPT_MASKED_TOKEN_COUNT','TOTAL_LOSS_BEARING_TOKEN_COUNT')
ZERO=('ACTION_ONLY_STRATEGY_ROW_COUNT','NON_VERIFIED_STRATEGY_ROW_COUNT')
def validate_strategy_census(c):
    for k in POS:
        if type(c.get(k)) is not int or c[k]<=0: raise ValueError(k+'_MUST_BE_POSITIVE')
    if c['VERIFIED_BENEFIT_ROW_COUNT']!=c['STRATEGY_ROW_COUNT']: raise ValueError('NON_VERIFIED_STRATEGY_ROW_COUNT')
    for k in ZERO:
        if c.get(k)!=0: raise ValueError(k+'_MUST_BE_ZERO')
    return {'authorized':True,'action_only_fallback':False}
