from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class AuditError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditError(f"JSON_FILE_MISSING:{path}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"JSON_PARSE_FAILED:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def require_file_sha(
    path: Path,
    expected: str,
    label: str,
) -> None:
    if not path.is_file() or path.is_symlink():
        raise AuditError(f"{label}_FILE_INVALID:{path}")
    observed = sha256_file(path)
    if observed != expected:
        raise AuditError(
            f"{label}_SHA_MISMATCH:{observed}:{expected}"
        )


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


def write_json_create_once(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise AuditError(f"OUTPUT_ALREADY_EXISTS:{path}")
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
