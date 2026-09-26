from pchsi.round_control.campaign_authority import (
    freeze_campaign_startup_authority,
)
from pchsi.round_control.scientific_round_governance import (
    advance_scientific_round_governance,
    new_scientific_round_governance,
)


def _authority(max_rounds=10, patience=3):
    return freeze_campaign_startup_authority(
        campaign_id="max10-test",
        requested_max_valid_rounds=max_rounds,
        no_promotion_patience=patience,
        max_infrastructure_attempt_restarts=2,
        force_run_all_rounds=False,
        campaign_purpose_sha256="a" * 64,
        heldout_firewall_sha256="b" * 64,
        paper_export_contract_sha256="c" * 64,
    )


def test_invalid_attempt_does_not_consume_scientific_round():
    s = new_scientific_round_governance(authority=_authority())
    s = advance_scientific_round_governance(
        s,
        outcome="PROTOCOL_INFRA_INVALID",
    )
    assert s.valid_rounds_consumed == 0
    assert s.invalid_attempt_count == 1
    assert not s.stop


def test_promotion_resets_patience():
    s = new_scientific_round_governance(authority=_authority())
    s = advance_scientific_round_governance(
        s,
        outcome="NO_TRAINING_UPDATE",
    )
    s = advance_scientific_round_governance(s, outcome="PROMOTED")
    assert s.valid_rounds_consumed == 2
    assert s.consecutive_no_promotion == 0


def test_authority_patience_stops_without_runtime_literal():
    s = new_scientific_round_governance(
        authority=_authority(max_rounds=9, patience=2)
    )
    for outcome in ("NO_TRAINING_UPDATE", "ROLLED_BACK"):
        s = advance_scientific_round_governance(s, outcome=outcome)
    assert s.stop
    assert s.stop_reason == "NO_PROMOTION_PATIENCE_EXHAUSTED"


def test_authority_max_rounds_stops_without_runtime_literal():
    s = new_scientific_round_governance(
        authority=_authority(max_rounds=2, patience=8)
    )
    for _ in range(2):
        s = advance_scientific_round_governance(
            s,
            outcome="PROMOTED",
        )
    assert s.stop
    assert s.stop_reason == "MAX_SCIENTIFIC_ROUNDS_REACHED"
