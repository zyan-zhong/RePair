from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from pchsi.evaluation.task_manifest import FrozenTaskRecord
from pchsi.evaluation.run_schedule import ScheduledCell, scheduled_cell_id


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha256(value: str, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _regular_file(path: Path, name: str) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{name} must be a regular non-symlink file")
    return path


def _bound_regular_file(root: Path, relative: str, name: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{name} relative path must be non-empty")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"{name} relative path escapes the frozen root")
    root = Path(root).resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{name} path escapes the frozen root") from error
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError(f"{name} target must be a regular non-symlink file")
    return candidate


def _load_jsonl(path: Path, *, expected_sha256: str) -> list[dict[str, Any]]:
    path = _regular_file(path, "manifest_path")
    _require_sha256(expected_sha256, "expected_sha256")
    if _sha256_file(path) != expected_sha256:
        raise ValueError("manifest SHA-256 mismatch")
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line:
            raise ValueError(f"blank JSONL line at {line_number}")
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            raise ValueError(f"manifest row {line_number} must be object")
        rows.append(value)
    return rows


def load_clean_train_pool_records(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    train_root: Path,
    expected_pool: str,
    expected_count: int,
) -> tuple[FrozenTaskRecord, ...]:
    if expected_pool not in {"TRAIN_UPDATE", "TRAIN_SELECT", "TRAIN_AUDIT"}:
        raise ValueError("unexpected train pool")
    if type(expected_count) is not int or expected_count <= 0:
        raise ValueError("expected_count must be positive int")
    train_root = Path(train_root).resolve()
    if train_root.is_symlink() or not train_root.is_dir():
        raise ValueError("train_root must be a regular directory")
    rows = _load_jsonl(manifest_path, expected_sha256=expected_manifest_sha256)
    if len(rows) != expected_count:
        raise ValueError("train-pool record count mismatch")

    records: list[FrozenTaskRecord] = []
    seen_ids: set[str] = set()
    seen_indices: set[int] = set()
    for row in rows:
        if row.get("schema_id") != "ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1":
            raise ValueError("unexpected clean train task schema")
        if row.get("split") != "train" or row.get("train_pool") != expected_pool:
            raise ValueError("clean train row split/pool mismatch")
        index = row.get("index")
        task_id = row.get("id")
        task_type = row.get("task_type")
        if type(index) is not int or index < 0 or index > 9999:
            raise ValueError("clean train task index invalid")
        if index in seen_indices:
            raise ValueError("duplicate clean train task index")
        if not isinstance(task_id, str) or not task_id or task_id in seen_ids:
            raise ValueError("clean train task id invalid or duplicate")
        if not isinstance(task_type, str) or not task_type:
            raise ValueError("clean train task_type invalid")

        gamefile = _bound_regular_file(
            train_root,
            str(row.get("gamefile_relpath")),
            "gamefile",
        )
        traj_file = _bound_regular_file(
            train_root,
            str(row.get("traj_file_relpath")),
            "traj_file",
        )
        initial_state = _bound_regular_file(
            train_root,
            str(row.get("initial_state_relpath")),
            "initial_state",
        )
        if gamefile.parent != traj_file.parent or gamefile.parent != initial_state.parent:
            raise ValueError("gamefile/traj/initial-state root mismatch")
        observed_sha1 = hashlib.sha1(gamefile.read_bytes()).hexdigest()
        observed_sha256 = _sha256_file(gamefile)
        if observed_sha1 != row.get("gamefile_sha1"):
            raise ValueError("gamefile SHA-1 mismatch")
        if observed_sha256 != row.get("gamefile_sha256"):
            raise ValueError("gamefile SHA-256 mismatch")
        if _sha256_file(traj_file) != row.get("traj_sha256"):
            raise ValueError("traj_data SHA-256 mismatch")
        if _sha256_file(initial_state) != row.get("initial_state_sha256"):
            raise ValueError("initial_state SHA-256 mismatch")

        records.append(
            FrozenTaskRecord(
                index=index,
                task_id=task_id,
                split="train",
                task_type=task_type,
                gamefile=str(gamefile),
                gamefile_sha1=observed_sha1,
                root=str(gamefile.parent),
                traj_file=str(traj_file),
            )
        )
        seen_ids.add(task_id)
        seen_indices.add(index)
    return tuple(records)


def load_official_benchmark_records(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    expected_split: str,
    expected_count: int,
) -> tuple[FrozenTaskRecord, ...]:
    if expected_split not in {"valid_seen", "valid_unseen"}:
        raise ValueError("official benchmark split invalid")
    if (expected_split, expected_count) not in {("valid_seen", 140), ("valid_unseen", 134)}:
        raise ValueError("official benchmark count mismatch")
    rows = _load_jsonl(manifest_path, expected_sha256=expected_manifest_sha256)
    if len(rows) != expected_count:
        raise ValueError("official benchmark record count mismatch")
    records: list[FrozenTaskRecord] = []
    seen_ids: set[str] = set()
    for expected_index, row in enumerate(rows):
        if row.get("index") != expected_index or row.get("split") != expected_split:
            raise ValueError("official benchmark row identity mismatch")
        task_id = row.get("id")
        if not isinstance(task_id, str) or not task_id or task_id in seen_ids:
            raise ValueError("official benchmark task id invalid or duplicate")
        gamefile = _regular_file(Path(str(row.get("gamefile"))), "gamefile").resolve()
        traj_file = _regular_file(Path(str(row.get("traj_file"))), "traj_file").resolve()
        root = Path(str(row.get("root"))).resolve()
        if not root.is_dir() or gamefile.parent != root or traj_file.parent != root:
            raise ValueError("official benchmark path binding mismatch")
        observed_sha1 = hashlib.sha1(gamefile.read_bytes()).hexdigest()
        if observed_sha1 != row.get("gamefile_sha1"):
            raise ValueError("official benchmark gamefile SHA-1 mismatch")
        records.append(
            FrozenTaskRecord(
                index=expected_index,
                task_id=task_id,
                split=expected_split,
                task_type=str(row.get("task_type")),
                gamefile=str(gamefile),
                gamefile_sha1=observed_sha1,
                root=str(root),
                traj_file=str(traj_file),
            )
        )
        seen_ids.add(task_id)
    return tuple(records)


@dataclass(frozen=True, slots=True)
class CleanScheduledEpisodeV1:
    scientific_cell_id: str
    split: str
    cell: ScheduledCell
    execution_attempt_id: str
    attempt_ordinal: int


def bind_stage2c_official_schedule(
    *,
    schedule_path: Path,
    expected_schedule_sha256: str,
    records: Sequence[FrozenTaskRecord],
) -> tuple[CleanScheduledEpisodeV1, ...]:
    schedule_path = _regular_file(schedule_path, "schedule_path")
    _require_sha256(expected_schedule_sha256, "expected_schedule_sha256")
    if _sha256_file(schedule_path) != expected_schedule_sha256:
        raise ValueError("official schedule file SHA-256 mismatch")
    value = json.loads(schedule_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_id") != "PI0_CLEAN_OFFICIAL_BENCHMARK_SCHEDULE_V1":
        raise ValueError("unexpected official schedule schema")
    cells = value.get("cells")
    frozen_records = tuple(records)
    if not isinstance(cells, list) or len(cells) != len(frozen_records):
        raise ValueError("official schedule cell population mismatch")
    by_index = {record.index: record for record in frozen_records}
    bound: list[CleanScheduledEpisodeV1] = []
    seen_scientific: set[str] = set()
    for row in cells:
        if not isinstance(row, dict):
            raise ValueError("official schedule cell must be object")
        index = row.get("task_index")
        seed = row.get("seed")
        task = by_index.get(index)
        if task is None or task.task_id != row.get("task_id") or task.split != row.get("split"):
            raise ValueError("official schedule task binding mismatch")
        expected_runtime_id = scheduled_cell_id(task_index=index, seed=seed)
        if row.get("runtime_scheduled_cell_id") != expected_runtime_id:
            raise ValueError("runtime scheduled cell id mismatch")
        attempt_ordinal = row.get("attempt_ordinal")
        if type(attempt_ordinal) is not int or attempt_ordinal != 0:
            raise ValueError("official primary schedule requires attempt_ordinal=0")
        expected_attempt_id = expected_runtime_id + "-a000"
        if row.get("execution_attempt_id") != expected_attempt_id:
            raise ValueError("execution attempt id mismatch")
        scientific_id = row.get("scientific_cell_id")
        if not isinstance(scientific_id, str) or not scientific_id or scientific_id in seen_scientific:
            raise ValueError("scientific cell id invalid or duplicate")
        bound.append(
            CleanScheduledEpisodeV1(
                scientific_cell_id=scientific_id,
                split=task.split,
                cell=ScheduledCell(
                    scheduled_cell_id=expected_runtime_id,
                    task_index=index,
                    task_id=task.task_id,
                    seed=seed,
                ),
                execution_attempt_id=expected_attempt_id,
                attempt_ordinal=0,
            )
        )
        seen_scientific.add(scientific_id)
    return tuple(bound)


def build_clean_train_schedule(
    *,
    records: Sequence[FrozenTaskRecord],
    train_pool: str,
    seed: int,
) -> tuple[CleanScheduledEpisodeV1, ...]:
    if train_pool not in {"TRAIN_UPDATE", "TRAIN_SELECT", "TRAIN_AUDIT"}:
        raise ValueError("unexpected train pool")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be non-negative int")
    bound: list[CleanScheduledEpisodeV1] = []
    for record in records:
        if record.split != "train":
            raise ValueError("train schedule received non-train task")
        runtime_id = scheduled_cell_id(task_index=record.index, seed=seed)
        scientific_id = (
            "clean-"
            + train_pool.lower().replace("_", "-")
            + f"-t{record.index:04d}-s{seed:010d}"
        )
        bound.append(
            CleanScheduledEpisodeV1(
                scientific_cell_id=scientific_id,
                split="train",
                cell=ScheduledCell(
                    scheduled_cell_id=runtime_id,
                    task_index=record.index,
                    task_id=record.task_id,
                    seed=seed,
                ),
                execution_attempt_id=runtime_id + "-a000",
                attempt_ordinal=0,
            )
        )
    return tuple(bound)
