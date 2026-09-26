from campaign_contract import classify_v110_boundary


def test_v110_post_only_zero_benefit_routes_to_recovery():
    post={'schema_id':'STRONG_PRIMARY_R1_HYDRATED_PLANNER_POST_ACCEPTED_V1','round_id':'R1','route':'NO_TRAINING_UPDATE','result_package_sha256':'a'*64,'verified_benefit_count':0}
    gate={'round_id':'R1','result_package_sha256':'a'*64,'stable_effect_counts':{'BENEFIT':0,'HARM':1,'NEUTRAL':0,'UNCERTAIN':0},'scientific_attempt_consumed':True}
    x=classify_v110_boundary(gap=None,post=post,verifier_gate=gate)
    assert x['action']=='RECOVER_NO_TRAIN_POST_ONLY'


def test_v110_positive_benefit_requires_exact_gap():
    post={'schema_id':'STRONG_PRIMARY_R1_HYDRATED_PLANNER_POST_ACCEPTED_V1','round_id':'R1','route':'VERIFIED_BENEFIT_TRAINING','result_package_sha256':'a'*64,'verified_benefit_count':1}
    gate={'round_id':'R1','result_package_sha256':'a'*64,'stable_effect_counts':{'BENEFIT':1,'HARM':0,'NEUTRAL':0,'UNCERTAIN':0},'scientific_attempt_consumed':True}
    x=classify_v110_boundary(gap=None,post=post,verifier_gate=gate)
    assert x['action']=='WAIT_EXACT_TRAIN_GAP_NO_FABRICATION'
