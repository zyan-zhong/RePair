import pytest
from pchsi.round_control.lifecycle import RoundLifecycleV1, RoundStageV1
from pchsi.round_control.no_training_update import freeze_no_training_update
from pchsi.round_control.orchestrator import next_action_for

def _post():
    s=RoundLifecycleV1.new(round_id='r',parent_policy_id='pi')
    for stage in (RoundStageV1.EVIDENCE_READY,RoundStageV1.ANALYSIS_READY,RoundStageV1.PRE_PLAN_FROZEN,RoundStageV1.EXPERIMENTS_COMPLETED,RoundStageV1.POST_PLAN_FROZEN):
        s=s.advance(stage,evidence_sha256='a'*64)
    return s

def test_valid_no_benefit_round_can_close_without_training():
    s=_post().advance(RoundStageV1.NO_TRAINING_UPDATE,evidence_sha256='b'*64)
    a=next_action_for(s)
    assert a.component_ids==()
    assert a.expected_output_stage is RoundStageV1.ROUND_CLOSED
    s=s.advance(RoundStageV1.ROUND_CLOSED,evidence_sha256='c'*64)
    assert s.current_stage is RoundStageV1.ROUND_CLOSED

def test_no_training_receipt_is_fail_closed():
    r=freeze_no_training_update(round_id='r',parent_policy_id='pi',post_plan_sha256='a'*64,
        verifier_result_sha256='b'*64,verified_benefit_count=0,verified_harm_count=1,
        verified_neutral_count=2,verified_uncertain_count=0,scientifically_valid_round=True)
    assert r.scientific_attempt_consumed and r.training_execution_count==0 and r.parent_policy_retained
    with pytest.raises(ValueError):
        freeze_no_training_update(round_id='r',parent_policy_id='pi',post_plan_sha256='a'*64,
            verifier_result_sha256='b'*64,verified_benefit_count=1,verified_harm_count=0,
            verified_neutral_count=0,verified_uncertain_count=0,scientifically_valid_round=True)
