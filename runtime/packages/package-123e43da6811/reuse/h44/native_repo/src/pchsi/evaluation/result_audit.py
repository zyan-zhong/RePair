"""Exact artifact-level result audit for one complete E1 run."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .attempt_state import CloseFailureEvidenceCode
from .canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_text,
)
from .schema_models import (
    AttemptReceiptV1,
    EpisodeArtifactV1,
    RunScheduleV1,
    ScientificCellLockV1,
)


_BUNDLE_NAMES = (
    "attempt.json",
    "action_traces.jsonl",
    "public_transitions.jsonl",
    "SHA256SUMS",
)
_PAYLOAD_NAMES = _BUNDLE_NAMES[:3]
_COMPLETE_SCIENTIFIC = {
    "SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS",
    "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE",
}


@dataclass(frozen=True, slots=True)
class ResultAuditReport:
    scheduled_cells: int
    scientifically_resolved_cells: int
    scientific_cell_locks: int
    published_scientific_attempt_bundles: int
    cell_locks_without_matching_published_bundle: int
    published_bundles_without_matching_cell_lock: int
    publication_pending: int
    artifact_io_failed_unresolved: int
    missing_terminal_receipts: int
    checksum_failures: int
    duplicate_cell_resolutions: int
    missing_task_seed_cells: int
    unresolved_protocol_errors: int
    unresolved_pre_result_infrastructure_cells: int
    best_of_run_selection: int
    approved: bool


@dataclass(frozen=True, slots=True)
class _BundleRecord:
    directory_name: str
    episode: EpisodeArtifactV1
    bundle_sha256: str


@dataclass(frozen=True, slots=True)
class _LockRecord:
    filename: str
    lock: ScientificCellLockV1


def _require_directory(path: Path, name: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{name} must be a real directory")
    return path


def _parse_checksum_file(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("SHA256SUMS must be UTF-8") from error
    if not text.endswith("\n"):
        raise ValueError("SHA256SUMS must end with LF")
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "  " not in line:
            raise ValueError("malformed SHA256SUMS line")
        digest, name = line.split("  ", 1)
        if name in result:
            raise ValueError("duplicate SHA256SUMS filename")
        if name not in _PAYLOAD_NAMES:
            raise ValueError("unexpected SHA256SUMS filename")
        if len(digest) != 64 or any(
            character not in "0123456789abcdef"
            for character in digest
        ):
            raise ValueError("invalid SHA256SUMS digest")
        result[name] = digest
    if tuple(result) != _PAYLOAD_NAMES:
        raise ValueError("SHA256SUMS file order is not frozen")
    return result


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


def _load_bundle(path: Path) -> _BundleRecord:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("attempt bundle must be a real directory")
    entries = tuple(sorted(
        item.name
        for item in path.iterdir()
        if item.is_file() and not item.is_symlink()
    ))
    if entries != tuple(sorted(_BUNDLE_NAMES)):
        raise ValueError("attempt bundle file inventory mismatch")
    if any(item.is_symlink() for item in path.iterdir()):
        raise ValueError("attempt bundle cannot contain symlinks")

    file_bytes = tuple(
        (name, (path / name).read_bytes())
        for name in _BUNDLE_NAMES
    )
    payload_map = dict(file_bytes)
    checksums = _parse_checksum_file(
        payload_map["SHA256SUMS"]
    )
    for name in _PAYLOAD_NAMES:
        if sha256_bytes(payload_map[name]) != checksums[name]:
            raise ValueError("attempt bundle checksum mismatch")

    episode = EpisodeArtifactV1.from_json(
        payload_map["attempt.json"]
    )
    if episode.execution_attempt_id != path.name:
        raise ValueError("attempt directory and artifact ID mismatch")
    if (
        episode.scientific_outcome_status
        not in _COMPLETE_SCIENTIFIC
    ):
        raise ValueError("published bundle is not scientific")

    return _BundleRecord(
        directory_name=path.name,
        episode=episode,
        bundle_sha256=_bundle_identity(file_bytes),
    )


def _load_receipts(
    ledger: Path,
) -> tuple[
    dict[str, AttemptReceiptV1],
    dict[str, AttemptReceiptV1],
    int,
]:
    started: dict[str, AttemptReceiptV1] = {}
    terminal: dict[str, AttemptReceiptV1] = {}
    parse_failures = 0
    for path in sorted(ledger.glob("*.json")):
        if path.is_symlink() or not path.is_file():
            parse_failures += 1
            continue
        try:
            receipt = AttemptReceiptV1.from_json(
                path.read_bytes()
            )
        except (TypeError, ValueError, OSError):
            parse_failures += 1
            continue
        expected_suffix = (
            ".started.json"
            if receipt.receipt_kind == "STARTED"
            else ".terminal.json"
        )
        if path.name != (
            receipt.execution_attempt_id
            + expected_suffix
        ):
            parse_failures += 1
            continue
        destination = (
            started
            if receipt.receipt_kind == "STARTED"
            else terminal
        )
        if receipt.execution_attempt_id in destination:
            parse_failures += 1
            continue
        destination[receipt.execution_attempt_id] = receipt
    return started, terminal, parse_failures


def _lock_matches_bundle(
    lock: ScientificCellLockV1,
    bundle: _BundleRecord,
    *,
    expected_schedule_sha256: str,
) -> bool:
    episode = bundle.episode
    return (
        lock.run_id == episode.run_id
        and lock.scheduled_cell_id
        == episode.scheduled_cell_id
        and lock.execution_attempt_id
        == episode.execution_attempt_id
        and lock.run_schedule_sha256
        == expected_schedule_sha256
        and lock.episode_semantic_sha256
        == episode.episode_semantic_sha256
        and lock.episode_semantic_sha256
        == bundle.episode.episode_semantic_sha256
        and lock.attempt_bundle_sha256
        == bundle.bundle_sha256
        and lock.scientific_outcome_status
        == episode.scientific_outcome_status
        and lock.evaluator_commit
        == episode.evaluator_commit
    )


def _terminal_matches(
    terminal: AttemptReceiptV1,
    *,
    lock: ScientificCellLockV1,
    bundle: _BundleRecord,
    expected_schedule_sha256: str,
) -> bool:
    if terminal.receipt_kind != "TERMINAL":
        return False
    if (
        terminal.run_id != lock.run_id
        or terminal.scheduled_cell_id
        != lock.scheduled_cell_id
        or terminal.execution_attempt_id
        != lock.execution_attempt_id
        or terminal.run_schedule_sha256
        != expected_schedule_sha256
        or terminal.scientific_outcome_status
        != lock.scientific_outcome_status
        or terminal.episode_semantic_sha256
        != lock.episode_semantic_sha256
        or terminal.attempt_bundle_sha256
        != bundle.bundle_sha256
    ):
        return False
    operational = terminal.operational_finalization_status
    if operational == "PUBLISHED":
        return True
    if operational == "CLOSE_FAILED_RECORDED":
        return (
            terminal.terminal_class
            == "POST_RESULT_OPERATIONAL_ERROR"
            and terminal.error_code
            == (
                CloseFailureEvidenceCode
                .WORKER_REAPED_NO_CONTAMINATION.value
            )
        )
    return False


def audit_e1_run(
    *,
    run_root: Path,
    expected_schedule: RunScheduleV1,
) -> ResultAuditReport:
    if not isinstance(expected_schedule, RunScheduleV1):
        raise TypeError(
            "expected_schedule must be RunScheduleV1"
        )
    if expected_schedule.cell_count != 670:
        raise ValueError("E1 schedule must contain 670 cells")
    if len(expected_schedule.cells) != 670:
        raise ValueError("E1 schedule cell array must contain 670 cells")
    if expected_schedule.primary_statistical_unit != "unique_task":
        raise ValueError("primary statistical unit must be unique_task")
    if expected_schedule.replicates_are_not_independent_tasks is not True:
        raise ValueError("replicates must not be independent tasks")
    if expected_schedule.pooled_670_iid_headline_result != "forbidden":
        raise ValueError("pooled 670 iid headline result is forbidden")

    root = _require_directory(Path(run_root), "run_root")
    ledger = _require_directory(
        root / "attempt_ledger",
        "attempt_ledger",
    )
    attempts_root = _require_directory(
        root / "attempts",
        "attempts",
    )
    locks_root = _require_directory(
        root / "cell_locks",
        "cell_locks",
    )

    expected_cell_ids = {
        cell.scheduled_cell_id
        for cell in expected_schedule.cells
    }
    if len(expected_cell_ids) != 670:
        raise ValueError("schedule contains duplicate cell IDs")
    schedule_sha256 = sha256_text(
        expected_schedule.to_json()
    )

    started, terminals, receipt_failures = _load_receipts(
        ledger
    )
    missing_receipts = (
        len(set(started) - set(terminals))
        + len(set(terminals) - set(started))
        + receipt_failures
    )

    checksum_failures = 0
    bundle_directories = [
        path
        for path in sorted(attempts_root.iterdir())
        if path.name != ".staging"
    ]
    valid_bundles: list[_BundleRecord] = []
    for path in bundle_directories:
        try:
            valid_bundles.append(_load_bundle(path))
        except (TypeError, ValueError, OSError):
            checksum_failures += 1

    bundles_by_cell: dict[str, list[_BundleRecord]] = (
        defaultdict(list)
    )
    bundles_by_attempt: dict[str, _BundleRecord] = {}
    for bundle in valid_bundles:
        bundles_by_cell[
            bundle.episode.scheduled_cell_id
        ].append(bundle)
        if bundle.directory_name in bundles_by_attempt:
            checksum_failures += 1
        bundles_by_attempt[bundle.directory_name] = bundle

    lock_records: list[_LockRecord] = []
    for path in sorted(locks_root.glob("*.json")):
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("lock is not a regular file")
            lock = ScientificCellLockV1.from_json(
                path.read_bytes()
            )
            if path.name != f"{lock.scheduled_cell_id}.json":
                raise ValueError("cell-lock filename mismatch")
            lock_records.append(
                _LockRecord(filename=path.name, lock=lock)
            )
        except (TypeError, ValueError, OSError):
            checksum_failures += 1

    matched_bundle_attempts: set[str] = set()
    matched_lock_filenames: set[str] = set()
    resolved_cells: set[str] = set()

    for record in lock_records:
        lock = record.lock
        bundle = bundles_by_attempt.get(
            lock.execution_attempt_id
        )
        if bundle is None:
            continue
        if not _lock_matches_bundle(
            lock,
            bundle,
            expected_schedule_sha256=schedule_sha256,
        ):
            checksum_failures += 1
            continue
        terminal = terminals.get(lock.execution_attempt_id)
        if terminal is None or not _terminal_matches(
            terminal,
            lock=lock,
            bundle=bundle,
            expected_schedule_sha256=schedule_sha256,
        ):
            checksum_failures += 1
            continue
        if lock.execution_attempt_id not in started:
            continue
        matched_bundle_attempts.add(
            lock.execution_attempt_id
        )
        matched_lock_filenames.add(record.filename)
        if lock.scheduled_cell_id in expected_cell_ids:
            resolved_cells.add(lock.scheduled_cell_id)

    lock_without_bundle = sum(
        record.filename not in matched_lock_filenames
        for record in lock_records
    )
    bundles_without_lock = (
        len(bundle_directories)
        - len(matched_bundle_attempts)
    )

    duplicate_cells = sum(
        len(bundles) > 1
        for cell_id, bundles in bundles_by_cell.items()
        if cell_id in expected_cell_ids
    )
    best_of = duplicate_cells

    unresolved_cells = expected_cell_ids - resolved_cells
    publication_pending = 0
    artifact_failed_unresolved = 0
    unresolved_protocol = 0
    unresolved_infrastructure = 0

    for receipt in terminals.values():
        if receipt.scheduled_cell_id not in unresolved_cells:
            continue
        if (
            receipt.operational_finalization_status
            == "PUBLICATION_PENDING"
        ):
            publication_pending += 1
        if (
            receipt.operational_finalization_status
            == "ARTIFACT_IO_FAILED"
        ):
            artifact_failed_unresolved += 1
        if receipt.terminal_class == "PROTOCOL_CONFIGURATION_ERROR":
            unresolved_protocol += 1
        if (
            receipt.terminal_class
            == "PRE_RESULT_INFRASTRUCTURE_ERROR"
        ):
            unresolved_infrastructure += 1

    report_values = {
        "scheduled_cells": 670,
        "scientifically_resolved_cells": len(resolved_cells),
        "scientific_cell_locks": len(lock_records),
        "published_scientific_attempt_bundles": len(valid_bundles),
        "cell_locks_without_matching_published_bundle": lock_without_bundle,
        "published_bundles_without_matching_cell_lock": bundles_without_lock,
        "publication_pending": publication_pending,
        "artifact_io_failed_unresolved": artifact_failed_unresolved,
        "missing_terminal_receipts": missing_receipts,
        "checksum_failures": checksum_failures,
        "duplicate_cell_resolutions": duplicate_cells,
        "missing_task_seed_cells": len(unresolved_cells),
        "unresolved_protocol_errors": unresolved_protocol,
        "unresolved_pre_result_infrastructure_cells": unresolved_infrastructure,
        "best_of_run_selection": best_of,
    }

    approved = (
        report_values["scheduled_cells"] == 670
        and report_values["scientifically_resolved_cells"] == 670
        and report_values["scientific_cell_locks"] == 670
        and report_values["published_scientific_attempt_bundles"] == 670
        and all(
            report_values[name] == 0
            for name in (
                "cell_locks_without_matching_published_bundle",
                "published_bundles_without_matching_cell_lock",
                "publication_pending",
                "artifact_io_failed_unresolved",
                "missing_terminal_receipts",
                "checksum_failures",
                "duplicate_cell_resolutions",
                "missing_task_seed_cells",
                "unresolved_protocol_errors",
                "unresolved_pre_result_infrastructure_cells",
                "best_of_run_selection",
            )
        )
    )

    return ResultAuditReport(
        **report_values,
        approved=approved,
    )
