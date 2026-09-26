import pytest

from pchsi.round_control.campaign_authority import (
    freeze_campaign_startup_authority,
)
from pchsi.round_control.scientific_round_governance import (
    advance_scientific_round_governance,
    new_scientific_round_governance,
)


def _authority(max_rounds=10, patience=3, infra=2, force=False):
    return freeze_campaign_startup_authority(
        campaign_id="campaign-test",
        requested_max_valid_rounds=max_rounds,
        no_promotion_patience=patience,
        max_infrastructure_attempt_restarts=infra,
        force_run_all_rounds=force,
        campaign_purpose_sha256="a" * 64,
        heldout_firewall_sha256="b" * 64,
        paper_export_contract_sha256="c" * 64,
    )


def test_campaign_limits_are_external_authority_not_runtime_constants():
    authority = _authority(max_rounds=4, patience=2, infra=1)
    state = new_scientific_round_governance(authority=authority)
    assert state.max_valid_rounds == 4
    assert state.no_promotion_patience == 2
    assert state.max_infrastructure_attempt_restarts == 1
    state = advance_scientific_round_governance(
        state,
        outcome="NO_TRAINING_UPDATE",
    )
    assert not state.stop
    state = advance_scientific_round_governance(
        state,
        outcome="ROLLED_BACK",
    )
    assert state.stop
    assert state.stop_reason == "NO_PROMOTION_PATIENCE_EXHAUSTED"


def test_infrastructure_invalid_does_not_consume_scientific_round():
    state = new_scientific_round_governance(authority=_authority())
    state = advance_scientific_round_governance(
        state,
        outcome="PROTOCOL_INFRA_INVALID",
    )
    assert state.valid_rounds_consumed == 0
    assert state.invalid_attempt_count == 1


def test_force_run_all_rounds_disables_patience_only():
    state = new_scientific_round_governance(
        authority=_authority(max_rounds=2, patience=1, force=True)
    )
    state = advance_scientific_round_governance(
        state,
        outcome="NO_TRAINING_UPDATE",
    )
    assert not state.stop
    state = advance_scientific_round_governance(
        state,
        outcome="PROMOTED",
    )
    assert state.stop
    assert state.stop_reason == "MAX_SCIENTIFIC_ROUNDS_REACHED"
