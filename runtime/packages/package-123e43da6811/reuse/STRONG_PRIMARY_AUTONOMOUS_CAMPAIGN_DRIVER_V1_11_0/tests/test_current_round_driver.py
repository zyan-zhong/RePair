from __future__ import annotations
import json
from pathlib import Path
import current_round_driver as d


def _write(p:Path,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding='utf-8')


def test_active_v110_is_observation_only(tmp_path,monkeypatch):
    monkeypatch.setattr(d,'verifier_files_ready',lambda p:True)
    monkeypatch.setattr(d,'decide_takeover_action',lambda **kw:{'action':'WAIT_V110_WRITER'})
    x=d.advance_current_round(repo=tmp_path,state_root=tmp_path/'s',closure_root=tmp_path/'c',prepared_root=tmp_path/'p',upstream_root=tmp_path/'u',v110_package_root=tmp_path/'v')
    assert x=={'phase':'WAIT_V110_WRITER','terminal':False,'side_effect':False}
    assert not (tmp_path/'s'/d.ADOPT).exists()


def test_accepted_post_is_adopted_without_provider_resend(tmp_path,monkeypatch):
    gate={'round_id':'R1','parent_policy_id':'PI0','result_package_sha256':'b'*64,'primary_pre_record_sha256':'a'*64,'stable_effect_counts':{'BENEFIT':1,'HARM':0,'NEUTRAL':0,'UNCERTAIN':0},'scientific_attempt_consumed':True}
    adopted={'schema_id':'STRONG_PRIMARY_V1_11_ADOPTED_V110_PLANNER_POST_V1','schema_version':1,'round_id':'R1','route':'VERIFIED_BENEFIT_TRAINING','verified_benefit_count':1,'stable_effect_counts':gate['stable_effect_counts'],'result_package_sha256':'b'*64,'post_plan_sha256':'c'*64,'call_dir':'/x','provider_resend_count':0}
    monkeypatch.setattr(d,'verifier_files_ready',lambda p:True)
    monkeypatch.setattr(d,'decide_takeover_action',lambda **kw:{'action':'ADOPT_ACCEPTED_V110_POST'})
    monkeypatch.setattr(d,'load_verifier_gate',lambda **kw:gate)
    monkeypatch.setattr(d,'adopt_accepted_v110_post',lambda **kw:adopted)
    def forbidden(**kw): raise AssertionError('provider resend')
    x=d.advance_current_round(repo=tmp_path,state_root=tmp_path/'s',closure_root=tmp_path/'c',prepared_root=tmp_path/'p',upstream_root=tmp_path/'u',v110_package_root=tmp_path/'v',run_post=forbidden)
    assert x['phase']=='VERIFIED_BENEFIT_ROUTE_BOUND'
    assert json.loads((tmp_path/'s'/d.ADOPT).read_text())['provider_resend_count']==0
    assert json.loads((tmp_path/'s'/d.BLOCKED).read_text())['full_max10_autonomous_campaign_released'] is False


def test_zero_benefit_calls_correct_native_no_train_after_adoption(tmp_path,monkeypatch):
    gate={'round_id':'R1','parent_policy_id':'PI0','result_package_sha256':'b'*64,'primary_pre_record_sha256':'a'*64,'stable_effect_counts':{'BENEFIT':0,'HARM':1,'NEUTRAL':0,'UNCERTAIN':0},'scientific_attempt_consumed':True}
    adopted={'schema_id':'STRONG_PRIMARY_V1_11_ADOPTED_V110_PLANNER_POST_V1','schema_version':1,'round_id':'R1','route':'NO_TRAINING_UPDATE','verified_benefit_count':0,'stable_effect_counts':gate['stable_effect_counts'],'result_package_sha256':'b'*64,'post_plan_sha256':'c'*64,'call_dir':'/x','provider_resend_count':0}
    monkeypatch.setattr(d,'verifier_files_ready',lambda p:True)
    monkeypatch.setattr(d,'decide_takeover_action',lambda **kw:{'action':'ADOPT_ACCEPTED_V110_POST'})
    monkeypatch.setattr(d,'load_verifier_gate',lambda **kw:gate)
    monkeypatch.setattr(d,'adopt_accepted_v110_post',lambda **kw:adopted)
    monkeypatch.setattr(d,'build_no_training_update',lambda **kw:{'schema_id':'NO_TRAINING_UPDATE_V1','round_id':'R1','training_execution_count':0,'parent_policy_retained':True})
    x=d.advance_current_round(repo=tmp_path,state_root=tmp_path/'s',closure_root=tmp_path/'c',prepared_root=tmp_path/'p',upstream_root=tmp_path/'u',v110_package_root=tmp_path/'v')
    assert x['phase']=='NO_TRAINING_UPDATE_APPLIED'
    assert (tmp_path/'s'/d.NO_TRAIN).is_file()
