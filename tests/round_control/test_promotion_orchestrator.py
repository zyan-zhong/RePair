from pchsi.round_control.lifecycle import RoundStageV1, RoundLifecycleV1
from pchsi.round_control.orchestrator import next_action_for
from pchsi.round_control.promotion import freeze_promotion_decision


def test_promotion_can_only_use_train_select_evidence() -> None:
    decision = freeze_promotion_decision(
        round_id="clean-r001",
        decision="PROMOTE",
        decision_rule_id="PRE_REGISTERED_INTERNAL_SELECT_RULE_V1",
        evidence_access_class="TRAIN_SELECT",
        evidence_sha256="e" * 64,
        parent_policy_id="pi0",
        candidate_policy_id="pi1",
    )
    assert decision.next_parent_policy_id == "pi1"

    try:
        freeze_promotion_decision(
            round_id="clean-r001",
            decision="PROMOTE",
            decision_rule_id="bad",
            evidence_access_class="VALID_UNSEEN",
            evidence_sha256="e" * 64,
            parent_policy_id="pi0",
            candidate_policy_id="pi1",
        )
    except ValueError as exc:
        assert "train_select" in str(exc).lower()
    else:
        raise AssertionError("benchmark evidence entered promotion")


def test_orchestrator_routes_to_existing_components() -> None:
    state = RoundLifecycleV1.new(
        round_id="clean-r001",
        parent_policy_id="pi0",
    )
    action = next_action_for(state)
    assert action.component_ids == ("EVIDENCE_PACKAGE",)

    state = state.advance(
        RoundStageV1.EVIDENCE_READY,
        evidence_sha256="a" * 64,
    )
    action = next_action_for(state)
    assert action.component_ids == (
        "HIERARCHICAL_ANALYZER",
        "PERSISTENT_FAILURE_EXPERIENCE",
    )
