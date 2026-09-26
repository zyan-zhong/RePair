from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pchsi.reference_loop.canonical import (
    domain_hash,
    require_bool,
    require_nonnegative_int,
    require_sha256,
    require_text,
)


def require_choice(name: str, value: str, allowed: set[str]) -> str:
    require_text(name, value)
    if value not in allowed:
        raise ValueError(f"{name} has unsupported value: {value}")
    return value


def hashed_payload(
    *,
    domain: str,
    hash_field: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    value = dict(payload)
    value[hash_field] = "0" * 64
    value[hash_field] = domain_hash(
        domain,
        value,
        excluded_field=hash_field,
    )
    return value


__all__ = [
    "domain_hash",
    "hashed_payload",
    "require_bool",
    "require_choice",
    "require_nonnegative_int",
    "require_sha256",
    "require_text",
]
