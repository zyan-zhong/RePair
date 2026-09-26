"""Independent scientific and operational state for one E1 attempt."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class ScientificOutcomeStatus(str, Enum):
    NOT_PRODUCED = "SCIENTIFIC_OUTCOME_NOT_PRODUCED"
    SUCCESS = "SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS"
    TASK_FAILURE = "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"


class OperationalFinalizationStatus(str, Enum):
    STAGING = "STAGING"
    PUBLISHED = "PUBLISHED"
    PUBLICATION_PENDING = "PUBLICATION_PENDING"
    CLOSE_FAILED_RECORDED = "CLOSE_FAILED_RECORDED"
    ARTIFACT_IO_FAILED = "ARTIFACT_IO_FAILED"


class CloseFailureEvidenceCode(str, Enum):
    # Frozen terminal-receipt evidence for post-result close failures.
    WORKER_REAPED_NO_CONTAMINATION = (
        "WORKER_REAPED_NO_CONTAMINATION"
    )
    WORKER_NOT_REAPED = "WORKER_NOT_REAPED"


@dataclass(frozen=True, slots=True)
class AttemptState:
    scientific_outcome_status: ScientificOutcomeStatus = (
        ScientificOutcomeStatus.NOT_PRODUCED
    )
    operational_finalization_status: OperationalFinalizationStatus = (
        OperationalFinalizationStatus.STAGING
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.scientific_outcome_status,
            ScientificOutcomeStatus,
        ):
            raise TypeError(
                "scientific_outcome_status must be ScientificOutcomeStatus"
            )
        if not isinstance(
            self.operational_finalization_status,
            OperationalFinalizationStatus,
        ):
            raise TypeError(
                "operational_finalization_status must be "
                "OperationalFinalizationStatus"
            )

    @property
    def scientific_complete(self) -> bool:
        return self.scientific_outcome_status in {
            ScientificOutcomeStatus.SUCCESS,
            ScientificOutcomeStatus.TASK_FAILURE,
        }

    @property
    def model_retry_allowed(self) -> bool:
        return (
            self.scientific_outcome_status
            is ScientificOutcomeStatus.NOT_PRODUCED
        )

    def with_scientific(
        self,
        status: ScientificOutcomeStatus,
    ) -> "AttemptState":
        if not isinstance(status, ScientificOutcomeStatus):
            raise TypeError(
                "status must be ScientificOutcomeStatus"
            )
        current = self.scientific_outcome_status
        if (
            current is not ScientificOutcomeStatus.NOT_PRODUCED
            and status is not current
        ):
            raise ValueError(
                "scientific outcome is immutable once produced"
            )
        return replace(
            self,
            scientific_outcome_status=status,
        )

    def with_operational(
        self,
        status: OperationalFinalizationStatus,
    ) -> "AttemptState":
        if not isinstance(
            status,
            OperationalFinalizationStatus,
        ):
            raise TypeError(
                "status must be OperationalFinalizationStatus"
            )
        return replace(
            self,
            operational_finalization_status=status,
        )
