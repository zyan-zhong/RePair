"""Canonical, read-only utilities for reference-loop evidence materialization."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any


_HEX = frozenset("0123456789abcdef")


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_without_newline(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def strict_json_loads(raw: str | bytes) -> object:
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_constant,
    )


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON constant: {value}")


def require_object(name: str, value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a JSON object")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{name} keys must be strings")
    return value


def require_array(name: str, value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a JSON array")
    return value


def require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text")
    if any(ch in value for ch in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains a forbidden control character")
    return value


def require_optional_text(name: str, value: object) -> str | None:
    if value is None:
        return None
    return require_text(name, value)


def require_nonnegative_int(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def require_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")
    return value


def require_sha256(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in _HEX for ch in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256")
    return value


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def domain_hash(
    domain: str,
    payload: Mapping[str, object],
    *,
    excluded_field: str | None = None,
) -> str:
    body = dict(payload)
    if excluded_field is not None:
        body.pop(excluded_field, None)
    return sha256_bytes(
        domain.encode("utf-8")
        + b"\0"
        + canonical_json_without_newline(body)
    )


def ensure_regular_no_symlink(path: Path, *, name: str) -> Path:
    if path.is_symlink():
        raise ValueError(f"{name} must not be a symlink: {path}")
    try:
        mode = path.stat().st_mode
    except FileNotFoundError as error:
        raise ValueError(f"{name} does not exist: {path}") from error
    if not stat.S_ISREG(mode):
        raise ValueError(f"{name} must be a regular file: {path}")
    current = path.resolve()
    probe = path.absolute()
    # Reject symlinked parent components too.
    for parent in (probe, *probe.parents):
        if parent.exists() and parent.is_symlink():
            raise ValueError(f"{name} has a symlink component: {parent}")
        if parent == parent.parent:
            break
    return current


def ensure_directory_no_symlink(path: Path, *, name: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{name} must be a non-symlink directory: {path}")
    probe = path.absolute()
    for parent in (probe, *probe.parents):
        if parent.exists() and parent.is_symlink():
            raise ValueError(f"{name} has a symlink component: {parent}")
        if parent == parent.parent:
            break
    return path.resolve()


def directory_manifest(path: Path) -> tuple[tuple[str, str, int], ...]:
    root = ensure_directory_no_symlink(path, name="artifact directory")
    rows: list[tuple[str, str, int]] = []
    for candidate in sorted(root.rglob("*")):
        if candidate.is_symlink():
            raise ValueError(f"artifact directory contains symlink: {candidate}")
        if candidate.is_dir():
            continue
        if not candidate.is_file():
            raise ValueError(f"artifact directory contains non-file: {candidate}")
        relative = candidate.relative_to(root).as_posix()
        rows.append(
            (
                relative,
                sha256_file(candidate),
                candidate.stat().st_size,
            )
        )
    if not rows:
        raise ValueError(f"artifact directory is empty: {path}")
    return tuple(rows)


def directory_manifest_sha256(path: Path) -> str:
    return sha256_bytes(
        canonical_json_without_newline(
            [
                {"path": rel, "sha256": digest, "size_bytes": size}
                for rel, digest, size in directory_manifest(path)
            ]
        )
    )


def parse_canonical_json_file(path: Path) -> dict[str, object]:
    source = ensure_regular_no_symlink(path, name="JSON file")
    raw = source.read_bytes()
    value = require_object("JSON file", strict_json_loads(raw))
    if canonical_json_bytes(value) != raw:
        raise ValueError(f"JSON file is not canonical: {path}")
    return value


def write_new_json(path: Path, value: Mapping[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(dict(value))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def write_new_text(path: Path, text: str) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def exact_keyset(
    payload: Mapping[str, object],
    expected: Iterable[str],
    *,
    name: str,
) -> None:
    expected_set = set(expected)
    observed = set(payload)
    if observed != expected_set:
        raise ValueError(
            f"{name} field mismatch: "
            f"missing={sorted(expected_set-observed)}, "
            f"unknown={sorted(observed-expected_set)}"
        )
