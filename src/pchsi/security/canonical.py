"""Strict canonical JSON helpers for S1 security artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Final


__all__ = [
    "CanonicalJsonError",
    "canonical_json_bytes",
    "sha256_hex",
    "strict_json_loadb",
    "strict_json_loads",
]


_MAX_DEPTH: Final[int] = 64
_INT64_MIN: Final[int] = -(2**63)
_INT64_MAX: Final[int] = 2**63 - 1


class CanonicalJsonError(ValueError):
    """Raised when input violates the frozen canonical JSON contract."""


class _DuplicateMemberError(CanonicalJsonError):
    """Raised when a JSON object repeats a member name."""


def _reject_duplicate_members(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}

    for key, value in pairs:
        if key in result:
            raise _DuplicateMemberError(
                f"duplicate JSON member: {key!r}"
            )

        result[key] = value

    return result


def _parse_int64(token: str) -> int:
    if token == "-0":
        raise CanonicalJsonError(
            "negative zero is not allowed"
        )

    value = int(token, 10)

    if value < _INT64_MIN or value > _INT64_MAX:
        raise CanonicalJsonError(
            "JSON integer is outside signed 64-bit range"
        )

    return value


def _reject_real(token: str) -> object:
    raise CanonicalJsonError(
        f"JSON real numbers are not allowed: {token}"
    )


def _reject_constant(token: str) -> object:
    raise CanonicalJsonError(
        f"non-standard JSON constant is not allowed: {token}"
    )


_DECODER: Final[json.JSONDecoder] = json.JSONDecoder(
    object_pairs_hook=_reject_duplicate_members,
    parse_int=_parse_int64,
    parse_float=_reject_real,
    parse_constant=_reject_constant,
    strict=True,
)


def _validate_depth(
    value: object,
    *,
    depth: int = 0,
) -> None:
    if isinstance(value, dict):
        next_depth = depth + 1

        if next_depth > _MAX_DEPTH:
            raise CanonicalJsonError(
                "maximum JSON nesting depth exceeded"
            )

        for key, child in value.items():
            if not isinstance(key, str):
                raise CanonicalJsonError(
                    "JSON object keys must be strings"
                )

            _validate_depth(
                child,
                depth=next_depth,
            )
        return

    if isinstance(value, (list, tuple)):
        next_depth = depth + 1

        if next_depth > _MAX_DEPTH:
            raise CanonicalJsonError(
                "maximum JSON nesting depth exceeded"
            )

        for child in value:
            _validate_depth(
                child,
                depth=next_depth,
            )
        return

    if value is None or isinstance(value, bool):
        return

    if isinstance(value, str):
        if any(
            0xD800 <= ord(character) <= 0xDFFF
            for character in value
        ):
            raise CanonicalJsonError(
                "JSON strings must contain Unicode scalar values"
            )
        return

    if isinstance(value, int) and not isinstance(value, bool):
        if value < _INT64_MIN or value > _INT64_MAX:
            raise CanonicalJsonError(
                "JSON integer is outside signed 64-bit range"
            )
        return

    raise CanonicalJsonError(
        f"unsupported canonical JSON value: {type(value).__name__}"
    )


def strict_json_loadb(data: bytes) -> object:
    """Parse exactly one strict UTF-8 JSON value."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    try:
        text = data.decode(
            "utf-8",
            errors="strict",
        )
    except UnicodeDecodeError as error:
        raise CanonicalJsonError(
            "input is not valid UTF-8"
        ) from error

    source = text.strip(" \t\r\n")

    try:
        value, end = _DECODER.raw_decode(source)
    except (
        CanonicalJsonError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, CanonicalJsonError):
            raise

        raise CanonicalJsonError(
            "invalid JSON syntax"
        ) from error

    if end != len(source):
        raise CanonicalJsonError(
            "trailing data after JSON value"
        )

    _validate_depth(value)
    return value


def strict_json_loads(text: str) -> object:
    """Parse exactly one strict JSON value from a Python string."""

    if not isinstance(text, str):
        raise TypeError("text must be str")

    return strict_json_loadb(
        text.encode("utf-8")
    )


def canonical_json_bytes(value: object) -> bytes:
    """Serialize one value to frozen canonical UTF-8 JSON bytes."""

    _validate_depth(value)

    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise CanonicalJsonError(
            "value cannot be represented as canonical JSON"
        ) from error

    return encoded.encode("utf-8") + b"\n"


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of bytes."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    return hashlib.sha256(data).hexdigest()
