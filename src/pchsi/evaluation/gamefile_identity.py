"""Fixture-safe gamefile byte identity for E1 readiness."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import ClassVar

from .canonical_evidence import (
    canonical_json_text,
    strict_json_loads,
)
from .schema_contract import (
    validate_payload_against_schema,
)
from .task_manifest import FrozenTaskRecord


@dataclass(frozen=True, slots=True)
class GamefileIdentityRecordV1:
    index: int
    task_id: str
    gamefile_sha1: str
    gamefile_sha256: str

    _KEYS: ClassVar[set[str]] = {
        "index",
        "task_id",
        "gamefile_sha1",
        "gamefile_sha256",
    }

    def __post_init__(self) -> None:
        if type(self.index) is not int:
            raise TypeError("index must be int")
        if self.index < 0:
            raise ValueError("index must be non-negative")
        if not isinstance(self.task_id, str) or not self.task_id:
            raise ValueError("task_id must be non-empty")
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
        if (
            len(self.gamefile_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.gamefile_sha256
            )
        ):
            raise ValueError(
                "gamefile_sha256 must be lowercase SHA-256"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "task_id": self.task_id,
            "gamefile_sha1": self.gamefile_sha1,
            "gamefile_sha256": self.gamefile_sha256,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "GamefileIdentityRecordV1":
        if not isinstance(value, dict):
            raise TypeError(
                "gamefile identity record must be an object"
            )
        if set(value) != cls._KEYS:
            raise ValueError(
                "gamefile identity record fields do not match"
            )
        return cls(
            index=value["index"],
            task_id=value["task_id"],
            gamefile_sha1=value["gamefile_sha1"],
            gamefile_sha256=value["gamefile_sha256"],
        )


@dataclass(frozen=True, slots=True)
class GamefileIdentityManifestV1:
    SCHEMA_ID: ClassVar[str] = (
        "E1_GAMEFILE_SHA256_PREFLIGHT_V1"
    )
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    manifest_id: str
    record_count: int
    records: tuple[GamefileIdentityRecordV1, ...]

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "manifest_id",
        "record_count",
        "records",
    }

    def __post_init__(self) -> None:
        if any(
            not isinstance(
                item,
                GamefileIdentityRecordV1,
            )
            for item in self.records
        ):
            raise TypeError(
                "records must contain "
                "GamefileIdentityRecordV1"
            )
        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )
        if self.record_count != len(self.records):
            raise ValueError(
                "record_count must equal records length"
            )
        if tuple(
            item.index for item in self.records
        ) != tuple(range(len(self.records))):
            raise ValueError(
                "identity record indices must be contiguous"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "record_count": self.record_count,
            "records": [
                item.to_dict()
                for item in self.records
            ],
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "GamefileIdentityManifestV1":
        if not isinstance(value, dict):
            raise TypeError(
                "gamefile identity manifest must be an object"
            )
        if set(value) != cls._KEYS:
            raise ValueError(
                "gamefile identity manifest fields do not match"
            )
        raw_records = value["records"]
        if not isinstance(raw_records, list):
            raise TypeError("records must be a JSON array")
        return cls(
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            manifest_id=value["manifest_id"],
            record_count=value["record_count"],
            records=tuple(
                GamefileIdentityRecordV1.from_dict(item)
                for item in raw_records
            ),
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "GamefileIdentityManifestV1":
        return cls.from_dict(strict_json_loads(value))


def _file_hashes(path: Path) -> tuple[str, str]:
    if path.is_symlink():
        raise ValueError(
            f"gamefile must not be a symlink: {path}"
        )
    if not path.is_file():
        raise ValueError(
            f"gamefile must be a regular file: {path}"
        )

    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            sha1.update(chunk)
            sha256.update(chunk)
    return sha1.hexdigest(), sha256.hexdigest()


def _write_no_clobber(
    *,
    path: Path,
    payload: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError(
                    "short write while publishing manifest"
                )
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_gamefile_identity_manifest(
    *,
    records: Sequence[FrozenTaskRecord],
    output_path: Path,
) -> GamefileIdentityManifestV1:
    """Build a no-clobber byte-identity artifact in task order."""

    if isinstance(records, (str, bytes, bytearray)):
        raise TypeError(
            "records must be a sequence of FrozenTaskRecord"
        )

    frozen_records = tuple(records)
    if not frozen_records:
        raise ValueError("records must not be empty")
    if any(
        not isinstance(item, FrozenTaskRecord)
        for item in frozen_records
    ):
        raise TypeError(
            "records must contain FrozenTaskRecord"
        )

    if tuple(
        item.index for item in frozen_records
    ) != tuple(range(len(frozen_records))):
        raise ValueError(
            "task record indices must be contiguous"
        )
    if len(
        {
            item.task_id
            for item in frozen_records
        }
    ) != len(frozen_records):
        raise ValueError("task IDs must be unique")

    identity_records: list[
        GamefileIdentityRecordV1
    ] = []

    for record in frozen_records:
        path = Path(record.gamefile)
        observed_sha1, observed_sha256 = _file_hashes(
            path
        )
        if observed_sha1 != record.gamefile_sha1:
            raise ValueError(
                f"gamefile SHA-1 mismatch for {record.task_id}"
            )
        identity_records.append(
            GamefileIdentityRecordV1(
                index=record.index,
                task_id=record.task_id,
                gamefile_sha1=observed_sha1,
                gamefile_sha256=observed_sha256,
            )
        )

    manifest = GamefileIdentityManifestV1(
        schema_id=(
            "E1_GAMEFILE_SHA256_PREFLIGHT_V1"
        ),
        schema_version=1,
        manifest_id=(
            "E1_GAMEFILE_SHA256_PREFLIGHT_V1"
        ),
        record_count=len(identity_records),
        records=tuple(identity_records),
    )

    _write_no_clobber(
        path=Path(output_path),
        payload=manifest.to_json().encode("utf-8"),
    )
    return manifest
