from pchsi.round_control.next_round import freeze_next_round_creation
from pchsi.round_control.promotion import freeze_promotion_decision


def test_promote_creates_next_round_from_candidate() -> None:
    decision = freeze_promotion_decision(
        round_id="r1",
        decision="PROMOTE",
        decision_rule_id="rule-v1",
        evidence_access_class="TRAIN_SELECT",
        evidence_sha256="a" * 64,
        parent_policy_id="pi1",
        candidate_policy_id="pi2",
    )
    next_round = freeze_next_round_creation(
        closed_round_id="r1",
        next_round_id="r2",
        promotion_decision=decision,
    )
    assert next_round.next_parent_policy_id == "pi2"
    assert next_round.automatic_creation_authorized is True


def test_rollback_keeps_parent_and_hold_blocks_auto_creation() -> None:
    rollback = freeze_promotion_decision(
        round_id="r1",
        decision="ROLLBACK",
        decision_rule_id="rule-v1",
        evidence_access_class="TRAIN_SELECT",
        evidence_sha256="b" * 64,
        parent_policy_id="pi1",
        candidate_policy_id="pi2",
    )
    next_round = freeze_next_round_creation(
        closed_round_id="r1",
        next_round_id="r2",
        promotion_decision=rollback,
    )
    assert next_round.next_parent_policy_id == "pi1"
    assert next_round.automatic_creation_authorized is True

    hold = freeze_promotion_decision(
        round_id="r1",
        decision="HOLD",
        decision_rule_id="rule-v1",
        evidence_access_class="TRAIN_SELECT",
        evidence_sha256="c" * 64,
        parent_policy_id="pi1",
        candidate_policy_id="pi2",
    )
    blocked = freeze_next_round_creation(
        closed_round_id="r1",
        next_round_id="r2",
        promotion_decision=hold,
    )
    assert blocked.next_parent_policy_id == "pi1"
    assert blocked.automatic_creation_authorized is False
