from __future__ import annotations

from dataclasses import dataclass

from .common import hashed_payload, require_sha256, require_text


@dataclass(frozen=True)
class PromotionDecisionV1:
    round_id: str
    decision: str
    decision_rule_id: str
    evidence_access_class: str
    evidence_sha256: str
    parent_policy_id: str
    candidate_policy_id: str
    next_parent_policy_id: str
    decision_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "PROMOTION_DECISION_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "decision": self.decision,
            "decision_rule_id": self.decision_rule_id,
            "evidence_access_class": self.evidence_access_class,
            "evidence_sha256": self.evidence_sha256,
            "parent_policy_id": self.parent_policy_id,
            "candidate_policy_id": self.candidate_policy_id,
            "next_parent_policy_id": self.next_parent_policy_id,
            "decision_sha256": self.decision_sha256,
        }


def freeze_promotion_decision(
    *,
    round_id: str,
    decision: str,
    decision_rule_id: str,
    evidence_access_class: str,
    evidence_sha256: str,
    parent_policy_id: str,
    candidate_policy_id: str,
) -> PromotionDecisionV1:
    for name, value in (
        ("round_id", round_id),
        ("decision_rule_id", decision_rule_id),
        ("parent_policy_id", parent_policy_id),
        ("candidate_policy_id", candidate_policy_id),
    ):
        require_text(name, value)
    require_sha256("evidence_sha256", evidence_sha256)
    if evidence_access_class != "TRAIN_SELECT":
        raise ValueError("promotion may only use TRAIN_SELECT evidence")
    if decision not in {"PROMOTE", "ROLLBACK", "HOLD"}:
        raise ValueError("unsupported promotion decision")
    next_parent = (
        candidate_policy_id if decision == "PROMOTE" else parent_policy_id
    )
    payload = {
        "schema_id": "PROMOTION_DECISION_V1",
        "schema_version": 1,
        "round_id": round_id,
        "decision": decision,
        "decision_rule_id": decision_rule_id,
        "evidence_access_class": evidence_access_class,
        "evidence_sha256": evidence_sha256,
        "parent_policy_id": parent_policy_id,
        "candidate_policy_id": candidate_policy_id,
        "next_parent_policy_id": next_parent,
        "benchmark_evidence_used": False,
    }
    hashed = hashed_payload(
        domain="PROMOTION_DECISION_V1",
        hash_field="decision_sha256",
        payload=payload,
    )
    return PromotionDecisionV1(
        round_id=round_id,
        decision=decision,
        decision_rule_id=decision_rule_id,
        evidence_access_class=evidence_access_class,
        evidence_sha256=evidence_sha256,
        parent_policy_id=parent_policy_id,
        candidate_policy_id=candidate_policy_id,
        next_parent_policy_id=next_parent,
        decision_sha256=hashed["decision_sha256"],
    )
