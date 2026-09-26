"""Strict trusted-manifest loading for E1 evaluator task selection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .canonical_evidence import (
    require_lower_sha256,
    strict_json_loads,
)


_EXPECTED_FIELDS = frozenset(
    {
        "gamefile",
        "gamefile_sha1",
        "id",
        "index",
        "root",
        "split",
        "task_id",
        "task_type",
        "traj_file",
    }
)


@dataclass(frozen=True, slots=True)
class FrozenTaskRecord:
    """One immutable task selected by the frozen strict-134 manifest."""

    index: int
    task_id: str
    split: str
    task_type: str
    gamefile: str
    gamefile_sha1: str
    root: str
    traj_file: str

    def __post_init__(self) -> None:
        if type(self.index) is not int:
            raise TypeError("index must be int")
        if self.index < 0:
            raise ValueError("index must be non-negative")

        for name in (
            "task_id",
            "split",
            "task_type",
            "gamefile",
            "root",
            "traj_file",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be non-empty")

        if (
            len(self.gamefile_sha1) != 40
            or any(
                character not in "0123456789abcdef"
                for character in self.gamefile_sha1
            )
        ):
            raise ValueError(
                "gamefile_sha1 must be lowercase SHA-1"
            )


def _require_string(
    payload: dict[str, object],
    name: str,
) -> str:
    value = payload[name]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def load_frozen_task_manifest(
    *,
    manifest_path: Path,
    expected_sha256: str,
    expected_record_count: int = 134,
) -> tuple[FrozenTaskRecord, ...]:
    """Load the exact ordered manifest without scanning a dataset."""

    manifest_path = Path(manifest_path)
    require_lower_sha256(
        "expected_sha256",
        expected_sha256,
    )

    if type(expected_record_count) is not int:
        raise TypeError("expected_record_count must be int")
    if expected_record_count <= 0:
        raise ValueError(
            "expected_record_count must be positive"
        )

    if manifest_path.is_symlink():
        raise ValueError("manifest_path must not be a symlink")
    if not manifest_path.is_file():
        raise ValueError(
            "manifest_path must identify a regular file"
        )

    raw = manifest_path.read_bytes()
    observed_sha256 = hashlib.sha256(raw).hexdigest()
    if observed_sha256 != expected_sha256:
        raise ValueError(
            "manifest SHA-256 does not match expected identity"
        )

    if not raw.endswith(b"\n"):
        raise ValueError(
            "manifest must end with exactly one LF-delimited record"
        )

    raw_lines = raw.splitlines()
    if any(not line for line in raw_lines):
        raise ValueError("manifest must not contain blank lines")
    if len(raw_lines) != expected_record_count:
        raise ValueError(
            "manifest record count does not match expected count"
        )

    records: list[FrozenTaskRecord] = []
    seen_ids: set[str] = set()
    seen_gamefiles: set[str] = set()

    for expected_index, raw_line in enumerate(raw_lines):
        payload = strict_json_loads(raw_line)
        if not isinstance(payload, dict):
            raise ValueError(
                f"manifest record {expected_index} must be an object"
            )

        observed_fields = set(payload)
        if observed_fields != _EXPECTED_FIELDS:
            missing = sorted(
                _EXPECTED_FIELDS - observed_fields
            )
            unknown = sorted(
                observed_fields - _EXPECTED_FIELDS
            )
            raise ValueError(
                "manifest record fields do not match contract: "
                f"missing={missing}, unknown={unknown}"
            )

        index = payload["index"]
        if type(index) is not int:
            raise TypeError(
                f"record {expected_index} index must be int"
            )
        if index != expected_index:
            raise ValueError(
                f"record index mismatch: expected {expected_index}, "
                f"observed {index}"
            )

        record_id = _require_string(payload, "id")
        expected_id = (
            "alfworld_valid_unseen_all134_"
            f"{expected_index:04d}"
        )
        if record_id != expected_id:
            raise ValueError(
                f"record ID mismatch: expected {expected_id}"
            )

        split = _require_string(payload, "split")
        if split != "valid_unseen":
            raise ValueError(
                "all frozen tasks must use valid_unseen"
            )

        gamefile = _require_string(payload, "gamefile")
        root = _require_string(payload, "root")
        traj_file = _require_string(payload, "traj_file")
        source_task_id = _require_string(payload, "task_id")
        task_type = _require_string(payload, "task_type")
        gamefile_sha1 = _require_string(
            payload,
            "gamefile_sha1",
        )

        if (
            len(gamefile_sha1) != 40
            or any(
                character not in "0123456789abcdef"
                for character in gamefile_sha1
            )
        ):
            raise ValueError(
                "gamefile_sha1 must be lowercase SHA-1"
            )

        if record_id in seen_ids:
            raise ValueError(
                f"duplicate task ID: {record_id}"
            )
        if gamefile in seen_gamefiles:
            raise ValueError(
                f"duplicate gamefile: {gamefile}"
            )

        gamefile_path = Path(gamefile)
        root_path = Path(root)
        traj_path = Path(traj_file)

        for name, path in (
            ("gamefile", gamefile_path),
            ("root", root_path),
            ("traj_file", traj_path),
        ):
            if not path.is_absolute():
                raise ValueError(
                    f"{name} must be an absolute path"
                )

        if gamefile_path.parent != root_path:
            raise ValueError(
                "gamefile parent must equal root"
            )
        if traj_path.parent != root_path:
            raise ValueError(
                "traj_file parent must equal root"
            )
        if root_path.name != source_task_id:
            raise ValueError(
                "manifest task_id must equal root basename"
            )

        seen_ids.add(record_id)
        seen_gamefiles.add(gamefile)

        records.append(
            FrozenTaskRecord(
                index=index,
                task_id=record_id,
                split=split,
                task_type=task_type,
                gamefile=gamefile,
                gamefile_sha1=gamefile_sha1,
                root=root,
                traj_file=traj_file,
            )
        )

    return tuple(records)
