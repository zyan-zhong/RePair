from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .common import (
    hashed_payload,
    require_nonnegative_int,
    require_sha256,
    require_text,
)


@dataclass(frozen=True)
class CampaignStartupAuthorityV1:
    campaign_id: str
    requested_max_valid_rounds: int
    no_promotion_patience: int
    max_infrastructure_attempt_restarts: int
    force_run_all_rounds: bool
    campaign_purpose_sha256: str
    heldout_firewall_sha256: str
    paper_export_contract_sha256: str
    authority_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "CAMPAIGN_STARTUP_AUTHORITY_V1",
            "schema_version": 1,
            "campaign_id": self.campaign_id,
            "requested_max_valid_rounds": self.requested_max_valid_rounds,
            "no_promotion_patience": self.no_promotion_patience,
            "max_infrastructure_attempt_restarts": (
                self.max_infrastructure_attempt_restarts
            ),
            "force_run_all_rounds": self.force_run_all_rounds,
            "campaign_purpose_sha256": self.campaign_purpose_sha256,
            "heldout_firewall_sha256": self.heldout_firewall_sha256,
            "paper_export_contract_sha256": self.paper_export_contract_sha256,
            "authority_sha256": self.authority_sha256,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "CampaignStartupAuthorityV1":
        if not isinstance(value, Mapping):
            raise TypeError("campaign startup authority must be mapping")
        expected = {
            "schema_id",
            "schema_version",
            "campaign_id",
            "requested_max_valid_rounds",
            "no_promotion_patience",
            "max_infrastructure_attempt_restarts",
            "force_run_all_rounds",
            "campaign_purpose_sha256",
            "heldout_firewall_sha256",
            "paper_export_contract_sha256",
            "authority_sha256",
        }
        if set(value) != expected:
            raise ValueError("campaign startup authority fields mismatch")
        if (
            value["schema_id"] != "CAMPAIGN_STARTUP_AUTHORITY_V1"
            or value["schema_version"] != 1
        ):
            raise ValueError("campaign startup authority schema mismatch")
        return freeze_campaign_startup_authority(
            campaign_id=value["campaign_id"],
            requested_max_valid_rounds=value["requested_max_valid_rounds"],
            no_promotion_patience=value["no_promotion_patience"],
            max_infrastructure_attempt_restarts=(
                value["max_infrastructure_attempt_restarts"]
            ),
            force_run_all_rounds=value["force_run_all_rounds"],
            campaign_purpose_sha256=value["campaign_purpose_sha256"],
            heldout_firewall_sha256=value["heldout_firewall_sha256"],
            paper_export_contract_sha256=value[
                "paper_export_contract_sha256"
            ],
            expected_authority_sha256=value["authority_sha256"],
        )


def freeze_campaign_startup_authority(
    *,
    campaign_id: str,
    requested_max_valid_rounds: int,
    no_promotion_patience: int,
    max_infrastructure_attempt_restarts: int,
    force_run_all_rounds: bool,
    campaign_purpose_sha256: str,
    heldout_firewall_sha256: str,
    paper_export_contract_sha256: str,
    expected_authority_sha256: str | None = None,
) -> CampaignStartupAuthorityV1:
    require_text("campaign_id", campaign_id)
    require_nonnegative_int(
        "requested_max_valid_rounds",
        requested_max_valid_rounds,
    )
    require_nonnegative_int(
        "no_promotion_patience",
        no_promotion_patience,
    )
    require_nonnegative_int(
        "max_infrastructure_attempt_restarts",
        max_infrastructure_attempt_restarts,
    )
    if requested_max_valid_rounds < 1:
        raise ValueError("requested_max_valid_rounds must be positive")
    if no_promotion_patience < 1:
        raise ValueError("no_promotion_patience must be positive")
    if type(force_run_all_rounds) is not bool:
        raise TypeError("force_run_all_rounds must be bool")
    for name, value in (
        ("campaign_purpose_sha256", campaign_purpose_sha256),
        ("heldout_firewall_sha256", heldout_firewall_sha256),
        ("paper_export_contract_sha256", paper_export_contract_sha256),
    ):
        require_sha256(name, value)
    payload = {
        "schema_id": "CAMPAIGN_STARTUP_AUTHORITY_V1",
        "schema_version": 1,
        "campaign_id": campaign_id,
        "requested_max_valid_rounds": requested_max_valid_rounds,
        "no_promotion_patience": no_promotion_patience,
        "max_infrastructure_attempt_restarts": (
            max_infrastructure_attempt_restarts
        ),
        "force_run_all_rounds": force_run_all_rounds,
        "campaign_purpose_sha256": campaign_purpose_sha256,
        "heldout_firewall_sha256": heldout_firewall_sha256,
        "paper_export_contract_sha256": paper_export_contract_sha256,
    }
    hashed = hashed_payload(
        domain="CAMPAIGN_STARTUP_AUTHORITY_V1",
        hash_field="authority_sha256",
        payload=payload,
    )
    observed = hashed["authority_sha256"]
    if (
        expected_authority_sha256 is not None
        and observed != expected_authority_sha256
    ):
        raise ValueError("campaign startup authority SHA mismatch")
    return CampaignStartupAuthorityV1(
        campaign_id=campaign_id,
        requested_max_valid_rounds=requested_max_valid_rounds,
        no_promotion_patience=no_promotion_patience,
        max_infrastructure_attempt_restarts=(
            max_infrastructure_attempt_restarts
        ),
        force_run_all_rounds=force_run_all_rounds,
        campaign_purpose_sha256=campaign_purpose_sha256,
        heldout_firewall_sha256=heldout_firewall_sha256,
        paper_export_contract_sha256=paper_export_contract_sha256,
        authority_sha256=observed,
    )
