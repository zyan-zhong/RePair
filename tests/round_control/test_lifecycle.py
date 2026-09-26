from pchsi.round_control.lifecycle import (
    RoundStageV1,
    RoundLifecycleV1,
)


def test_lifecycle_accepts_exact_frozen_transition_chain() -> None:
    state = RoundLifecycleV1.new(
        round_id="clean-r001",
        parent_policy_id="pi0-clean",
    )
    chain = (
        RoundStageV1.EVIDENCE_READY,
        RoundStageV1.ANALYSIS_READY,
        RoundStageV1.PRE_PLAN_FROZEN,
        RoundStageV1.EXPERIMENTS_COMPLETED,
        RoundStageV1.POST_PLAN_FROZEN,
        RoundStageV1.TRAINING_DATA_READY,
        RoundStageV1.TRAINING_COMPLETED,
        RoundStageV1.INTERNAL_EVALUATION_COMPLETED,
        RoundStageV1.PROMOTED,
        RoundStageV1.ROUND_CLOSED,
    )
    for stage in chain:
        state = state.advance(
            stage,
            evidence_sha256="a" * 64,
        )
    assert state.current_stage is RoundStageV1.ROUND_CLOSED


def test_lifecycle_rejects_skipped_stage() -> None:
    state = RoundLifecycleV1.new(
        round_id="clean-r001",
        parent_policy_id="pi0-clean",
    )
    try:
        state.advance(
            RoundStageV1.PRE_PLAN_FROZEN,
            evidence_sha256="a" * 64,
        )
    except ValueError as exc:
        assert "transition" in str(exc).lower()
    else:
        raise AssertionError("skipped lifecycle stage was accepted")
