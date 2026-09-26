from __future__ import annotations

def desired_governance_call(repo,outcome,state_path):
    if outcome not in {'PROMOTED','ROLLED_BACK','NO_TRAINING_UPDATE','PROTOCOL_INFRA_INVALID'}: raise ValueError('OUTCOME_INVALID')
    return {'repo':repo,'module':'pchsi.round_control.scientific_round_governance','state_path':state_path,'outcome':outcome,'max_valid_rounds':10,'no_promotion_patience':3,'native_authority_required':True}
