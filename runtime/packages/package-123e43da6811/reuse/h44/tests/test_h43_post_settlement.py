import json
from types import SimpleNamespace

import pytest

from io_utils import canonical, read_json, sha
from post_resume import resume
from tests.test_h42_post_resume import _fixture


def _install_initial_transport_failure(monkeypatch, *, retry_class, bytes_state, failure_class, http_status=None, hard_stop=False):
    import pchsi.cognitive_runtime.orchestrator as o
    from pchsi.cognitive_runtime.p2_bridge import P2TransportError

    calls=[]
    def fail(bundle, call_dir, *, client_request_id):
        calls.append(client_request_id)
        raise P2TransportError(
            failure_class,
            failure_class=failure_class,
            bytes_transmission_state=bytes_state,
            retry_class=retry_class,
            retry_authority='HUMAN_DISPOSITION' if retry_class in ('SAFE_PRE_SEND','SAFE_PROVIDER_REJECTION') else 'FROZEN_RUNTIME_POLICY',
            terminal_attempt_status='INFRASTRUCTURE_ERROR' if bytes_state=='NOT_SENT' else 'PROVIDER_REJECTED',
            logical_method_status='INFRASTRUCTURE_UNAVAILABLE',
            counts_as_method_failure=False,
            hard_stop=hard_stop,
            http_status=http_status,
            response_headers={},
            raw_response=(b'{}' if http_status is not None else None),
        )
    monkeypatch.setattr(o,'execute_via_existing_p2',fail)
    return calls


def _install_no_train_success(monkeypatch, plan):
    import pchsi.cognitive_runtime.orchestrator as o
    calls=[]
    def ok(bundle, call_dir, *, client_request_id):
        calls.append(client_request_id)
        projection=bundle['input_projection']
        payload={
            'schema_id':'API_RESEARCHER_POST_PRIMARY_V1','schema_version':1,
            'round_id':plan['round_id'],
            'primary_pre_record_sha256':projection['primary_pre_record_sha256'],
            'environment_result_package_sha256':projection['environment_result_package_sha256'],
            'protocol_audit':'verified complete fixture','observed_outcome':'neutral',
            'numerator':0,'denominator':len(plan['states']),'unexpected_evidence':[],
            'hypothesis_status':'UNRESOLVED','alternative_explanations':['fixture'],
            'researcher_training_recommendation':'NO_TRAIN','researcher_promotion_recommendation':'HOLD',
            'lesson':'fixture','next_round_implication':'retain parent','primary_record_sha256':'0'*64,
        }
        response={
            'id':'response-h43-fixture','model':bundle['provider_request']['model'],'status':'completed',
            'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(payload)}]}],
            'usage':{'input_tokens':10,'output_tokens':10,'output_tokens_details':{'reasoning_tokens':0}},
        }
        return SimpleNamespace(http_status=200,response_headers={'x-request-id':'fixture-h43'},provider_http_request_id='fixture-h43',raw_response=canonical(response))
    monkeypatch.setattr(o,'execute_via_existing_p2',ok)
    return calls


def _create_h42_nonterminal(tmp_path, monkeypatch, **failure):
    scientific,recovery,plan,verifier=_fixture(tmp_path)
    calls=_install_initial_transport_failure(monkeypatch, **failure)
    result=resume(recovery)
    assert result['status']=='CURRENT_CAUSAL_POST_CONTINUATION_NOT_TERMINAL_NO_RESEND'
    assert len(calls)==1
    return scientific,recovery,plan,verifier


def test_safe_pre_send_is_classified_for_one_autonomous_remediation(tmp_path, monkeypatch):
    _,recovery,plan,_=_create_h42_nonterminal(
        tmp_path,monkeypatch,retry_class='SAFE_PRE_SEND',bytes_state='NOT_SENT',
        failure_class='PRE_SEND_INFRASTRUCTURE_UNAVAILABLE')
    from post_settlement import classify_existing_post
    row=classify_existing_post(recovery)
    assert row['disposition']=='ONE_AUTONOMOUS_INFRASTRUCTURE_REMEDIATION_ELIGIBLE'
    assert row['provider_resend_same_logical_call_authorized'] is False
    assert row['new_remediation_logical_call_authorized'] is True
    assert row['request_body_sha256']


def test_ambiguous_post_send_is_never_retried(tmp_path, monkeypatch):
    scientific,recovery,plan,verifier=_fixture(tmp_path)
    import pchsi.cognitive_runtime.orchestrator as o
    calls=[]
    def ambiguous(bundle, call_dir, *, client_request_id):
        calls.append(client_request_id)
        raise RuntimeError('after-send ambiguity fixture')
    monkeypatch.setattr(o,'execute_via_existing_p2',ambiguous)
    result=resume(recovery)
    assert len(calls)==1
    from post_settlement import settle_existing_post
    before=len(calls)
    settled=settle_existing_post(recovery,execute_remediation=True)
    assert len(calls)==before
    assert settled['status']=='POST_METHOD_TERMINAL_NO_RESEND'
    assert settled['provider_calls_this_settlement']==0


def test_safe_pre_send_gets_exactly_one_new_logical_call_and_routes_no_train(tmp_path, monkeypatch):
    _,recovery,plan,_=_create_h42_nonterminal(
        tmp_path,monkeypatch,retry_class='SAFE_PRE_SEND',bytes_state='NOT_SENT',
        failure_class='PRE_SEND_INFRASTRUCTURE_UNAVAILABLE')
    initial_call_dirs=list((recovery/'post'/'calls').iterdir())
    assert len(initial_call_dirs)==1
    initial=read_json(initial_call_dirs[0]/'logical_call.json')
    success_calls=_install_no_train_success(monkeypatch,plan)
    from post_settlement import settle_existing_post
    settled=settle_existing_post(recovery,execute_remediation=True)
    assert settled['training_recommendation']=='NO_TRAIN'
    assert settled['provider_calls_this_settlement']==1
    assert len(success_calls)==1
    remediation_dirs=list((recovery/'post'/'remediation_calls').iterdir())
    assert len(remediation_dirs)==1
    remediation=read_json(remediation_dirs[0]/'logical_call.json')
    assert remediation['logical_call_id'] != initial['logical_call_id']
    assert remediation['request_body_sha256'] == initial['request_body_sha256']
    assert (recovery/'post'/'NO_TRAINING_UPDATE_V1.json').is_file()


def test_safe_provider_rejection_is_eligible_but_only_one_remediation_attempt(tmp_path, monkeypatch):
    _,recovery,plan,_=_create_h42_nonterminal(
        tmp_path,monkeypatch,retry_class='SAFE_PROVIDER_REJECTION',bytes_state='CONFIRMED_SENT',
        failure_class='PROVIDER_TRANSIENT_UNAVAILABLE',http_status=503)
    from post_settlement import classify_existing_post, settle_existing_post
    row=classify_existing_post(recovery)
    assert row['disposition']=='ONE_AUTONOMOUS_INFRASTRUCTURE_REMEDIATION_ELIGIBLE'
    # Remediation itself fails pre-send; the next invocation must adopt that terminal and never send again.
    retry_calls=_install_initial_transport_failure(monkeypatch,retry_class='SAFE_PRE_SEND',bytes_state='NOT_SENT',failure_class='PRE_SEND_INFRASTRUCTURE_UNAVAILABLE')
    first=settle_existing_post(recovery,execute_remediation=True)
    assert len(retry_calls)==1
    assert first['status']=='POST_REMEDIATION_TERMINAL_NO_SECOND_RETRY'
    second=settle_existing_post(recovery,execute_remediation=True)
    assert len(retry_calls)==1
    assert second==first


def test_unknown_nonaccepted_method_terminal_is_fail_closed_without_provider_call(tmp_path, monkeypatch):
    scientific,recovery,plan,verifier=_fixture(tmp_path)
    import pchsi.cognitive_runtime.orchestrator as o
    calls=[]
    def schema_invalid(bundle, call_dir, *, client_request_id):
        calls.append(client_request_id)
        response={'id':'bad','model':bundle['provider_request']['model'],'status':'completed','output':[],'usage':{}}
        return SimpleNamespace(http_status=200,response_headers={},provider_http_request_id='bad',raw_response=canonical(response))
    monkeypatch.setattr(o,'execute_via_existing_p2',schema_invalid)
    result=resume(recovery)
    assert len(calls)==1
    from post_settlement import settle_existing_post
    before=len(calls)
    settled=settle_existing_post(recovery,execute_remediation=True)
    assert len(calls)==before
    assert settled['status']=='POST_METHOD_TERMINAL_NO_RESEND'
    assert settled['provider_calls_this_settlement']==0


def test_settlement_rejects_non_verified_complete_continuation(tmp_path, monkeypatch):
    _,recovery,plan,_=_create_h42_nonterminal(
        tmp_path,monkeypatch,retry_class='SAFE_PRE_SEND',bytes_state='NOT_SENT',
        failure_class='PRE_SEND_INFRASTRUCTURE_UNAVAILABLE')
    cont=read_json(recovery/'ROUND_EXECUTION_CONTINUATION_TERMINAL.json')
    cont['verifier_status']='NOT_COMPLETE'
    cont['continuation_terminal_sha256']=sha(canonical({k:v for k,v in cont.items() if k!='continuation_terminal_sha256'}))
    (recovery/'ROUND_EXECUTION_CONTINUATION_TERMINAL.json').unlink()
    from io_utils import put_json
    put_json(recovery/'ROUND_EXECUTION_CONTINUATION_TERMINAL.json',cont)
    from post_settlement import classify_existing_post
    with pytest.raises(ValueError, match='SETTLEMENT_VERIFIER_NOT_COMPLETE'):
        classify_existing_post(recovery)
