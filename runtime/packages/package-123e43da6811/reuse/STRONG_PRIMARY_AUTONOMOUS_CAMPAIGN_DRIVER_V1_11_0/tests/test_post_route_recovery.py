from __future__ import annotations
import pytest
from post_route_recovery import validate_primary_post_and_route


def gate(benefit: int):
    return {
        'round_id':'R1',
        'result_package_sha256':'b'*64,
        'stable_effect_counts':{
            'BENEFIT':benefit,'HARM':1 if benefit == 0 else 0,'NEUTRAL':0,'UNCERTAIN':0,
        },
        'scientific_attempt_consumed':True,
    }


def post(promo='HOLD'):
    return {
        'schema_id':'API_RESEARCHER_POST_PRIMARY_V1','schema_version':1,
        'round_id':'R1','primary_pre_record_sha256':'a'*64,
        'environment_result_package_sha256':'b'*64,
        'protocol_audit':'ok','observed_outcome':'observed','numerator':1,'denominator':1,
        'unexpected_evidence':[],'hypothesis_status':'SUPPORTED','alternative_explanations':[],
        'researcher_training_recommendation':'use only independently verified Benefit evidence',
        'researcher_promotion_recommendation':promo,
        'lesson':'lesson','next_round_implication':'next','primary_record_sha256':'c'*64,
    }


def test_zero_benefit_route_comes_from_verifier_not_free_text_post():
    x=validate_primary_post_and_route(post=post(), verifier_gate=gate(0))
    assert x['route']=='NO_TRAINING_UPDATE'
    assert x['verified_benefit_count']==0
    assert x['post_effect_authority_used'] is False


def test_positive_benefit_route_comes_from_verifier():
    x=validate_primary_post_and_route(post=post(), verifier_gate=gate(2))
    assert x['route']=='VERIFIED_BENEFIT_TRAINING'
    assert x['verified_benefit_count']==2


def test_current_fixed_head_post_schema_does_not_require_nonexistent_training_recommendation_object():
    x=validate_primary_post_and_route(post=post(), verifier_gate=gate(0))
    assert x['post_schema_id']=='API_RESEARCHER_POST_PRIMARY_V1'


def test_planner_promotion_recommendation_is_descriptive_not_authority():
    x=validate_primary_post_and_route(post=post('PROMOTE'), verifier_gate=gate(1))
    assert x['route']=='VERIFIED_BENEFIT_TRAINING'
    assert x['post_promotion_authority_used'] is False
