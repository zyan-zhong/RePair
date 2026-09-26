from __future__ import annotations
import fcntl,json,os
from pathlib import Path
import pytest
from v110_boundary import writer_lock_state, decide_takeover_action


def _write(p:Path,v:dict):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v),encoding='utf-8')


def test_active_v110_writer_is_observe_only(tmp_path:Path):
    closure=tmp_path/'closure'; closure.mkdir()
    p=closure/'.tail_writer.lock'; fd=os.open(p,os.O_RDWR|os.O_CREAT,0o600); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        assert writer_lock_state(closure)=='ACTIVE'
        x=decide_takeover_action(closure_root=closure,verifier_ready=True)
        assert x['action']=='WAIT_V110_WRITER'
        assert x['side_effect_authorized'] is False
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN); os.close(fd)


def test_inactive_with_accepted_call_prefers_adoption(tmp_path:Path):
    closure=tmp_path/'closure'; closure.mkdir(); (closure/'.tail_writer.lock').touch()
    call=closure/'hydrated_planner_post_runtime'/'c'; call.mkdir(parents=True)
    _write(call/'method_result.json',{'status':'ACCEPTED'})
    _write(call/'validated_artifact.json',{'schema_id':'API_RESEARCHER_POST_PRIMARY_V1'})
    x=decide_takeover_action(closure_root=closure,verifier_ready=True)
    assert x['action']=='ADOPT_ACCEPTED_V110_POST'
    assert x['provider_resend_authorized'] is False


def test_inactive_without_any_post_allows_exactly_one_post_worker(tmp_path:Path):
    closure=tmp_path/'closure'; closure.mkdir(); (closure/'.tail_writer.lock').touch()
    x=decide_takeover_action(closure_root=closure,verifier_ready=True)
    assert x['action']=='RUN_V110_POST_ONCE'
    assert x['provider_resend_authorized'] is False
    assert x['fresh_single_send_authorized'] is True


def test_partial_call_hard_stops_no_resend(tmp_path:Path):
    closure=tmp_path/'closure'; closure.mkdir(); (closure/'.tail_writer.lock').touch()
    call=closure/'hydrated_planner_post_runtime'/'c'; call.mkdir(parents=True)
    _write(call/'method_result.json',{'status':'STARTED'})
    x=decide_takeover_action(closure_root=closure,verifier_ready=True)
    assert x['action']=='FAIL_CLOSED_PARTIAL_POST_NO_RESEND'
    assert x['side_effect_authorized'] is False
