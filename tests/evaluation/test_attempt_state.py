from __future__ import annotations
import pytest
from pchsi.evaluation.attempt_state import (
    AttemptState,
    OperationalFinalizationStatus,
    ScientificOutcomeStatus,
)

def test_scientific_and_operational_states_are_independent() -> None:
    state = AttemptState()
    assert state.scientific_outcome_status is ScientificOutcomeStatus.NOT_PRODUCED
    assert state.operational_finalization_status is OperationalFinalizationStatus.STAGING
    assert state.scientific_complete is False
    assert state.model_retry_allowed is True

    scientific = state.with_scientific(ScientificOutcomeStatus.SUCCESS)
    assert scientific.scientific_outcome_status is ScientificOutcomeStatus.SUCCESS
    assert scientific.operational_finalization_status is OperationalFinalizationStatus.STAGING
    assert scientific.scientific_complete is True
    assert scientific.model_retry_allowed is False

    pending = scientific.with_operational(OperationalFinalizationStatus.PUBLICATION_PENDING)
    assert pending.scientific_outcome_status is ScientificOutcomeStatus.SUCCESS
    assert pending.operational_finalization_status is OperationalFinalizationStatus.PUBLICATION_PENDING
    assert pending.model_retry_allowed is False

    with pytest.raises(ValueError, match="immutable"):
        scientific.with_scientific(ScientificOutcomeStatus.TASK_FAILURE)
