from __future__ import annotations
from pathlib import Path
from pchsi.reference_loop.canonical import strict_json_loads
from .validation import validate


def schema_root() -> Path:
    return Path(__file__).resolve().parents[3]/"configs/cognitive_runtime/schemas"


def load_schema(schema_id: str) -> dict[str,object]:
    path=schema_root()/(schema_id.lower()+".json")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"unknown cognitive-runtime schema: {schema_id}")
    value=strict_json_loads(path.read_bytes())
    if not isinstance(value,dict) or value.get("$id")!=schema_id:
        raise ValueError("schema identity mismatch")
    return value


def validate_artifact(schema_id: str, value: object) -> None:
    validate(value,load_schema(schema_id))
