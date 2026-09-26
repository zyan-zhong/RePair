from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from pchsi.reference_loop.canonical import canonical_json_bytes, domain_hash


def load_object(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"regular JSON file required: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"one JSON object required: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_value(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def write_json_new(path: Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def finalize_hash(
    *,
    domain: str,
    field: str,
    value: Mapping[str, object],
) -> dict[str, object]:
    out = dict(value)
    out[field] = "0" * 64
    out[field] = domain_hash(domain, out, excluded_field=field)
    return out


def recursive_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(recursive_keys(child))
    return keys
