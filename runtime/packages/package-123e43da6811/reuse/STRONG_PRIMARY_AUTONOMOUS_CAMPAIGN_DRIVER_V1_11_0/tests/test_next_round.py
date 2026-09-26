from next_round_driver import next_round_action

def test_stop_does_not_launch():
    assert next_round_action({'stop':True,'reason':'MAX_SCIENTIFIC_ROUNDS_REACHED'},'pi1')['launch'] is False

def test_continue_launches_without_human_choice():
    x=next_round_action({'stop':False,'reason':'CONTINUE'},'pi1')
    assert x['launch'] is True and x['human_decision_required'] is False
