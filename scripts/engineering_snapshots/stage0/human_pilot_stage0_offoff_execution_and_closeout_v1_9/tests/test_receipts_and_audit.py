from pathlib import Path

from stage0.receipts import (
    append_receipt,
    load_receipts,
    make_cell_receipt,
)
from stage0.result_audit import aggregate_paired_results


def test_receipt_chain_is_append_only_and_reload_safe(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    first = make_cell_receipt(
        condition_id="PARENT",
        condition_cell_id="parent-t0-s17",
        manifest_index=0,
        task_id="task-0",
        seed=17,
        execution_attempt_id="attempt-parent-0",
        attempt_bundle_sha256="a" * 64,
        success=False,
        termination_reason="budget",
        previous_receipt_sha256=None,
    )
    append_receipt(ledger, first)
    second = make_cell_receipt(
        condition_id="CANDIDATE",
        condition_cell_id="candidate-t0-s17",
        manifest_index=0,
        task_id="task-0",
        seed=17,
        execution_attempt_id="attempt-candidate-0",
        attempt_bundle_sha256="b" * 64,
        success=True,
        termination_reason="success",
        previous_receipt_sha256=first["receipt_sha256"],
    )
    append_receipt(ledger, second)

    loaded = load_receipts(ledger)
    assert loaded == (first, second)


def test_paired_aggregation_uses_unique_task_as_primary_unit() -> None:
    parent = []
    candidate = []
    for task_index, task_id in enumerate(("task-a", "task-b")):
        for seed in (17, 31):
            parent.append({
                "manifest_index": task_index,
                "task_id": task_id,
                "seed": seed,
                "success": task_id == "task-b",
            })
            candidate.append({
                "manifest_index": task_index,
                "task_id": task_id,
                "seed": seed,
                "success": True,
            })

    result = aggregate_paired_results(
        parent_receipts=tuple(parent),
        candidate_receipts=tuple(candidate),
        expected_task_count=2,
        expected_seeds=(17, 31),
    )

    assert result["unique_task_count"] == 2
    assert result["paired_cell_count"] == 4
    assert result["parent_success_cells"] == 2
    assert result["candidate_success_cells"] == 4
    assert result["candidate_only_success_cells"] == 2
    assert result["mean_task_success_rate_delta"] == 0.5
    assert result["primary_statistical_unit"] == "unique_task"
