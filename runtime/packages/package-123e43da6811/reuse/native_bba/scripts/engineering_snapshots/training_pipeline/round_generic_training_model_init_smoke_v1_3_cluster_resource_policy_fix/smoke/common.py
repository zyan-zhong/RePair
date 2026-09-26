from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class SmokeError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def domain_sha256(
    schema_id: str,
    value: dict[str, Any],
    *,
    sha_field: str,
) -> str:
    payload = {
        key: child
        for key, child in value.items()
        if key != sha_field
    }
    return hashlib.sha256(
        schema_id.encode("utf-8")
        + b"\0"
        + canonical_json_bytes(payload)
    ).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SmokeError(f"JSON_FILE_MISSING:{path}") from exc
    except json.JSONDecodeError as exc:
        raise SmokeError(f"JSON_PARSE_FAILED:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise SmokeError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def require_sha(path: Path, expected: str, label: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64:
        raise SmokeError(f"{label}_EXPECTED_SHA_INVALID")
    if not path.is_file() or path.is_symlink():
        raise SmokeError(f"{label}_FILE_INVALID:{path}")
    observed = sha256_file(path)
    if observed != expected:
        raise SmokeError(
            f"{label}_SHA_MISMATCH:{observed}:{expected}"
        )


def require_domain_sha(
    value: dict[str, Any],
    *,
    schema_id: str,
    sha_field: str,
) -> None:
    if value.get("schema_id") != schema_id:
        raise SmokeError(
            f"SCHEMA_ID_MISMATCH:{value.get('schema_id')}:{schema_id}"
        )
    expected = value.get(sha_field)
    if not isinstance(expected, str) or len(expected) != 64:
        raise SmokeError(f"{sha_field}_INVALID")
    observed = domain_sha256(
        schema_id,
        value,
        sha_field=sha_field,
    )
    if observed != expected:
        raise SmokeError(
            f"{sha_field}_MISMATCH:{observed}:{expected}"
        )


def write_json_create_once(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SmokeError(f"OUTPUT_ALREADY_EXISTS:{path}")
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
