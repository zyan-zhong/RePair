from __future__ import annotations

from dataclasses import dataclass

from .common import hashed_payload, require_sha256, require_text
from .promotion import PromotionDecisionV1


@dataclass(frozen=True)
class NextRoundCreationV1:
    closed_round_id: str
    next_round_id: str
    previous_parent_policy_id: str
    next_parent_policy_id: str
    promotion_decision_sha256: str
    automatic_creation_authorized: bool
    creation_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "NEXT_ROUND_CREATION_V1",
            "schema_version": 1,
            "closed_round_id": self.closed_round_id,
            "next_round_id": self.next_round_id,
            "previous_parent_policy_id": self.previous_parent_policy_id,
            "next_parent_policy_id": self.next_parent_policy_id,
            "promotion_decision_sha256": self.promotion_decision_sha256,
            "automatic_creation_authorized": self.automatic_creation_authorized,
            "creation_sha256": self.creation_sha256,
        }


def freeze_next_round_creation(
    *,
    closed_round_id: str,
    next_round_id: str,
    promotion_decision: PromotionDecisionV1,
) -> NextRoundCreationV1:
    require_text("closed_round_id", closed_round_id)
    require_text("next_round_id", next_round_id)
    if promotion_decision.round_id != closed_round_id:
        raise ValueError("promotion decision is not bound to the closed round")
    require_sha256(
        "promotion_decision_sha256",
        promotion_decision.decision_sha256,
    )
    if promotion_decision.decision == "HOLD":
        automatic_creation_authorized = False
    else:
        automatic_creation_authorized = True

    payload = {
        "schema_id": "NEXT_ROUND_CREATION_V1",
        "schema_version": 1,
        "closed_round_id": closed_round_id,
        "next_round_id": next_round_id,
        "previous_parent_policy_id": promotion_decision.parent_policy_id,
        "next_parent_policy_id": promotion_decision.next_parent_policy_id,
        "promotion_decision_sha256": promotion_decision.decision_sha256,
        "automatic_creation_authorized": automatic_creation_authorized,
    }
    hashed = hashed_payload(
        domain="NEXT_ROUND_CREATION_V1",
        hash_field="creation_sha256",
        payload=payload,
    )
    return NextRoundCreationV1(
        closed_round_id=closed_round_id,
        next_round_id=next_round_id,
        previous_parent_policy_id=promotion_decision.parent_policy_id,
        next_parent_policy_id=promotion_decision.next_parent_policy_id,
        promotion_decision_sha256=promotion_decision.decision_sha256,
        automatic_creation_authorized=automatic_creation_authorized,
        creation_sha256=hashed["creation_sha256"],
    )
