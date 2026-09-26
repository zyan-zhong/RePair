import pytest

from pchsi.round_control.campaign_authority import (
    freeze_campaign_startup_authority,
)
from pchsi.round_control.formal_campaign_startup import (
    freeze_formal_max10_campaign_startup_receipt,
)
from pchsi.round_control.rollout_collection import (
    RoundRolloutCollectionRequestV1,
    RoundRolloutExecutionBindingV1,
)


def _campaign():
    return freeze_campaign_startup_authority(
        campaign_id="formal-max10",
        requested_max_valid_rounds=10,
        no_promotion_patience=3,
        max_infrastructure_attempt_restarts=2,
        force_run_all_rounds=False,
        campaign_purpose_sha256="a" * 64,
        heldout_firewall_sha256="b" * 64,
        paper_export_contract_sha256="c" * 64,
    )


def _request():
    return RoundRolloutCollectionRequestV1(
        round_id="formal-r1",
        execution_attempt_id="formal-r1-attempt-0",
        parent_policy_id="PI0_CLEAN",
        parent_policy_artifact_sha256="1" * 64,
        policy_runtime_binding_sha256="2" * 64,
        execution_profile_sha256="3" * 64,
        train_update_manifest_sha256="4" * 64,
        round_memory_runtime_authority_sha256="5" * 64,
        round_start_memory_snapshot_sha256="6" * 64,
        token_budget_contract_sha256="7" * 64,
        execution_namespace="formal-max10-r1",
        rollout_seed=17,
    )


def _binding(request, authorized=True):
    return RoundRolloutExecutionBindingV1(
        request_sha256=request.request_sha256,
        rollout_control_source_sha256="8" * 64,
        clean_execution_binding_source_sha256="9" * 64,
        episode_evaluator_source_sha256="a" * 64,
        attempt_receipts_source_sha256="b" * 64,
        policy_runtime_adapter_sha256="c" * 64,
        scientific_execution_authorized=authorized,
    )


def test_receipt_freezes_only_before_scientific_execution():
    request = _request()
    receipt = freeze_formal_max10_campaign_startup_receipt(
        campaign_authority=_campaign(),
        integration_commit_oid="d" * 40,
        rollout_request=request,
        rollout_execution_binding=_binding(request),
        first_round_execution_binding_sha256="e" * 64,
        controlled_campaign_startup_authorized=True,
    )
    assert receipt.single_operator_launch_only is True
    assert receipt.routine_human_scientific_decision_count == 0
    assert receipt.canary_round_adopted_as_formal_round is False
    assert receipt.scientific_execution_started is False


def test_receipt_rejects_unauthorized_rollout_binding():
    request = _request()
    with pytest.raises(ValueError):
        freeze_formal_max10_campaign_startup_receipt(
            campaign_authority=_campaign(),
            integration_commit_oid="d" * 40,
            rollout_request=request,
            rollout_execution_binding=_binding(request, authorized=False),
            first_round_execution_binding_sha256="e" * 64,
            controlled_campaign_startup_authorized=True,
        )


def test_receipt_rejects_canary_adoption():
    request = _request()
    with pytest.raises(ValueError):
        freeze_formal_max10_campaign_startup_receipt(
            campaign_authority=_campaign(),
            integration_commit_oid="d" * 40,
            rollout_request=request,
            rollout_execution_binding=_binding(request),
            first_round_execution_binding_sha256="e" * 64,
            controlled_campaign_startup_authorized=True,
            canary_round_adopted_as_formal_round=True,
        )


def test_receipt_rejects_routine_human_decision():
    request = _request()
    with pytest.raises(ValueError):
        freeze_formal_max10_campaign_startup_receipt(
            campaign_authority=_campaign(),
            integration_commit_oid="d" * 40,
            rollout_request=request,
            rollout_execution_binding=_binding(request),
            first_round_execution_binding_sha256="e" * 64,
            controlled_campaign_startup_authorized=True,
            routine_human_scientific_decision_count=1,
        )
