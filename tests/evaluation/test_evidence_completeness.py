import pytest

from pchsi.evaluation.evidence_completeness import (
    EvidenceRequirementStatus,
    INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE,
    audit_current_evidence_contract,
    require_no_critical_missing,
)


def test_code_inventory_is_not_an_episode_certificate():
    report = audit_current_evidence_contract()
    assert report.status_for(
        "policy_call.raw_response_body"
    ) is EvidenceRequirementStatus.PRESENT_BUT_UNVALIDATED
    with pytest.raises(
        ValueError,
        match=INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE,
    ):
        require_no_critical_missing(report)


def test_removed_upgraded_flag_cannot_self_certify():
    with pytest.raises(TypeError):
        audit_current_evidence_contract(upgraded=True)
