from __future__ import annotations

import pytest

from pchsi.round_control.retention import (
    ArtifactKindV1,
    decide_cross_round_retention,
)


@pytest.mark.parametrize(
    "access_class",
    [
        "TRAIN_UPDATE",
        "TRAIN_REFERENCE_ROUND",
        "TRAIN_RESEARCH_INTELLIGENCE",
    ],
)
def test_registered_train_side_strong_trace_enters_localization(access_class):
    decision = decide_cross_round_retention(
        origin_round_role="CLEAN_STRONG_OR_REFERENCE_ROUND_V1",
        artifact_kind=ArtifactKindV1.STRONG_STRUCTURED_TRACE,
        access_class=access_class,
    )
    assert decision.allowed is True
    assert decision.destination == "LOCALIZATION_SUPERVISION"


def test_strong_train_audit_is_audit_history_only():
    decision = decide_cross_round_retention(
        origin_round_role="STRONG_TAKEOVER_AUDIT_V1",
        artifact_kind=ArtifactKindV1.STRONG_STRUCTURED_TRACE,
        access_class="TRAIN_AUDIT",
    )
    assert decision.allowed is True
    assert decision.destination == "LOCAL_SHADOW_AUDIT_HISTORY"
    assert decision.destination != "LOCALIZATION_SUPERVISION"


@pytest.mark.parametrize(
    "access_class",
    [
        "TRAIN_SELECT",
        "TRAIN_AUTONOMOUS_ROUND",
        "VALID_SEEN",
        "VALID_UNSEEN",
        "DEV_VISIBLE",
    ],
)
def test_unregistered_or_nonlocalization_sources_do_not_enter_localization(
    access_class,
):
    with pytest.raises(ValueError):
        decide_cross_round_retention(
            origin_round_role="STRONG_PRIMARY_ROUND_V1",
            artifact_kind=ArtifactKindV1.STRONG_STRUCTURED_TRACE,
            access_class=access_class,
        )
