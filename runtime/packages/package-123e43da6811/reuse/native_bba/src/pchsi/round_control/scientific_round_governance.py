from __future__ import annotations

from dataclasses import dataclass

from .campaign_authority import CampaignStartupAuthorityV1
from .common import hashed_payload, require_nonnegative_int, require_sha256, require_text


OUTCOMES = {
    "PROMOTED",
    "ROLLED_BACK",
    "NO_TRAINING_UPDATE",
    "PROTOCOL_INFRA_INVALID",
}


@dataclass(frozen=True)
class ScientificRoundGovernanceV1:
    valid_rounds_consumed: int
    consecutive_no_promotion: int
    invalid_attempt_count: int
    max_valid_rounds: int
    no_promotion_patience: int
    max_infrastructure_attempt_restarts: int
    force_run_all_rounds: bool
    campaign_authority_sha256: str
    stop: bool
    stop_reason: str | None
    last_outcome: str | None
    governance_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "SCIENTIFIC_ROUND_GOVERNANCE_V1",
            "schema_version": 1,
            "valid_rounds_consumed": self.valid_rounds_consumed,
            "consecutive_no_promotion": self.consecutive_no_promotion,
            "invalid_attempt_count": self.invalid_attempt_count,
            "max_valid_rounds": self.max_valid_rounds,
            "no_promotion_patience": self.no_promotion_patience,
            "max_infrastructure_attempt_restarts": (
                self.max_infrastructure_attempt_restarts
            ),
            "force_run_all_rounds": self.force_run_all_rounds,
            "campaign_authority_sha256": self.campaign_authority_sha256,
            "stop": self.stop,
            "stop_reason": self.stop_reason,
            "last_outcome": self.last_outcome,
            "governance_sha256": self.governance_sha256,
        }


def _freeze(
    *,
    valid_rounds_consumed: int,
    consecutive_no_promotion: int,
    invalid_attempt_count: int,
    max_valid_rounds: int,
    no_promotion_patience: int,
    max_infrastructure_attempt_restarts: int,
    force_run_all_rounds: bool,
    campaign_authority_sha256: str,
    last_outcome: str | None,
) -> ScientificRoundGovernanceV1:
    for name, value in (
        ("valid_rounds_consumed", valid_rounds_consumed),
        ("consecutive_no_promotion", consecutive_no_promotion),
        ("invalid_attempt_count", invalid_attempt_count),
        ("max_valid_rounds", max_valid_rounds),
        ("no_promotion_patience", no_promotion_patience),
        (
            "max_infrastructure_attempt_restarts",
            max_infrastructure_attempt_restarts,
        ),
    ):
        require_nonnegative_int(name, value)
    require_sha256(
        "campaign_authority_sha256",
        campaign_authority_sha256,
    )
    if max_valid_rounds < 1 or no_promotion_patience < 1:
        raise ValueError("campaign round limits must be positive")
    if type(force_run_all_rounds) is not bool:
        raise TypeError("force_run_all_rounds must be bool")

    stop = False
    reason = None
    if valid_rounds_consumed >= max_valid_rounds:
        stop = True
        reason = "MAX_SCIENTIFIC_ROUNDS_REACHED"
    elif (
        not force_run_all_rounds
        and consecutive_no_promotion >= no_promotion_patience
    ):
        stop = True
        reason = "NO_PROMOTION_PATIENCE_EXHAUSTED"

    payload = {
        "schema_id": "SCIENTIFIC_ROUND_GOVERNANCE_V1",
        "schema_version": 1,
        "valid_rounds_consumed": valid_rounds_consumed,
        "consecutive_no_promotion": consecutive_no_promotion,
        "invalid_attempt_count": invalid_attempt_count,
        "max_valid_rounds": max_valid_rounds,
        "no_promotion_patience": no_promotion_patience,
        "max_infrastructure_attempt_restarts": (
            max_infrastructure_attempt_restarts
        ),
        "force_run_all_rounds": force_run_all_rounds,
        "campaign_authority_sha256": campaign_authority_sha256,
        "stop": stop,
        "stop_reason": reason,
        "last_outcome": last_outcome,
    }
    hashed = hashed_payload(
        domain="SCIENTIFIC_ROUND_GOVERNANCE_V1",
        hash_field="governance_sha256",
        payload=payload,
    )
    return ScientificRoundGovernanceV1(
        **{
            name: hashed[name]
            for name in ScientificRoundGovernanceV1.__dataclass_fields__
        }
    )


def new_scientific_round_governance(
    *,
    authority: CampaignStartupAuthorityV1,
) -> ScientificRoundGovernanceV1:
    if not isinstance(authority, CampaignStartupAuthorityV1):
        raise TypeError("authority must be CampaignStartupAuthorityV1")
    return _freeze(
        valid_rounds_consumed=0,
        consecutive_no_promotion=0,
        invalid_attempt_count=0,
        max_valid_rounds=authority.requested_max_valid_rounds,
        no_promotion_patience=authority.no_promotion_patience,
        max_infrastructure_attempt_restarts=(
            authority.max_infrastructure_attempt_restarts
        ),
        force_run_all_rounds=authority.force_run_all_rounds,
        campaign_authority_sha256=authority.authority_sha256,
        last_outcome=None,
    )


def advance_scientific_round_governance(
    state: ScientificRoundGovernanceV1,
    *,
    outcome: str,
) -> ScientificRoundGovernanceV1:
    if not isinstance(state, ScientificRoundGovernanceV1):
        raise TypeError("state must be ScientificRoundGovernanceV1")
    require_text("outcome", outcome)
    if outcome not in OUTCOMES:
        raise ValueError("unsupported round outcome")
    if state.stop:
        raise ValueError("outer loop already stopped")

    valid = state.valid_rounds_consumed
    no_promotion = state.consecutive_no_promotion
    invalid = state.invalid_attempt_count
    if outcome == "PROTOCOL_INFRA_INVALID":
        invalid += 1
    else:
        valid += 1
        no_promotion = 0 if outcome == "PROMOTED" else no_promotion + 1

    return _freeze(
        valid_rounds_consumed=valid,
        consecutive_no_promotion=no_promotion,
        invalid_attempt_count=invalid,
        max_valid_rounds=state.max_valid_rounds,
        no_promotion_patience=state.no_promotion_patience,
        max_infrastructure_attempt_restarts=(
            state.max_infrastructure_attempt_restarts
        ),
        force_run_all_rounds=state.force_run_all_rounds,
        campaign_authority_sha256=state.campaign_authority_sha256,
        last_outcome=outcome,
    )
