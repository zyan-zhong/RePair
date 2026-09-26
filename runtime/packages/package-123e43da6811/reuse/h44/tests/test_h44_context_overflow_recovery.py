import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from io_utils import canonical, put_json, read_json, sha
from tests.test_h43_post_settlement import _install_no_train_success
from tests.test_h42_post_resume import _fixture

from post_context_recovery import (
    build_context_bounded_projection,
    validate_context_overflow_recovery,
    recover_context_overflow_post,
    provider_request_size_bytes,
)


def _install_context_overflow(monkeypatch, plan):
    import pchsi.cognitive_runtime.orchestrator as o
    from pchsi.cognitive_runtime.p2_bridge import P2TransportError
    calls=[]
    def fail(bundle, call_dir, *, client_request_id):
        calls.append(client_request_id)
        raise P2TransportError(
            'REJECT_TEACHER_CONTEXT_OVERFLOW',
            failure_class='METHOD_CONTEXT_OVERFLOW',
            bytes_transmission_state='CONFIRMED_SENT',
            retry_class='NO_RETRY',
            retry_authority='FROZEN_RUNTIME_POLICY',
            terminal_attempt_status='PROVIDER_REJECTED',
            logical_method_status='SEMANTIC_INVALID',
            counts_as_method_failure=True,
            hard_stop=False,
            http_status=400,
            response_headers={'x-request-id':'overflow-fixture'},
            raw_response=b'{"error":{"message":"context overflow"}}',
        )
    monkeypatch.setattr(o,'execute_via_existing_p2',fail)
    return calls


def _make_overflow_terminal(tmp_path, monkeypatch):
    scientific,recovery,plan,verifier=_fixture(tmp_path)
    # Expand verifier raw branch payload dramatically while keeping state/pair authority compact.
    verifier.update({
        'status':'VERIFIED_COMPLETE',
        'round_id':plan['round_id'],
        'frozen_pair_count':1,
        'planned_branch_count':len(plan['handoff']['branch_plan']),
        'diagnostics':[],
        'hypothesis_scope_notice':plan['scope_notice'],
        'comparison':'SELECTED_REPAIR_VS_PARENT_CONTINUATION_NOT_A3_VS_A2',
        'automatic_environment_effect_assignment':True,
        'human_decision_count':0,
        'training_authorized_by_this_verifier':False,
    })
    verifier['branch_records']=[
        {
            'branch_key_sha256': sha(f'branch-{i}'.encode()),
            'binding_sha256': sha(f'binding-{i}'.encode()),
            'source_state_sha256': plan['states'][i % len(plan['states'])]['source_state_sha256'],
            'source_candidate_sha256': plan['states'][i % len(plan['states'])]['preferred_candidate_sha256'],
            'native_source_fingerprint_sha256': sha(f'fingerprint-{i}'.encode()),
            'arm': 'F0' if i % 2 == 0 else 'F1',
            'replicate_index': i // 2,
            'continuation_seed': i // 2,
            'evidence_complete': True,
            'scientific_outcome_produced': True,
            'terminal_success': bool(i % 3),
            'terminal_reason': 'ENVIRONMENT_TERMINATED',
            'option_environment_step_count': 0 if i % 2 == 0 else 1,
            'policy_call_count_from_source': 3,
            'environment_step_count_from_source': 4,
            'automatic_retry_count': 0,
            'source_replay_report': {'report_sha256': sha(f'replay-{i}'.encode())},
            'policy_calls': [{'large_payload':'x'*120000} for _ in range(2)],
            'environment_transitions_from_source': [{'large_payload':'y'*120000}],
            'evidence_sha256': sha(f'evidence-{i}'.encode()),
        }
        for i in range(max(2,len(plan['states'])*10))
    ]
    verifier.pop('environment_result_package_sha256',None)
    verifier['environment_result_package_sha256']=sha(canonical(verifier))
    (recovery/'verifier'/'ENVIRONMENT_RESULT_PACKAGE.json').unlink()
    put_json(recovery/'verifier'/'ENVIRONMENT_RESULT_PACKAGE.json',verifier)
    cont=read_json(recovery/'ROUND_EXECUTION_TERMINAL.json')
    cont['environment_result_package_sha256']=verifier['environment_result_package_sha256']
    put_json(recovery/'ROUND_EXECUTION_TERMINAL_REPLACEMENT.json',cont)
    (recovery/'ROUND_EXECUTION_TERMINAL.json').unlink()
    (recovery/'ROUND_EXECUTION_TERMINAL_REPLACEMENT.json').replace(recovery/'ROUND_EXECUTION_TERMINAL.json')
    calls=_install_context_overflow(monkeypatch,plan)
    from post_resume import resume
    first=resume(recovery)
    assert first['status']=='CURRENT_CAUSAL_POST_CONTINUATION_NOT_TERMINAL_NO_RESEND'
    assert len(calls)==1
    from post_settlement import settle_existing_post
    settled=settle_existing_post(recovery,execute_remediation=True)
    assert settled['status']=='POST_METHOD_TERMINAL_NO_RESEND'
    assert settled['failure_class']=='METHOD_CONTEXT_OVERFLOW'
    return scientific,recovery,plan,verifier,calls


def test_compact_projection_preserves_effect_authority_and_omits_raw_branch_payload(tmp_path, monkeypatch):
    _,recovery,plan,verifier,_=_make_overflow_terminal(tmp_path,monkeypatch)
    compact=build_context_bounded_projection(recovery,plan,verifier)
    env=compact['environment_result_package_projection']
    assert env['source_environment_result_package_sha256']==verifier['environment_result_package_sha256']
    assert env['stable_effect_counts']==verifier['stable_effect_counts']
    assert env['state_results']==verifier['state_results']
    assert env['pair_results']==verifier['pair_results']
    assert len(env['branch_evidence_index'])==len(verifier['branch_records'])
    text=json.dumps(compact,sort_keys=True)
    assert 'large_payload' not in text
    for row in env['branch_evidence_index']:
        assert 'policy_calls' not in row
        assert 'environment_transitions_from_source' not in row
        assert 'intervention_sequence' not in row


def test_context_overflow_recovery_requires_exact_method_terminal(tmp_path, monkeypatch):
    _,recovery,plan,verifier,_=_make_overflow_terminal(tmp_path,monkeypatch)
    validated=validate_context_overflow_recovery(recovery)
    assert validated['classification']['failure_class']=='METHOD_CONTEXT_OVERFLOW'
    terminal=read_json(recovery/'ROUND_EXECUTION_POST_SETTLEMENT_TERMINAL.json')
    terminal['failure_class']='METHOD_PROVIDER_REJECTION'
    terminal['settlement_terminal_sha256']=sha(canonical({k:v for k,v in terminal.items() if k!='settlement_terminal_sha256'}))
    (recovery/'ROUND_EXECUTION_POST_SETTLEMENT_TERMINAL.json').unlink()
    put_json(recovery/'ROUND_EXECUTION_POST_SETTLEMENT_TERMINAL.json',terminal)
    with pytest.raises(ValueError,match='CONTEXT_RECOVERY_SETTLEMENT_NOT_CONTEXT_OVERFLOW'):
        validate_context_overflow_recovery(recovery)


def test_context_bounded_request_is_under_authority_budget_and_not_same_logical_call(tmp_path, monkeypatch):
    _,recovery,plan,verifier,initial_calls=_make_overflow_terminal(tmp_path,monkeypatch)
    # Swap transport to accepted NO_TRAIN for the new context-bounded logical call.
    success_calls=_install_no_train_success(monkeypatch,plan)
    result=recover_context_overflow_post(recovery,execute_call=True)
    assert result['training_recommendation']=='NO_TRAIN'
    assert result['provider_calls_this_context_recovery']==1
    assert len(success_calls)==1
    assert result['same_logical_call_resend_count']==0
    assert result['original_method_failure_preserved'] is True
    assert result['context_recovery_logical_call_id'] != result['original_logical_call_id']
    authority=read_json(recovery/'post'/'context_bounded_recovery'/'POST_CONTEXT_BUDGET_POLICY_V1.json')
    request=read_json(recovery/'post'/'context_bounded_recovery'/'request_preflight.json')
    assert request['provider_request_body_bytes'] <= authority['max_provider_request_body_bytes']
    assert request['full_environment_package_bytes'] > request['compact_environment_projection_bytes']


def test_context_bounded_recovery_is_one_shot(tmp_path, monkeypatch):
    _,recovery,plan,verifier,_=_make_overflow_terminal(tmp_path,monkeypatch)
    calls=_install_context_overflow(monkeypatch,plan)
    first=recover_context_overflow_post(recovery,execute_call=True)
    assert first['status']=='POST_CONTEXT_BOUNDED_RECOVERY_TERMINAL_NO_SECOND_CALL'
    assert len(calls)==1
    second=recover_context_overflow_post(recovery,execute_call=True)
    assert second==first
    assert len(calls)==1


def test_current_branch_cardinality_is_not_a_context_recovery_source_constant():
    src=Path(__file__).parents[1]/'post_context_recovery.py'
    text=src.read_text(encoding='utf-8')
    assert '== 20' not in text
    assert 'range(20)' not in text
    assert 'CURRENT_BRANCH_COUNT = 20' not in text


def test_package_verifier_covers_context_recovery_runner():
    src=(Path(__file__).parents[1]/'verify_package.py').read_text(encoding='utf-8')
    assert 'RUN_RECOVER_CONTEXT_OVERFLOW_POST.sh' in src


def test_package_identity_supersedes_exact_h43_release():
    identity=read_json(Path(__file__).parents[1]/'PACKAGE_IDENTITY.json')
    expected='PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_3'
    assert identity['supersedes_package']==expected
    assert identity['supersedes_package_name']==expected


def test_context_budget_policy_rejects_silent_provider_truncation():
    import post_context_recovery as m
    policy=read_json(Path(__file__).parents[1]/'assets'/'POST_CONTEXT_BUDGET_POLICY_V1.json')
    manifest={'truncation':'auto','requested_model':'gpt-5.6-sol'}
    with pytest.raises(ValueError,match='CONTEXT_RECOVERY_PROVIDER_TRUNCATION_NOT_DISABLED'):
        m._validate_context_policy(policy,manifest)


def test_context_budget_policy_is_one_shot_and_cardinality_agnostic():
    import post_context_recovery as m
    policy=read_json(Path(__file__).parents[1]/'assets'/'POST_CONTEXT_BUDGET_POLICY_V1.json')
    manifest={'truncation':'disabled','requested_model':'gpt-5.6-sol'}
    m._validate_context_policy(policy,manifest)
    changed=dict(policy)
    changed['max_new_context_bounded_logical_calls_after_full_projection_overflow']=2
    with pytest.raises(ValueError,match='CONTEXT_RECOVERY_MAX_NEW_LOGICAL_CALLS_NOT_ONE'):
        m._validate_context_policy(changed,manifest)
