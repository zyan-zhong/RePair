"""Explicit single-resolution attempt control for E1 scheduled cells."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical_evidence import sha256_text
from .run_schedule import execution_attempt_id
from .schema_models import (
    AttemptReceiptV1,
    RunScheduleV1,
)


_NOT_PRODUCED = "SCIENTIFIC_OUTCOME_NOT_PRODUCED"
_SUCCESS = "SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS"
_TASK_FAILURE = (
    "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"
)
_SCIENTIFIC_RESULTS = {
    _SUCCESS,
    _TASK_FAILURE,
}
_PRE_RESULT_INFRASTRUCTURE = (
    "PRE_RESULT_INFRASTRUCTURE_ERROR"
)
_PROTOCOL_ERROR = "PROTOCOL_CONFIGURATION_ERROR"


@dataclass(frozen=True, slots=True)
class AttemptAuthorization:
    scheduled_cell_id: str
    execution_attempt_id: str
    attempt_ordinal: int


class RunResolutionState:
    """Mutable run-local authorization state with explicit attempt boundaries."""

    def __init__(
        self,
        *,
        schedule: RunScheduleV1,
        run_id: str,
    ) -> None:
        if not isinstance(schedule, RunScheduleV1):
            raise TypeError(
                "schedule must be RunScheduleV1"
            )
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id must be non-empty")

        self._schedule = schedule
        self._run_id = run_id
        self._schedule_sha256 = sha256_text(
            schedule.to_json()
        )
        self._known_cells = {
            cell.scheduled_cell_id
            for cell in schedule.cells
        }
        if len(self._known_cells) != schedule.cell_count:
            raise ValueError(
                "schedule contains duplicate cell IDs"
            )

        self._next_ordinal: dict[str, int] = {
            cell_id: 0
            for cell_id in self._known_cells
        }
        self._active: dict[
            str,
            AttemptAuthorization,
        ] = {}
        self._terminal_receipts: list[
            AttemptReceiptV1
        ] = []
        self._terminal_attempt_ids: set[str] = set()
        self._locked_cells: set[str] = set()
        self._run_invalid = False

    @property
    def schedule(self) -> RunScheduleV1:
        return self._schedule

    @property
    def schedule_sha256(self) -> str:
        return self._schedule_sha256

    @property
    def run_invalid(self) -> bool:
        return self._run_invalid

    @property
    def terminal_receipts(
        self,
    ) -> tuple[AttemptReceiptV1, ...]:
        return tuple(self._terminal_receipts)

    def _require_cell(
        self,
        scheduled_cell_id: str,
    ) -> str:
        if (
            not isinstance(scheduled_cell_id, str)
            or not scheduled_cell_id
        ):
            raise ValueError(
                "scheduled_cell_id must be non-empty"
            )
        if scheduled_cell_id not in self._known_cells:
            raise ValueError(
                "scheduled_cell_id is not in the frozen schedule"
            )
        return scheduled_cell_id

    def begin_attempt(
        self,
        *,
        scheduled_cell_id: str,
    ) -> AttemptAuthorization:
        cell_id = self._require_cell(
            scheduled_cell_id
        )

        if self._run_invalid:
            raise RuntimeError(
                "run is invalid; no further attempts are authorized"
            )
        if cell_id in self._locked_cells:
            raise RuntimeError(
                "scheduled cell is scientifically locked"
            )
        if cell_id in self._active:
            raise RuntimeError(
                "scheduled cell already has an active attempt"
            )

        receipts = [
            receipt
            for receipt in self._terminal_receipts
            if receipt.scheduled_cell_id == cell_id
        ]
        if receipts and not self.can_retry(
            scheduled_cell_id=cell_id
        ):
            raise RuntimeError(
                "scheduled cell is not retryable"
            )

        ordinal = self._next_ordinal[cell_id]
        authorization = AttemptAuthorization(
            scheduled_cell_id=cell_id,
            execution_attempt_id=execution_attempt_id(
                scheduled_cell_id=cell_id,
                attempt_ordinal=ordinal,
            ),
            attempt_ordinal=ordinal,
        )
        self._active[cell_id] = authorization
        self._next_ordinal[cell_id] = ordinal + 1
        return authorization

    def _validate_receipt_identity(
        self,
        receipt: AttemptReceiptV1,
        authorization: AttemptAuthorization,
    ) -> None:
        if receipt.receipt_kind != "TERMINAL":
            raise ValueError(
                "record_terminal_attempt requires a TERMINAL receipt"
            )
        if receipt.run_id != self._run_id:
            raise ValueError(
                "terminal receipt run_id mismatch"
            )
        if (
            receipt.run_schedule_sha256
            != self._schedule_sha256
        ):
            raise ValueError(
                "terminal receipt run_schedule_sha256 mismatch"
            )
        if (
            receipt.scheduled_cell_id
            != authorization.scheduled_cell_id
            or receipt.execution_attempt_id
            != authorization.execution_attempt_id
            or receipt.attempt_ordinal
            != authorization.attempt_ordinal
        ):
            raise ValueError(
                "terminal receipt does not match the active attempt"
            )

    def record_terminal_attempt(
        self,
        *,
        receipt: AttemptReceiptV1,
    ) -> "RunResolutionState":
        if not isinstance(receipt, AttemptReceiptV1):
            raise TypeError(
                "receipt must be AttemptReceiptV1"
            )
        cell_id = self._require_cell(
            receipt.scheduled_cell_id
        )

        if (
            receipt.execution_attempt_id
            in self._terminal_attempt_ids
        ):
            raise RuntimeError(
                "execution attempt is already terminal"
            )

        authorization = self._active.get(cell_id)
        if authorization is None:
            raise RuntimeError(
                "terminal receipt has no active attempt"
            )
        self._validate_receipt_identity(
            receipt,
            authorization,
        )

        scientific = (
            receipt.scientific_outcome_status
        )
        if scientific in _SCIENTIFIC_RESULTS:
            if (
                receipt.episode_semantic_sha256 is None
                or receipt.attempt_bundle_sha256 is None
            ):
                raise ValueError(
                    "scientific result requires semantic and bundle hashes"
                )
            self._locked_cells.add(cell_id)
        elif scientific == _NOT_PRODUCED:
            if (
                receipt.episode_semantic_sha256 is not None
                or receipt.attempt_bundle_sha256 is not None
            ):
                raise ValueError(
                    "non-produced outcome cannot have scientific hashes"
                )
        else:
            raise ValueError(
                "scientific_outcome_status is not recognized"
            )

        del self._active[cell_id]
        self._terminal_attempt_ids.add(
            receipt.execution_attempt_id
        )
        self._terminal_receipts.append(receipt)

        if receipt.terminal_class == _PROTOCOL_ERROR:
            self._run_invalid = True

        return self

    def can_retry(
        self,
        *,
        scheduled_cell_id: str,
    ) -> bool:
        cell_id = self._require_cell(
            scheduled_cell_id
        )
        if (
            self._run_invalid
            or cell_id in self._locked_cells
            or cell_id in self._active
        ):
            return False

        receipts = [
            receipt
            for receipt in self._terminal_receipts
            if receipt.scheduled_cell_id == cell_id
        ]
        if not receipts:
            return False

        return all(
            receipt.scientific_outcome_status
            == _NOT_PRODUCED
            and receipt.terminal_class
            == _PRE_RESULT_INFRASTRUCTURE
            for receipt in receipts
        )
