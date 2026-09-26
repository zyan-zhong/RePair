"""Content-addressed manifest identity helpers for S1 artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterable, Mapping

from .canonical import canonical_json_bytes, sha256_hex


__all__ = [
    "DetachedSha256Record",
    "ManifestHashes",
    "detached_sha256_record_bytes",
    "exact_file_sha256",
    "semantic_projection_sha256",
    "verify_detached_sha256_record",
    "write_canonical_manifest",
    "write_detached_sha256_record",
]


@dataclass(frozen=True, slots=True)
class ManifestHashes:
    """Hashes that intentionally describe different artifact identities."""

    semantic_projection_sha256: str
    exact_file_sha256: str


@dataclass(frozen=True, slots=True)
class DetachedSha256Record:
    """Identity of a target file and its detached sha256sum-style record."""

    target_sha256: str
    record_sha256: str
    record_bytes: bytes


def _project_top_level(
    value: Mapping[str, object],
    *,
    excluded_top_level_fields: Iterable[str],
) -> dict[str, object]:
    excluded = frozenset(excluded_top_level_fields)

    if any(
        not isinstance(field, str) or not field
        for field in excluded
    ):
        raise ValueError(
            "excluded_top_level_fields must contain non-empty strings"
        )

    return {
        key: child
        for key, child in value.items()
        if key not in excluded
    }


def semantic_projection_sha256(
    value: Mapping[str, object],
    *,
    excluded_top_level_fields: Iterable[str] = (),
) -> str:
    """Hash the explicit semantic top-level projection of a manifest."""

    if not isinstance(value, Mapping):
        raise TypeError("value must be a mapping")

    projection = _project_top_level(
        value,
        excluded_top_level_fields=excluded_top_level_fields,
    )

    return sha256_hex(
        canonical_json_bytes(projection)
    )


def exact_file_sha256(path: Path) -> str:
    """Hash the exact bytes of one regular file."""

    path = Path(path)

    if not path.is_file():
        raise ValueError(
            f"path must identify a regular file: {path}"
        )

    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _validate_display_name(display_name: str) -> None:
    if not isinstance(display_name, str) or not display_name:
        raise ValueError("display_name must be a non-empty string")

    if "\n" in display_name or "\r" in display_name:
        raise ValueError("display_name must not contain line breaks")

    if display_name in {".", ".."}:
        raise ValueError("display_name must not be dot or dot-dot")

    if "/" in display_name or "\\" in display_name:
        raise ValueError(
            "display_name must be one file name, not a path"
        )


def detached_sha256_record_bytes(
    *,
    target_sha256: str,
    display_name: str,
) -> bytes:
    """Build one deterministic sha256sum-style detached record."""

    if (
        not isinstance(target_sha256, str)
        or len(target_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in target_sha256
        )
    ):
        raise ValueError(
            "target_sha256 must be lowercase SHA-256 hex"
        )

    _validate_display_name(display_name)

    try:
        encoded_name = display_name.encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeEncodeError as error:
        raise ValueError(
            "display_name must be valid UTF-8"
        ) from error

    return (
        target_sha256.encode("ascii")
        + b"  "
        + encoded_name
        + b"\n"
    )


def write_canonical_manifest(
    path: Path,
    value: Mapping[str, object],
    *,
    excluded_top_level_fields: Iterable[str] = (),
) -> ManifestHashes:
    """Write canonical manifest bytes and return semantic/exact identities.

    The exact-file digest is computed after serialization and is returned
    to the caller. The manifest itself is rejected if it already contains
    that exact digest, preventing a self-referential exact-file hash.
    """

    path = Path(path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = canonical_json_bytes(
        dict(value)
    )
    exact_digest = sha256_hex(encoded)

    if exact_digest.encode("ascii") in encoded:
        raise ValueError(
            "manifest must not contain its own exact-file SHA-256"
        )

    temporary = path.with_name(
        path.name + ".tmp"
    )
    temporary.write_bytes(encoded)
    temporary.replace(path)

    return ManifestHashes(
        semantic_projection_sha256=semantic_projection_sha256(
            value,
            excluded_top_level_fields=excluded_top_level_fields,
        ),
        exact_file_sha256=exact_digest,
    )


def write_detached_sha256_record(
    *,
    target_path: Path,
    record_path: Path,
    display_name: str | None = None,
) -> DetachedSha256Record:
    """Write a detached exact-file record for one existing target."""

    target_path = Path(target_path)
    record_path = Path(record_path)

    target_digest = exact_file_sha256(target_path)
    name = (
        target_path.name
        if display_name is None
        else display_name
    )
    record_bytes = detached_sha256_record_bytes(
        target_sha256=target_digest,
        display_name=name,
    )

    record_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = record_path.with_name(
        record_path.name + ".tmp"
    )
    temporary.write_bytes(record_bytes)
    temporary.replace(record_path)

    return DetachedSha256Record(
        target_sha256=target_digest,
        record_sha256=sha256_hex(record_bytes),
        record_bytes=record_bytes,
    )


def verify_detached_sha256_record(
    *,
    target_path: Path,
    record_path: Path,
) -> bool:
    """Verify one exact sha256sum-style record against a target file."""

    target_path = Path(target_path)
    record_path = Path(record_path)

    try:
        record_bytes = record_path.read_bytes()
        text = record_bytes.decode(
            "utf-8",
            errors="strict",
        )
    except (
        OSError,
        UnicodeDecodeError,
    ):
        return False

    if not text.endswith("\n") or text.count("\n") != 1:
        return False

    line = text[:-1]

    if len(line) < 67 or line[64:66] != "  ":
        return False

    digest = line[:64]
    display_name = line[66:]

    try:
        expected = detached_sha256_record_bytes(
            target_sha256=digest,
            display_name=display_name,
        )
    except ValueError:
        return False

    if expected != record_bytes:
        return False

    if display_name != target_path.name:
        return False

    try:
        observed = exact_file_sha256(target_path)
    except (OSError, ValueError):
        return False

    return observed == digest
# ---------------------------------------------------------------------------
# Task 14: reproducible candidate runtime manifest
# ---------------------------------------------------------------------------

from dataclasses import dataclass as _task14_dataclass
import json as _task14_json
import re as _task14_re


_TASK14_SHA256_RE = _task14_re.compile(r"^[0-9a-f]{64}$")


@_task14_dataclass(frozen=True, slots=True)
class RuntimeManifest:
    schema_version: int
    status: str
    python_sha256: str
    bootstrap_sha256: str
    interpreter_path: str
    needed_libraries: tuple[str, ...]
    source_date_epoch: int
    toolchain: str

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if self.status != "candidate_pending_static_and_semantic_review":
            raise ValueError("invalid candidate status")

        for name in ("python_sha256", "bootstrap_sha256"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or _TASK14_SHA256_RE.fullmatch(value) is None
            ):
                raise ValueError(f"{name} must be lowercase SHA-256")

        if (
            not isinstance(self.interpreter_path, str)
            or not self.interpreter_path.startswith("/")
            or "\x00" in self.interpreter_path
        ):
            raise ValueError("interpreter_path must be absolute")

        if (
            not isinstance(self.needed_libraries, tuple)
            or tuple(sorted(set(self.needed_libraries)))
            != self.needed_libraries
        ):
            raise ValueError(
                "needed_libraries must be a sorted unique tuple"
            )

        if (
            isinstance(self.source_date_epoch, bool)
            or not isinstance(self.source_date_epoch, int)
            or self.source_date_epoch < 0
        ):
            raise ValueError(
                "source_date_epoch must be a non-negative integer"
            )

        if not isinstance(self.toolchain, str) or not self.toolchain:
            raise ValueError("toolchain must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "python_sha256": self.python_sha256,
            "bootstrap_sha256": self.bootstrap_sha256,
            "interpreter_path": self.interpreter_path,
            "needed_libraries": list(self.needed_libraries),
            "source_date_epoch": self.source_date_epoch,
            "toolchain": self.toolchain,
        }

    def canonical_bytes(self) -> bytes:
        return (
            _task14_json.dumps(
                self.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
