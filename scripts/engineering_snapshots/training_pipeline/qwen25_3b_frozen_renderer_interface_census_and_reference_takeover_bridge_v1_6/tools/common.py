from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ContractError(RuntimeError):
    pass


def reject_duplicate_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"DUPLICATE_JSON_KEY:{key}")
        out[key] = value
    return out


def load_json_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"REGULAR_FILE_REQUIRED:{path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_pairs,
        )
    except Exception as exc:
        raise ContractError(
            f"JSON_LOAD_FAILED:{path}:{type(exc).__name__}"
        ) from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"REGULAR_FILE_REQUIRED:{path}")
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(
                    line,
                    object_pairs_hook=reject_duplicate_pairs,
                )
            except Exception as exc:
                raise ContractError(
                    f"JSONL_LOAD_FAILED:{path}:{line_no}:{type(exc).__name__}"
                ) from exc
            if not isinstance(value, dict):
                raise ContractError(
                    f"JSONL_OBJECT_REQUIRED:{path}:{line_no}"
                )
            rows.append(value)
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def domain_hash(schema_id: str, payload: dict[str, Any]) -> str:
    body = canonical_json_bytes(payload)
    return hashlib.sha256(
        schema_id.encode("utf-8") + b"\0" + body
    ).hexdigest()


def finalize(
    schema_id: str,
    hash_field: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload)
    out[hash_field] = domain_hash(schema_id, payload)
    return out


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ContractError(f"NO_CLOBBER:{path}")
    path.write_bytes(canonical_json_bytes(value))


def write_new_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ContractError(f"NO_CLOBBER:{path}")
    path.write_text(text, encoding="utf-8")
