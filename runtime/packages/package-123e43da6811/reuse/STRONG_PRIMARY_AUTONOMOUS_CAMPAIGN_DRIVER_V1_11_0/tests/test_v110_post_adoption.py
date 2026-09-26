from __future__ import annotations
import json
from pathlib import Path
import pytest
from v110_post_adoption import adopt_accepted_v110_post


def _write(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def _gate(benefit=0):
    return {'round_id':'R1','primary_pre_record_sha256':'a'*64,'result_package_sha256':'b'*64,
            'stable_effect_counts':{'BENEFIT':benefit,'HARM':1 if benefit==0 else 0,'NEUTRAL':0,'UNCERTAIN':0},
            'scientific_attempt_consumed':True}


def _artifact():
    return {'schema_id':'API_RESEARCHER_POST_PRIMARY_V1','schema_version':1,'round_id':'R1',
            'primary_pre_record_sha256':'a'*64,'environment_result_package_sha256':'b'*64,
            'protocol_audit':'ok','observed_outcome':'obs','numerator':1,'denominator':1,
            'unexpected_evidence':[],'hypothesis_status':'SUPPORTED','alternative_explanations':[],
            'researcher_training_recommendation':'verifier governed',
            'researcher_promotion_recommendation':'HOLD','lesson':'l','next_round_implication':'n',
            'primary_record_sha256':'c'*64}


def _authority(root: Path):
    _write(root/'HYDRATED_POST_INPUT_AUTHORITY_V1.json', {
        'schema_id':'HYDRATED_POST_INPUT_AUTHORITY_V1','schema_version':1,'round_id':'R1',
        'result_package_sha256':'b'*64,'primary_pre_record_sha256':'a'*64,'memory_pack_sha256':'d'*64,
        'verifier_state_result_count':1,'verifier_pair_result_count':1,
        'hash_only_scientific_input_forbidden':True,'human_scientific_decision_count':0,
    })


def test_adopts_exactly_one_accepted_call_without_resend(tmp_path: Path):
    closure=tmp_path/'closure'; _authority(closure)
    call=closure/'hydrated_planner_post_runtime'/'call1'
    _write(call/'method_result.json', {'status':'ACCEPTED'})
    _write(call/'validated_artifact.json', _artifact())
    x=adopt_accepted_v110_post(closure_root=closure, verifier_gate=_gate())
    assert x['adopted'] is True and x['route']=='NO_TRAINING_UPDATE'
    assert x['call_dir']==str(call.resolve())
    assert x['provider_resend_count']==0
    assert x['memory_pack_sha256']=='d'*64


def test_partial_call_is_not_resent_or_adopted(tmp_path: Path):
    closure=tmp_path/'closure'; _authority(closure)
    call=closure/'hydrated_planner_post_runtime'/'call1'
    _write(call/'method_result.json', {'status':'STARTED'})
    with pytest.raises(ValueError, match='V110_POST_CALL_PARTIAL_NO_RESEND'):
        adopt_accepted_v110_post(closure_root=closure, verifier_gate=_gate())


def test_multiple_accepted_calls_fail_closed(tmp_path: Path):
    closure=tmp_path/'closure'; _authority(closure)
    for name in ('c1','c2'):
        call=closure/'hydrated_planner_post_runtime'/name
        _write(call/'method_result.json', {'status':'ACCEPTED'})
        _write(call/'validated_artifact.json', _artifact())
    with pytest.raises(ValueError, match='V110_ACCEPTED_POST_CALL_AMBIGUOUS'):
        adopt_accepted_v110_post(closure_root=closure, verifier_gate=_gate())
