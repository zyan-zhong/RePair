from dataclasses import fields

import pytest

from pchsi.round_control.campaign_authority import freeze_campaign_startup_authority
from pchsi.round_control.scientific_round_governance import new_scientific_round_governance, advance_scientific_round_governance
from pchsi.round_control.rollout_collection import RoundRolloutExecutionBindingV1
from test_api import request


def governance(outcome='NO_TRAINING_UPDATE', maximum=7):
    authority = freeze_campaign_startup_authority(campaign_id='fixture-campaign',
        requested_max_valid_rounds=maximum, no_promotion_patience=4,
        max_infrastructure_attempt_restarts=1, force_run_all_rounds=False,
        campaign_purpose_sha256='a'*64, heldout_firewall_sha256='b'*64, paper_export_contract_sha256='c'*64)
    return advance_scientific_round_governance(new_scientific_round_governance(authority=authority), outcome=outcome)


def result(outcome='NO_TRAINING_UPDATE'):
    start = request()
    return {**start, 'outcome': outcome,
        'next_parent_policy_id': 'new-policy' if outcome == 'PROMOTED' else start['parent_policy_id'],
        'next_parent_policy_artifact_sha256': 'b'*64 if outcome == 'PROMOTED' else start['parent_policy_artifact_sha256']}


def inputs():
    return {'runtime_file_sha256':'c'*64, 'profile_file_sha256':'d'*64,
            'memory_file_sha256':'e'*64, 'snapshot_sha256':'f'*64,
            'token_budget_contract_sha256':'a'*64, 'train_manifest_sha256':'a'*64}


@pytest.mark.parametrize('outcome', ['NO_TRAINING_UPDATE','PROMOTED','ROLLED_BACK'])
def test_native_next_request_refreshes_policy_memory_and_attempt(outcome):
    from continuity_binding.next_request import derive_next_request
    nxt = derive_next_request(start=request(), result=result(outcome), governance=governance(outcome),
                              resolved_inputs=inputs(), closure_sha256='9'*64)
    assert nxt.parent_policy_id == result(outcome)['next_parent_policy_id']
    assert nxt.parent_policy_artifact_sha256 == result(outcome)['next_parent_policy_artifact_sha256']
    assert nxt.round_start_memory_snapshot_sha256 == 'f'*64
    assert nxt.round_memory_runtime_authority_sha256 == 'e'*64
    assert nxt.policy_runtime_binding_sha256 == 'c'*64
    assert nxt.round_id != request()['round_id']
    assert nxt.execution_attempt_id != request()['execution_attempt_id']
    assert nxt.request_sha256 != request()['request_sha256']
    assert nxt.to_dict()['selection_rule'] == 'FULL_FROZEN_TRAIN_UPDATE_UNIVERSE'


def test_governor_stop_creates_no_request():
    from continuity_binding.next_request import derive_next_request
    with pytest.raises(ValueError, match='GOVERNOR_STOP'):
        derive_next_request(start=request(), result=result(), governance=governance(maximum=1),
                            resolved_inputs=inputs(), closure_sha256='9'*64)


def test_invalid_attempt_is_not_a_closed_round():
    from continuity_binding.next_request import derive_next_request
    with pytest.raises(ValueError, match='INVALID_ATTEMPT'):
        derive_next_request(start=request(), result=result('PROTOCOL_INFRA_INVALID'),
            governance=governance('PROTOCOL_INFRA_INVALID'), resolved_inputs=inputs(), closure_sha256='9'*64)


def test_next_execution_binding_uses_native_fresh_request():
    from continuity_binding.next_request import rebind_execution
    start = request()
    source = RoundRolloutExecutionBindingV1(request_sha256=start['request_sha256'],
        scientific_execution_authorized=True,
        **{f.name:'a'*64 for f in fields(RoundRolloutExecutionBindingV1)
           if f.name.endswith('_sha256') and f.name not in {'request_sha256','binding_sha256'}})
    nxt = rebind_execution(source.to_dict(), start['request_sha256'], 'b'*64)
    assert nxt.request_sha256 == 'b'*64
    assert nxt.binding_sha256 != source.binding_sha256
    assert nxt.rollout_control_source_sha256 == source.rollout_control_source_sha256


def test_governor_tampering_not_accepted():
    from continuity_binding.next_request import derive_next_request
    state = governance()
    object.__setattr__(state, 'max_valid_rounds', 99)
    with pytest.raises(ValueError, match='GOVERNANCE'):
        derive_next_request(start=request(), result=result(), governance=state,
                            resolved_inputs=inputs(), closure_sha256='9'*64)
