from __future__ import annotations

import pytest

from pchsi.evaluation.run_resolution import (
    RunResolutionState,
)
from pchsi.evaluation.run_schedule import (
    build_e1_run_schedule,
)
from pchsi.evaluation.schema_models import AttemptReceiptV1
from pchsi.evaluation.task_manifest import FrozenTaskRecord


DIGEST = "a" * 64


def _records() -> tuple[FrozenTaskRecord, ...]:
    return tuple(
        FrozenTaskRecord(
            index=index,
            task_id=(
                "alfworld_valid_unseen_all134_"
                f"{index:04d}"
            ),
            split="valid_unseen",
            task_type="pick_and_place_simple",
            gamefile=f"/dataset/task-{index:04d}/game.tw-pddl",
            gamefile_sha1="b" * 40,
            root=f"/dataset/task-{index:04d}",
            traj_file=f"/dataset/task-{index:04d}/traj_data.json",
        )
        for index in range(134)
    )


def _state() -> RunResolutionState:
    return RunResolutionState(
        schedule=build_e1_run_schedule(
            records=_records(),
            task_manifest_sha256=DIGEST,
        ),
        run_id="run-e1",
    )


def _terminal(
    state: RunResolutionState,
    authorization,
    *,
    scientific: str,
    terminal_class: str,
    operational: str = "PUBLISHED",
) -> AttemptReceiptV1:
    return AttemptReceiptV1(
        schema_id="E1_ATTEMPT_RECEIPT_V1",
        schema_version=1,
        receipt_kind="TERMINAL",
        run_id="run-e1",
        scheduled_cell_id=authorization.scheduled_cell_id,
        execution_attempt_id=authorization.execution_attempt_id,
        attempt_ordinal=authorization.attempt_ordinal,
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        run_schedule_sha256=state.schedule_sha256,
        scientific_outcome_status=scientific,
        operational_finalization_status=operational,
        episode_semantic_sha256=(
            None
            if scientific == "SCIENTIFIC_OUTCOME_NOT_PRODUCED"
            else "c" * 64
        ),
        attempt_bundle_sha256=(
            None
            if scientific == "SCIENTIFIC_OUTCOME_NOT_PRODUCED"
            else "d" * 64
        ),
        terminal_class=terminal_class,
        error_code=None,
        created_at_utc="2026-08-07T00:00:00Z",
    )


def test_attempt_ordinals_are_monotonic_and_no_clobber() -> None:
    state = _state()
    cell_id = state.schedule.cells[0].scheduled_cell_id

    first = state.begin_attempt(scheduled_cell_id=cell_id)
    assert first.attempt_ordinal == 0
    assert first.execution_attempt_id.endswith("-a000")

    with pytest.raises(RuntimeError, match="active"):
        state.begin_attempt(scheduled_cell_id=cell_id)

    state.record_terminal_attempt(
        receipt=_terminal(
            state,
            first,
            scientific="SCIENTIFIC_OUTCOME_NOT_PRODUCED",
            terminal_class="PRE_RESULT_INFRASTRUCTURE_ERROR",
            operational="ARTIFACT_IO_FAILED",
        )
    )

    second = state.begin_attempt(scheduled_cell_id=cell_id)
    assert second.attempt_ordinal == 1
    assert second.execution_attempt_id.endswith("-a001")


def test_first_scientific_result_locks_cell() -> None:
    state = _state()
    cell_id = state.schedule.cells[0].scheduled_cell_id
    first = state.begin_attempt(scheduled_cell_id=cell_id)

    state.record_terminal_attempt(
        receipt=_terminal(
            state,
            first,
            scientific="SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS",
            terminal_class="SCIENTIFIC_RESULT",
        )
    )

    assert state.can_retry(scheduled_cell_id=cell_id) is False

    with pytest.raises(RuntimeError, match="locked"):
        state.begin_attempt(scheduled_cell_id=cell_id)


def test_pre_result_infrastructure_failure_allows_explicit_retry() -> None:
    state = _state()
    cell_id = state.schedule.cells[0].scheduled_cell_id
    first = state.begin_attempt(scheduled_cell_id=cell_id)

    state.record_terminal_attempt(
        receipt=_terminal(
            state,
            first,
            scientific="SCIENTIFIC_OUTCOME_NOT_PRODUCED",
            terminal_class="PRE_RESULT_INFRASTRUCTURE_ERROR",
            operational="ARTIFACT_IO_FAILED",
        )
    )

    assert state.can_retry(scheduled_cell_id=cell_id) is True
    assert state.begin_attempt(
        scheduled_cell_id=cell_id
    ).attempt_ordinal == 1


def test_protocol_error_invalidates_entire_run() -> None:
    state = _state()
    first_cell = state.schedule.cells[0].scheduled_cell_id
    second_cell = state.schedule.cells[1].scheduled_cell_id

    first = state.begin_attempt(
        scheduled_cell_id=first_cell
    )
    state.record_terminal_attempt(
        receipt=_terminal(
            state,
            first,
            scientific="SCIENTIFIC_OUTCOME_NOT_PRODUCED",
            terminal_class="PROTOCOL_CONFIGURATION_ERROR",
            operational="ARTIFACT_IO_FAILED",
        )
    )

    assert state.run_invalid is True

    with pytest.raises(RuntimeError, match="invalid"):
        state.begin_attempt(
            scheduled_cell_id=second_cell
        )


def test_post_result_operational_failure_does_not_authorize_model_retry() -> None:
    state = _state()
    cell_id = state.schedule.cells[0].scheduled_cell_id
    first = state.begin_attempt(scheduled_cell_id=cell_id)

    state.record_terminal_attempt(
        receipt=_terminal(
            state,
            first,
            scientific="SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE",
            terminal_class="POST_RESULT_OPERATIONAL_ERROR",
            operational="PUBLICATION_PENDING",
        )
    )

    assert state.can_retry(scheduled_cell_id=cell_id) is False
    with pytest.raises(RuntimeError, match="locked"):
        state.begin_attempt(scheduled_cell_id=cell_id)


def test_best_of_run_selection_is_impossible() -> None:
    state = _state()
    cell_id = state.schedule.cells[0].scheduled_cell_id
    first = state.begin_attempt(scheduled_cell_id=cell_id)

    state.record_terminal_attempt(
        receipt=_terminal(
            state,
            first,
            scientific="SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE",
            terminal_class="SCIENTIFIC_RESULT",
        )
    )

    duplicate = _terminal(
        state,
        first,
        scientific="SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS",
        terminal_class="SCIENTIFIC_RESULT",
    )

    with pytest.raises(RuntimeError, match="already"):
        state.record_terminal_attempt(receipt=duplicate)

    assert len(state.terminal_receipts) == 1
