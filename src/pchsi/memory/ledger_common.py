from __future__ import annotations

from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import re

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    strict_json_loads,
)


_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$"
)


def _text(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ch in value for ch in ("\0", "\r", "\n"))
    ):
        raise ValueError(f"{name} must be nonempty single-line str")
    return value


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise OSError("os.write made no progress")
        view = view[count:]


def _fsync_directory(path: Path) -> None:
    fd = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@dataclass(frozen=True, slots=True)
class AppendOnlyLedgerEntryV1:
    ledger_id: str
    ledger_kind: str
    entry_id: str
    event_type: str
    memory_lineage_id: str
    record_version: int
    event_time_utc: str
    repository_commit: str
    payload: dict[str, object]
    previous_entry_sha256: str | None
    entry_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in ("ledger_id", "ledger_kind", "entry_id", "event_type"):
            _text(name, getattr(self, name))
        require_lower_sha256(
            "memory_lineage_id",
            self.memory_lineage_id,
        )
        if type(self.record_version) is not int or self.record_version < 1:
            raise ValueError("record_version must be positive int")
        if (
            not isinstance(self.event_time_utc, str)
            or _UTC_RE.fullmatch(self.event_time_utc) is None
        ):
            raise ValueError(
                "event_time_utc must be caller-supplied UTC RFC3339"
            )
        if (
            not isinstance(self.repository_commit, str)
            or _COMMIT_RE.fullmatch(self.repository_commit) is None
        ):
            raise ValueError(
                "repository_commit must be 40 lowercase hex"
            )
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be dict")
        canonical_json_bytes(self.payload)
        if self.previous_entry_sha256 is not None:
            require_lower_sha256(
                "previous_entry_sha256",
                self.previous_entry_sha256,
            )
        expected = sha256_bytes(
            b"FAILURE_MEMORY_LEDGER_ENTRY_V1\0"
            + canonical_json_bytes(
                self._payload_without_sha()
            )
        )
        if self.entry_sha256 is None:
            object.__setattr__(
                self,
                "entry_sha256",
                expected,
            )
        elif self.entry_sha256 != expected:
            raise ValueError("entry_sha256 mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": "FAILURE_MEMORY_LEDGER_ENTRY_V1",
            "schema_version": 1,
            "ledger_id": self.ledger_id,
            "ledger_kind": self.ledger_kind,
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "event_time_utc": self.event_time_utc,
            "repository_commit": self.repository_commit,
            "payload": self.payload,
            "previous_entry_sha256": self.previous_entry_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "entry_sha256": self.entry_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_json(
        cls,
        raw: str | bytes,
    ) -> "AppendOnlyLedgerEntryV1":
        payload = strict_json_loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("ledger entry must be object")
        expected = {
            "schema_id",
            "schema_version",
            "ledger_id",
            "ledger_kind",
            "entry_id",
            "event_type",
            "memory_lineage_id",
            "record_version",
            "event_time_utc",
            "repository_commit",
            "payload",
            "previous_entry_sha256",
            "entry_sha256",
        }
        if set(payload) != expected:
            raise ValueError("ledger entry fields mismatch")
        if (
            payload["schema_id"]
            != "FAILURE_MEMORY_LEDGER_ENTRY_V1"
            or payload["schema_version"] != 1
        ):
            raise ValueError("ledger entry schema mismatch")
        return cls(
            ledger_id=payload["ledger_id"],
            ledger_kind=payload["ledger_kind"],
            entry_id=payload["entry_id"],
            event_type=payload["event_type"],
            memory_lineage_id=payload["memory_lineage_id"],
            record_version=payload["record_version"],
            event_time_utc=payload["event_time_utc"],
            repository_commit=payload["repository_commit"],
            payload=payload["payload"],
            previous_entry_sha256=payload[
                "previous_entry_sha256"
            ],
            entry_sha256=payload["entry_sha256"],
        )


def read_ledger_v1(
    path: Path,
) -> tuple[AppendOnlyLedgerEntryV1, ...]:
    path = Path(path)
    if not path.exists():
        return ()
    if path.is_symlink() or not path.is_file():
        raise ValueError("ledger path invalid")
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise ValueError("ledger lacks terminal newline")
    values = tuple(
        AppendOnlyLedgerEntryV1.from_json(line)
        for line in data.splitlines()
        if line
    )
    previous = None
    seen = set()
    identity = None
    for entry in values:
        if identity is None:
            identity = (
                entry.ledger_id,
                entry.ledger_kind,
            )
        elif identity != (
            entry.ledger_id,
            entry.ledger_kind,
        ):
            raise ValueError(
                "ledger identity changed"
            )
        if entry.entry_id in seen:
            raise ValueError(
                "duplicate ledger entry_id"
            )
        if entry.previous_entry_sha256 != previous:
            raise ValueError(
                "ledger hash chain broken"
            )
        seen.add(entry.entry_id)
        previous = entry.entry_sha256
    return values


def append_ledger_entry_v1(
    path: Path,
    entry: AppendOnlyLedgerEntryV1,
) -> None:
    path = Path(path)
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("ledger parent invalid")
    if path.is_symlink():
        raise ValueError(
            "ledger path must not be symlink"
        )
    lock = parent / f".{path.name}.lock"
    lock_fd = os.open(
        lock,
        os.O_CREAT | os.O_RDWR,
        0o600,
    )
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        existing = read_ledger_v1(path)
        if existing:
            last = existing[-1]
            if any(
                item.entry_id == entry.entry_id
                for item in existing
            ):
                raise ValueError(
                    "duplicate ledger entry_id"
                )
            if (
                entry.ledger_id != last.ledger_id
                or entry.ledger_kind
                != last.ledger_kind
            ):
                raise ValueError(
                    "ledger identity mismatch"
                )
            if (
                entry.previous_entry_sha256
                != last.entry_sha256
            ):
                raise ValueError(
                    "previous_entry_sha256 mismatch"
                )
            old = path.read_bytes()
        else:
            if entry.previous_entry_sha256 is not None:
                raise ValueError(
                    "first ledger entry previous SHA "
                    "must be null"
                )
            old = b""

        temp = (
            parent
            / f".{path.name}.{entry.entry_sha256}.tmp"
        )
        if temp.exists() or temp.is_symlink():
            raise FileExistsError(str(temp))

        fd = os.open(
            temp,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
        published = False
        try:
            _write_all(
                fd,
                old + entry.canonical_bytes(),
            )
            os.fsync(fd)
        except BaseException:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
            raise
        finally:
            os.close(fd)

        try:
            os.replace(temp, path)
            _fsync_directory(parent)
            published = True
        finally:
            if not published:
                try:
                    temp.unlink()
                except FileNotFoundError:
                    pass

        rebuilt = read_ledger_v1(path)
        if not rebuilt or rebuilt[-1] != entry:
            raise RuntimeError(
                "ledger publication verification failed"
            )
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def make_ledger_entry_v1(
    **kwargs,
) -> AppendOnlyLedgerEntryV1:
    return AppendOnlyLedgerEntryV1(
        entry_sha256=None,
        **kwargs,
    )
