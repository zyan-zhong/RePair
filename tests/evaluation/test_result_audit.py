from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_text,
)
from pchsi.evaluation.result_audit import audit_e1_run
from pchsi.evaluation.run_schedule import build_e1_run_schedule
from pchsi.evaluation.schema_models import (
    AttemptReceiptV1,
    BudgetSnapshotV1,
    EpisodeArtifactV1,
    ScientificCellLockV1,
)
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
            gamefile=(
                f"/dataset/task-{index:04d}/"
                "game.tw-pddl"
            ),
            gamefile_sha1="b" * 40,
            root=f"/dataset/task-{index:04d}",
            traj_file=(
                f"/dataset/task-{index:04d}/"
                "traj_data.json"
            ),
        )
        for index in range(134)
    )


@lru_cache(maxsize=1)
def _schedule():
    return build_e1_run_schedule(
        records=_records(),
        task_manifest_sha256=DIGEST,
    )


def _bundle_identity(files: tuple[tuple[str, bytes], ...]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            [
                {
                    "filename": name,
                    "sha256": sha256_bytes(data),
                }
                for name, data in files
            ]
        )
    )


def _episode(cell, attempt_id: str) -> EpisodeArtifactV1:
    return EpisodeArtifactV1(
        schema_id="E1_EPISODE_ARTIFACT_V1",
        schema_version=1,
        run_id="run-e1",
        scheduled_cell_id=cell.scheduled_cell_id,
        execution_attempt_id=attempt_id,
        attempt_ordinal=int(attempt_id.rsplit("a", 1)[1]),
        task_index=cell.task_index,
        task_id=cell.task_id,
        task_type="pick_and_place_simple",
        gamefile_sha1="b" * 40,
        gamefile_sha256="c" * 64,
        seed=cell.seed,
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        raw_protocol_sha256=DIGEST,
        split_access_sha256=DIGEST,
        gamefile_identity_manifest_sha256=DIGEST,
        environment_runtime_manifest_sha256=DIGEST,
        policy_runtime_manifest_sha256=DIGEST,
        policy_request_schema_sha256=DIGEST,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"
        ),
        operational_finalization_status="PUBLISHED",
        success=False,
        termination_reason=(
            "POLICY_ATTEMPT_BUDGET_EXHAUSTED"
        ),
        final_score=None,
        final_done=False,
        final_won=False,
        final_budget=BudgetSnapshotV1(
            policy_attempt_count=0,
            environment_step_count=0,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
        trace_count=0,
        public_transition_count=0,
        environment_call_trace_count=0,
        initial_observation_sha256="d" * 64,
        final_observation_sha256="d" * 64,
        episode_semantic_sha256="e" * 64,
        started_at_utc="2026-08-07T00:00:00Z",
        completed_at_utc="2026-08-07T00:00:01Z",
    )


def _write_receipt(
    root: Path,
    *,
    cell,
    attempt_id: str,
    kind: str,
    scientific: str,
    operational: str,
    semantic: str | None,
    bundle_hash: str | None,
    terminal_class: str | None,
    error_code: str | None = None,
) -> None:
    receipt = AttemptReceiptV1(
        schema_id="E1_ATTEMPT_RECEIPT_V1",
        schema_version=1,
        receipt_kind=kind,
        run_id="run-e1",
        scheduled_cell_id=cell.scheduled_cell_id,
        execution_attempt_id=attempt_id,
        attempt_ordinal=int(attempt_id.rsplit("a", 1)[1]),
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        run_schedule_sha256=sha256_text(_schedule().to_json()),
        scientific_outcome_status=scientific,
        operational_finalization_status=operational,
        episode_semantic_sha256=semantic,
        attempt_bundle_sha256=bundle_hash,
        terminal_class=terminal_class,
        error_code=error_code,
        created_at_utc="2026-08-07T00:00:02Z",
    )
    suffix = "started" if kind == "STARTED" else "terminal"
    (root / "attempt_ledger" / f"{attempt_id}.{suffix}.json").write_text(
        receipt.to_json(),
        encoding="utf-8",
    )


def _write_scientific_cell(root: Path, cell, *, ordinal: int = 0) -> None:
    attempt_id = f"{cell.scheduled_cell_id}-a{ordinal:03d}"
    attempt_dir = root / "attempts" / attempt_id
    attempt_dir.mkdir(parents=True)

    episode = _episode(cell, attempt_id)
    attempt_json = episode.to_json().encode("utf-8")
    traces = b""
    transitions = b""
    checksums = (
        f"{sha256_bytes(attempt_json)}  attempt.json\n"
        f"{sha256_bytes(traces)}  action_traces.jsonl\n"
        f"{sha256_bytes(transitions)}  public_transitions.jsonl\n"
    ).encode("utf-8")
    files = (
        ("attempt.json", attempt_json),
        ("action_traces.jsonl", traces),
        ("public_transitions.jsonl", transitions),
        ("SHA256SUMS", checksums),
    )
    bundle_hash = _bundle_identity(files)

    for name, payload in files:
        (attempt_dir / name).write_bytes(payload)

    lock = ScientificCellLockV1(
        schema_id="E1_SCIENTIFIC_CELL_LOCK_V1",
        schema_version=1,
        run_id="run-e1",
        scheduled_cell_id=cell.scheduled_cell_id,
        execution_attempt_id=attempt_id,
        run_schedule_sha256=sha256_text(_schedule().to_json()),
        episode_semantic_sha256=(
            episode.episode_semantic_sha256
        ),
        attempt_bundle_sha256=bundle_hash,
        scientific_outcome_status=(
            episode.scientific_outcome_status
        ),
        evaluator_commit="evaluator",
    )
    (root / "cell_locks" / f"{cell.scheduled_cell_id}.json").write_text(
        lock.to_json(),
        encoding="utf-8",
    )

    _write_receipt(
        root,
        cell=cell,
        attempt_id=attempt_id,
        kind="STARTED",
        scientific="SCIENTIFIC_OUTCOME_NOT_PRODUCED",
        operational="STAGING",
        semantic=None,
        bundle_hash=None,
        terminal_class=None,
    )
    _write_receipt(
        root,
        cell=cell,
        attempt_id=attempt_id,
        kind="TERMINAL",
        scientific=episode.scientific_outcome_status,
        operational="PUBLISHED",
        semantic=episode.episode_semantic_sha256,
        bundle_hash=bundle_hash,
        terminal_class="SCIENTIFIC_RESULT",
    )


def _build_complete(root: Path) -> None:
    for directory in (
        root / "attempt_ledger",
        root / "attempts",
        root / "attempts" / ".staging",
        root / "cell_locks",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for cell in _schedule().cells:
        _write_scientific_cell(root, cell)


@pytest.fixture(scope="session")
def complete_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("complete-run")
    _build_complete(root)
    return root


@pytest.fixture
def run_copy(tmp_path: Path, complete_run: Path) -> Path:
    destination = tmp_path / "run"
    shutil.copytree(
        complete_run,
        destination,
    )
    return destination


def test_complete_670_cell_run_is_approved(run_copy: Path) -> None:
    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.approved is True
    assert report.scheduled_cells == 670
    assert report.scientifically_resolved_cells == 670
    assert report.scientific_cell_locks == 670
    assert report.published_scientific_attempt_bundles == 670


@pytest.mark.parametrize(
    "condition",
    ["missing_lock", "missing_bundle", "orphan_lock", "orphan_bundle"],
)
def test_each_single_missing_or_orphan_condition_rejects(
    run_copy: Path,
    condition: str,
) -> None:
    cell = _schedule().cells[0]
    lock = run_copy / "cell_locks" / f"{cell.scheduled_cell_id}.json"
    attempt = run_copy / "attempts" / f"{cell.scheduled_cell_id}-a000"

    if condition == "missing_lock":
        lock.unlink()
    elif condition == "missing_bundle":
        shutil.rmtree(attempt)
    elif condition == "orphan_lock":
        payload = json.loads(lock.read_text(encoding="utf-8"))
        payload["scheduled_cell_id"] = "e1-t9999-s0000000017"
        (run_copy / "cell_locks" / "e1-t9999-s0000000017.json").write_bytes(
            canonical_json_bytes(payload)
        )
    elif condition == "orphan_bundle":
        shutil.copytree(
            attempt,
            run_copy / "attempts" / "orphan-a000",
        )
    else:
        raise AssertionError(condition)

    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.approved is False
    assert (
        report.cell_locks_without_matching_published_bundle
        + report.published_bundles_without_matching_cell_lock
        + report.missing_task_seed_cells
    ) > 0


def test_lock_and_bundle_semantic_and_exact_hashes_must_match(
    run_copy: Path,
) -> None:
    cell = _schedule().cells[0]
    lock_path = (
        run_copy / "cell_locks" / f"{cell.scheduled_cell_id}.json"
    )
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["attempt_bundle_sha256"] = "f" * 64
    lock_path.write_bytes(canonical_json_bytes(lock))

    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.approved is False
    assert report.checksum_failures >= 1


def test_missing_started_or_terminal_receipt_rejects(run_copy: Path) -> None:
    cell = _schedule().cells[0]
    attempt_id = f"{cell.scheduled_cell_id}-a000"
    started = run_copy / "attempt_ledger" / f"{attempt_id}.started.json"
    terminal = run_copy / "attempt_ledger" / f"{attempt_id}.terminal.json"

    started.unlink()
    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.approved is False
    assert report.missing_terminal_receipts >= 1

    complete_run = run_copy.parent / "terminal-missing"
    shutil.copytree(run_copy, complete_run)
    # restore a syntactically valid started receipt by copying from another cell
    other = _schedule().cells[1]
    other_started = (
        complete_run / "attempt_ledger" /
        f"{other.scheduled_cell_id}-a000.started.json"
    )
    payload = json.loads(other_started.read_text(encoding="utf-8"))
    payload["scheduled_cell_id"] = cell.scheduled_cell_id
    payload["execution_attempt_id"] = attempt_id
    (complete_run / "attempt_ledger" / f"{attempt_id}.started.json").write_bytes(
        canonical_json_bytes(payload)
    )
    (complete_run / "attempt_ledger" / f"{attempt_id}.terminal.json").unlink()
    report = audit_e1_run(
        run_root=complete_run,
        expected_schedule=_schedule(),
    )
    assert report.approved is False
    assert report.missing_terminal_receipts >= 1


def test_publication_pending_and_unresolved_artifact_failure_reject(
    run_copy: Path,
) -> None:
    cell = _schedule().cells[0]
    attempt_id = f"{cell.scheduled_cell_id}-a000"
    terminal_path = (
        run_copy / "attempt_ledger" / f"{attempt_id}.terminal.json"
    )
    payload = json.loads(terminal_path.read_text(encoding="utf-8"))
    payload["operational_finalization_status"] = "PUBLICATION_PENDING"
    terminal_path.write_bytes(canonical_json_bytes(payload))

    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.publication_pending == 1
    assert report.approved is False

    payload["operational_finalization_status"] = "ARTIFACT_IO_FAILED"
    terminal_path.write_bytes(canonical_json_bytes(payload))
    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.artifact_io_failed_unresolved == 1
    assert report.approved is False


def test_duplicate_resolution_and_best_of_run_reject(run_copy: Path) -> None:
    cell = _schedule().cells[0]
    source = run_copy / "attempts" / f"{cell.scheduled_cell_id}-a000"
    duplicate = run_copy / "attempts" / f"{cell.scheduled_cell_id}-a001"
    shutil.copytree(source, duplicate)
    attempt_path = duplicate / "attempt.json"
    payload = json.loads(attempt_path.read_text(encoding="utf-8"))
    payload["execution_attempt_id"] = f"{cell.scheduled_cell_id}-a001"
    payload["attempt_ordinal"] = 1
    attempt_path.write_bytes(canonical_json_bytes(payload))
    traces = (duplicate / "action_traces.jsonl").read_bytes()
    transitions = (duplicate / "public_transitions.jsonl").read_bytes()
    attempt_json = attempt_path.read_bytes()
    (duplicate / "SHA256SUMS").write_text(
        f"{sha256_bytes(attempt_json)}  attempt.json\n"
        f"{sha256_bytes(traces)}  action_traces.jsonl\n"
        f"{sha256_bytes(transitions)}  public_transitions.jsonl\n",
        encoding="utf-8",
    )

    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.duplicate_cell_resolutions >= 1
    assert report.best_of_run_selection >= 1
    assert report.approved is False


def test_unresolved_protocol_or_infrastructure_cell_rejects(
    run_copy: Path,
) -> None:
    cell = _schedule().cells[0]
    attempt_id = f"{cell.scheduled_cell_id}-a000"
    shutil.rmtree(run_copy / "attempts" / attempt_id)
    (run_copy / "cell_locks" / f"{cell.scheduled_cell_id}.json").unlink()
    terminal_path = (
        run_copy / "attempt_ledger" / f"{attempt_id}.terminal.json"
    )
    payload = json.loads(terminal_path.read_text(encoding="utf-8"))
    payload.update(
        {
            "scientific_outcome_status": "SCIENTIFIC_OUTCOME_NOT_PRODUCED",
            "operational_finalization_status": "ARTIFACT_IO_FAILED",
            "episode_semantic_sha256": None,
            "attempt_bundle_sha256": None,
            "terminal_class": "PROTOCOL_CONFIGURATION_ERROR",
        }
    )
    terminal_path.write_bytes(canonical_json_bytes(payload))

    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.unresolved_protocol_errors == 1
    assert report.approved is False

    payload["terminal_class"] = "PRE_RESULT_INFRASTRUCTURE_ERROR"
    terminal_path.write_bytes(canonical_json_bytes(payload))
    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.unresolved_pre_result_infrastructure_cells == 1
    assert report.approved is False


def test_close_failed_recorded_is_allowed_only_with_published_bundle_and_reaped_worker(
    run_copy: Path,
) -> None:
    cell = _schedule().cells[0]
    attempt_id = f"{cell.scheduled_cell_id}-a000"
    terminal_path = (
        run_copy / "attempt_ledger" / f"{attempt_id}.terminal.json"
    )
    payload = json.loads(terminal_path.read_text(encoding="utf-8"))
    payload["operational_finalization_status"] = "CLOSE_FAILED_RECORDED"
    payload["terminal_class"] = "POST_RESULT_OPERATIONAL_ERROR"
    payload["error_code"] = "WORKER_REAPED_NO_CONTAMINATION"
    terminal_path.write_bytes(canonical_json_bytes(payload))

    assert audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    ).approved is True

    payload["error_code"] = "WORKER_NOT_REAPED"
    terminal_path.write_bytes(canonical_json_bytes(payload))
    assert audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    ).approved is False


def test_total_attempts_may_exceed_670_without_changing_scientific_cells(
    run_copy: Path,
) -> None:
    cell = _schedule().cells[0]
    attempt_id = f"{cell.scheduled_cell_id}-a999"
    _write_receipt(
        run_copy,
        cell=cell,
        attempt_id=attempt_id,
        kind="STARTED",
        scientific="SCIENTIFIC_OUTCOME_NOT_PRODUCED",
        operational="STAGING",
        semantic=None,
        bundle_hash=None,
        terminal_class=None,
    )
    _write_receipt(
        run_copy,
        cell=cell,
        attempt_id=attempt_id,
        kind="TERMINAL",
        scientific="SCIENTIFIC_OUTCOME_NOT_PRODUCED",
        operational="ARTIFACT_IO_FAILED",
        semantic=None,
        bundle_hash=None,
        terminal_class="PRE_RESULT_INFRASTRUCTURE_ERROR",
    )

    report = audit_e1_run(
        run_root=run_copy,
        expected_schedule=_schedule(),
    )
    assert report.scientifically_resolved_cells == 670
    assert report.approved is True


def test_pooled_670_iid_headline_is_forbidden(run_copy: Path) -> None:
    schedule = object.__new__(type(_schedule()))
    for name in _schedule().__dataclass_fields__:
        object.__setattr__(schedule, name, getattr(_schedule(), name))
    object.__setattr__(
        schedule,
        "pooled_670_iid_headline_result",
        "allowed",
    )
    with pytest.raises(ValueError, match="pooled"):
        audit_e1_run(
            run_root=run_copy,
            expected_schedule=schedule,
        )
