from __future__ import annotations

from dataclasses import dataclass
import re

from .campaign_authority import CampaignStartupAuthorityV1
from .common import hashed_payload, require_bool, require_sha256, require_text
from .rollout_collection import (
    RoundRolloutCollectionRequestV1,
    RoundRolloutExecutionBindingV1,
)


_GIT_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


@dataclass(frozen=True)
class FormalMax10CampaignStartupReceiptV1:
    campaign_authority_sha256: str
    integration_commit_oid: str
    rollout_request_sha256: str
    rollout_execution_binding_sha256: str
    first_round_execution_binding_sha256: str
    controlled_campaign_startup_authorized: bool
    single_operator_launch_only: bool
    routine_human_scientific_decision_count: int
    canary_round_adopted_as_formal_round: bool
    scientific_execution_started: bool
    startup_receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "FORMAL_MAX10_CAMPAIGN_STARTUP_RECEIPT_V1",
            "schema_version": 1,
            "campaign_authority_sha256": self.campaign_authority_sha256,
            "integration_commit_oid": self.integration_commit_oid,
            "rollout_request_sha256": self.rollout_request_sha256,
            "rollout_execution_binding_sha256": (
                self.rollout_execution_binding_sha256
            ),
            "first_round_execution_binding_sha256": (
                self.first_round_execution_binding_sha256
            ),
            "controlled_campaign_startup_authorized": (
                self.controlled_campaign_startup_authorized
            ),
            "single_operator_launch_only": self.single_operator_launch_only,
            "routine_human_scientific_decision_count": (
                self.routine_human_scientific_decision_count
            ),
            "canary_round_adopted_as_formal_round": (
                self.canary_round_adopted_as_formal_round
            ),
            "scientific_execution_started": self.scientific_execution_started,
            "startup_receipt_sha256": self.startup_receipt_sha256,
        }


def freeze_formal_max10_campaign_startup_receipt(
    *,
    campaign_authority: CampaignStartupAuthorityV1,
    integration_commit_oid: str,
    rollout_request: RoundRolloutCollectionRequestV1,
    rollout_execution_binding: RoundRolloutExecutionBindingV1,
    first_round_execution_binding_sha256: str,
    controlled_campaign_startup_authorized: bool,
    single_operator_launch_only: bool = True,
    routine_human_scientific_decision_count: int = 0,
    canary_round_adopted_as_formal_round: bool = False,
    scientific_execution_started: bool = False,
) -> FormalMax10CampaignStartupReceiptV1:
    if not isinstance(campaign_authority, CampaignStartupAuthorityV1):
        raise TypeError("campaign_authority type mismatch")
    if not isinstance(
        rollout_request,
        RoundRolloutCollectionRequestV1,
    ):
        raise TypeError("rollout_request type mismatch")
    if not isinstance(
        rollout_execution_binding,
        RoundRolloutExecutionBindingV1,
    ):
        raise TypeError("rollout_execution_binding type mismatch")

    require_text("integration_commit_oid", integration_commit_oid)
    if _GIT_OID.fullmatch(integration_commit_oid) is None:
        raise ValueError("integration_commit_oid must be Git object id")

    require_sha256(
        "first_round_execution_binding_sha256",
        first_round_execution_binding_sha256,
    )
    require_bool(
        "controlled_campaign_startup_authorized",
        controlled_campaign_startup_authorized,
    )
    require_bool(
        "single_operator_launch_only",
        single_operator_launch_only,
    )
    require_bool(
        "canary_round_adopted_as_formal_round",
        canary_round_adopted_as_formal_round,
    )
    require_bool(
        "scientific_execution_started",
        scientific_execution_started,
    )

    if type(routine_human_scientific_decision_count) is not int:
        raise TypeError(
            "routine_human_scientific_decision_count must be int"
        )
    if routine_human_scientific_decision_count != 0:
        raise ValueError(
            "formal max10 forbids routine human scientific decisions"
        )
    if canary_round_adopted_as_formal_round:
        raise ValueError(
            "pre-release canary cannot enter formal max10 denominator"
        )
    if scientific_execution_started:
        raise ValueError(
            "startup receipt must freeze before scientific execution"
        )
    if single_operator_launch_only is not True:
        raise ValueError("formal max10 requires one operator launch")
    if controlled_campaign_startup_authorized is not True:
        raise ValueError("formal max10 startup authority is not authorized")

    if rollout_request.benchmark_feedback_authorized is not False:
        raise ValueError("benchmark feedback must remain forbidden")
    if (
        rollout_request.invalid_attempt_adaptive_evidence_reuse_authorized
        is not False
    ):
        raise ValueError(
            "invalid-attempt adaptive evidence reuse must remain forbidden"
        )
    if rollout_execution_binding.request_sha256 != rollout_request.request_sha256:
        raise ValueError("rollout request/binding identity mismatch")
    if rollout_execution_binding.scientific_execution_authorized is not True:
        raise ValueError(
            "first formal round requires authorized rollout execution binding"
        )

    payload = {
        "schema_id": "FORMAL_MAX10_CAMPAIGN_STARTUP_RECEIPT_V1",
        "schema_version": 1,
        "campaign_authority_sha256": (
            campaign_authority.authority_sha256
        ),
        "integration_commit_oid": integration_commit_oid,
        "rollout_request_sha256": rollout_request.request_sha256,
        "rollout_execution_binding_sha256": (
            rollout_execution_binding.binding_sha256
        ),
        "first_round_execution_binding_sha256": (
            first_round_execution_binding_sha256
        ),
        "controlled_campaign_startup_authorized": True,
        "single_operator_launch_only": True,
        "routine_human_scientific_decision_count": 0,
        "canary_round_adopted_as_formal_round": False,
        "scientific_execution_started": False,
    }
    hashed = hashed_payload(
        domain="FORMAL_MAX10_CAMPAIGN_STARTUP_RECEIPT_V1",
        hash_field="startup_receipt_sha256",
        payload=payload,
    )
    return FormalMax10CampaignStartupReceiptV1(
        **{
            name: hashed[name]
            for name in FormalMax10CampaignStartupReceiptV1.__dataclass_fields__
        }
    )
