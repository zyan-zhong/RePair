from governance_adapter import desired_governance_call

def test_native_governance_is_required_not_reimplemented():
    x=desired_governance_call('/repo','ROLLED_BACK','/state.json')
    assert x['module']=='pchsi.round_control.scientific_round_governance'
    assert x['max_valid_rounds']==10 and x['no_promotion_patience']==3
    assert x['outcome']=='ROLLED_BACK'
