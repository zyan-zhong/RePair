from __future__ import annotations
import hashlib
import json
from pathlib import Path


def canonical_json_without_newline(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def domain_hash(
    domain: str,
    payload,
    *,
    excluded_field: str | None = None,
) -> str:
    body = dict(payload)
    if excluded_field is not None:
        body.pop(excluded_field, None)
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\0"
        + canonical_json_without_newline(body)
    ).hexdigest()


def require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text")
    return value


def require_sha256(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256")
    return value


def require_nonnegative_int(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def require_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")
    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def directory_manifest_sha256(path: Path) -> str:
    rows = []
    for candidate in sorted(path.rglob("*")):
        if candidate.is_file():
            rows.append({
                "path": candidate.relative_to(path).as_posix(),
                "sha256": sha256_file(candidate),
                "size_bytes": candidate.stat().st_size,
            })
    if not rows:
        raise ValueError("artifact directory is empty")
    return hashlib.sha256(
        canonical_json_without_newline(rows)
    ).hexdigest()
