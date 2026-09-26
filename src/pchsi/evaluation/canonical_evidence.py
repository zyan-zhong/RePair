"""Canonical evidence primitives for E1 evaluator artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def canonical_json_bytes(value: object) -> bytes:
    """Serialize one JSON value as deterministic UTF-8 plus one LF."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def canonical_json_text(value: object) -> str:
    """Return canonical JSON as text, including its terminal LF."""

    return canonical_json_bytes(value).decode("utf-8")


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(
                f"duplicate JSON object key: {key!r}"
            )
        result[key] = value
    return result


def _reject_nonstandard_constant(token: str) -> object:
    raise ValueError(
        f"non-standard JSON numeric constant: {token}"
    )


def strict_json_loads(data: str | bytes) -> object:
    """Parse strict UTF-8 JSON, rejecting duplicate keys and NaN tokens."""

    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ValueError("JSON bytes must be valid UTF-8") from error
    elif isinstance(data, str):
        text = data
    else:
        raise TypeError("data must be str or bytes")

    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonstandard_constant,
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid JSON: {error.msg}"
        ) from error


def sha256_bytes(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    path = Path(path)
    if path.is_symlink():
        raise ValueError("path must not be a symlink")
    if not path.is_file():
        raise ValueError("path must identify a regular file")

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)
    return digest.hexdigest()


def require_lower_sha256(name: str, value: object) -> str:
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string")
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if (
        len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
    ):
        raise ValueError(
            f"{name} must be a 64-character lowercase SHA-256"
        )
    return value


def require_nonnegative_int(name: str, value: object) -> int:
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string")
    if type(value) is not int:
        raise TypeError(f"{name} must be int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def require_finite_number(
    name: str,
    value: object,
) -> int | float:
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string")
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be int or float")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value
