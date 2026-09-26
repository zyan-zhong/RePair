from campaign_contract import transition_after_round, validate_handoff

def test_waits_for_v110_without_competing():
    assert transition_after_round({'phase':'WAITING_FOR_VERIFIER'})['action']=='WAIT_PREDECESSOR'

def test_requires_exact_hydrated_gap_and_post():
    try:
        validate_handoff({'schema_id':'X'}, {'schema_id':'Y'})
    except ValueError as e:
        assert 'V110' in str(e)
    else:
        raise AssertionError('expected fail closed')

def test_no_train_route_is_automatic():
    x=transition_after_round({'phase':'HYDRATED_DOWNSTREAM_GAP','route':'NO_TRAINING_UPDATE'})
    assert x['action']=='AUTO_CLOSE_NO_TRAIN'

def test_train_route_is_automatic():
    x=transition_after_round({'phase':'HYDRATED_DOWNSTREAM_GAP','route':'VERIFIED_BENEFIT_TRAINING'})
    assert x['action']=='AUTO_TRAIN_EVALUATE'
