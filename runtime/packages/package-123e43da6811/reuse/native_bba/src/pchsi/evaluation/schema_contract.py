"""Closed, standard-library-only JSON Schema subset for E1 artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from pathlib import Path
import re
from typing import Any, ClassVar, Protocol

from .canonical_evidence import strict_json_loads


class StrictSchemaModel(Protocol):
    SCHEMA_ID: ClassVar[str]
    SCHEMA_VERSION: ClassVar[int]

    def to_dict(self) -> dict[str, object]:
        ...


_ALLOWED_KEYWORDS = frozenset(
    {
        "$schema",
        "$id",
        "title",
        "description",
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "pattern",
        "minimum",
        "maximum",
        "enum",
        "const",
    }
)

_ALLOWED_TYPES = frozenset(
    {
        "object",
        "array",
        "string",
        "integer",
        "number",
        "boolean",
        "null",
    }
)


def schema_directory() -> Path:
    """Return the repository's evaluator schema directory."""

    root = Path(__file__).resolve().parents[3]
    path = root / "configs" / "evaluation" / "schemas"
    if not path.is_dir():
        raise ValueError(
            f"evaluator schema directory does not exist: {path}"
        )
    return path


def _schema_inventory() -> dict[str, Path]:
    inventory: dict[str, Path] = {}
    for path in sorted(schema_directory().glob("*.json")):
        if path.is_symlink():
            raise ValueError(
                f"schema file must not be a symlink: {path}"
            )
        payload = strict_json_loads(path.read_bytes())
        if not isinstance(payload, dict):
            raise ValueError(
                f"schema must be a JSON object: {path}"
            )
        schema_id = payload.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ValueError(
                f"schema $id must be non-empty: {path}"
            )
        if schema_id in inventory:
            raise ValueError(
                f"duplicate schema $id: {schema_id}"
            )
        inventory[schema_id] = path
    return inventory


def load_schema(schema_id: str) -> dict[str, object]:
    if not isinstance(schema_id, str) or not schema_id:
        raise ValueError("schema_id must be a non-empty string")

    inventory = _schema_inventory()
    try:
        path = inventory[schema_id]
    except KeyError as error:
        raise ValueError(
            f"unknown evaluator schema: {schema_id}"
        ) from error

    payload = strict_json_loads(path.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError("schema must be a JSON object")
    validate_schema_definition(payload)
    return payload


def _validate_type_keyword(value: object, path: str) -> None:
    if isinstance(value, str):
        values = (value,)
    elif (
        isinstance(value, list)
        and value
        and all(isinstance(item, str) for item in value)
    ):
        values = tuple(value)
    else:
        raise ValueError(
            f"{path}.type must be a string or non-empty string list"
        )

    if len(set(values)) != len(values):
        raise ValueError(f"{path}.type contains duplicates")

    unsupported = set(values) - _ALLOWED_TYPES
    if unsupported:
        raise ValueError(
            f"{path}.type contains unsupported values: "
            f"{sorted(unsupported)}"
        )


def _validate_schema_node(node: object, path: str) -> None:
    if not isinstance(node, dict):
        raise ValueError(f"{path} must be a schema object")

    unsupported = set(node) - _ALLOWED_KEYWORDS
    if unsupported:
        raise ValueError(
            f"{path} contains unsupported schema keywords: "
            f"{sorted(unsupported)}"
        )

    if "type" in node:
        _validate_type_keyword(node["type"], path)

    if "properties" in node:
        properties = node["properties"]
        if not isinstance(properties, dict):
            raise ValueError(
                f"{path}.properties must be an object"
            )
        for key, child in properties.items():
            if not isinstance(key, str) or not key:
                raise ValueError(
                    f"{path}.properties keys must be non-empty strings"
                )
            _validate_schema_node(
                child,
                f"{path}.properties[{key!r}]",
            )

    if "required" in node:
        required = node["required"]
        if (
            not isinstance(required, list)
            or any(
                not isinstance(item, str) or not item
                for item in required
            )
        ):
            raise ValueError(
                f"{path}.required must be a string list"
            )
        if len(set(required)) != len(required):
            raise ValueError(
                f"{path}.required contains duplicates"
            )
        properties = node.get("properties", {})
        if not isinstance(properties, dict):
            raise ValueError(
                f"{path}.properties must exist with required"
            )
        missing = set(required) - set(properties)
        if missing:
            raise ValueError(
                f"{path}.required references unknown properties: "
                f"{sorted(missing)}"
            )

    if "additionalProperties" in node:
        if node["additionalProperties"] is not False:
            raise ValueError(
                f"{path}.additionalProperties must be false"
            )

    if "items" in node:
        _validate_schema_node(
            node["items"],
            f"{path}.items",
        )

    for keyword in (
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
    ):
        if keyword in node:
            value = node[keyword]
            if type(value) is not int or value < 0:
                raise ValueError(
                    f"{path}.{keyword} must be a non-negative integer"
                )

    for keyword in ("minimum", "maximum"):
        if keyword in node:
            value = node[keyword]
            if (
                type(value) not in (int, float)
                or (
                    isinstance(value, float)
                    and not math.isfinite(value)
                )
            ):
                raise ValueError(
                    f"{path}.{keyword} must be finite numeric"
                )

    if "pattern" in node:
        pattern = node["pattern"]
        if not isinstance(pattern, str):
            raise ValueError(
                f"{path}.pattern must be a string"
            )
        try:
            re.compile(pattern)
        except re.error as error:
            raise ValueError(
                f"{path}.pattern is invalid"
            ) from error

    if "enum" in node:
        enum = node["enum"]
        if not isinstance(enum, list) or not enum:
            raise ValueError(
                f"{path}.enum must be a non-empty array"
            )

    if (
        "minItems" in node
        and "maxItems" in node
        and node["minItems"] > node["maxItems"]
    ):
        raise ValueError(
            f"{path}.minItems exceeds maxItems"
        )

    if (
        "minLength" in node
        and "maxLength" in node
        and node["minLength"] > node["maxLength"]
    ):
        raise ValueError(
            f"{path}.minLength exceeds maxLength"
        )


def validate_schema_definition(schema: object) -> None:
    """Validate the frozen standard-library schema subset."""

    _validate_schema_node(schema, "$")

    if not isinstance(schema, dict):
        raise ValueError("schema must be an object")

    schema_id = schema.get("$id")
    if not isinstance(schema_id, str) or not schema_id:
        raise ValueError("schema $id must be non-empty")

    if schema.get("type") != "object":
        raise ValueError("top-level schema type must be object")

    if schema.get("additionalProperties") is not False:
        raise ValueError(
            "top-level additionalProperties must be false"
        )


def _matches_type(value: object, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return type(value) is bool
    if expected == "integer":
        return type(value) is int
    if expected == "number":
        return type(value) in (int, float) and not (
            isinstance(value, float)
            and not math.isfinite(value)
        )
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return (
            isinstance(value, (list, tuple))
            and not isinstance(value, (str, bytes, bytearray))
        )
    if expected == "object":
        return isinstance(value, dict)
    raise AssertionError(f"unsupported type: {expected}")


def _validate_payload_node(
    value: object,
    schema: Mapping[str, object],
    path: str,
) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} must be finite")

    type_spec = schema.get("type")
    if type_spec is not None:
        expected_types = (
            (type_spec,)
            if isinstance(type_spec, str)
            else tuple(type_spec)
        )
        if not any(
            _matches_type(value, expected)
            for expected in expected_types
        ):
            joined = " or ".join(expected_types)
            raise ValueError(
                f"{path} must have JSON type {joined}"
            )

    if value is None:
        return

    if "const" in schema and value != schema["const"]:
        raise ValueError(
            f"{path} must equal const {schema['const']!r}"
        )

    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(
            f"{path} must be one of {schema['enum']!r}"
        )

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}

        required = schema.get("required", [])
        if not isinstance(required, list):
            required = []

        missing = [
            name for name in required
            if name not in value
        ]
        if missing:
            raise ValueError(
                f"{path} is missing required fields: {missing}"
            )

        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise ValueError(
                    f"{path} contains unknown fields: {unknown}"
                )

        for name, child in value.items():
            if name in properties:
                child_schema = properties[name]
                if not isinstance(child_schema, dict):
                    raise ValueError(
                        f"invalid schema for {path}.{name}"
                    )
                _validate_payload_node(
                    child,
                    child_schema,
                    f"{path}.{name}",
                )

    if isinstance(value, (list, tuple)):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValueError(
                f"{path} has fewer than minItems"
            )
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(
                f"{path} has more than maxItems"
            )

        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_payload_node(
                    item,
                    item_schema,
                    f"{path}[{index}]",
                )

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(
                f"{path} is shorter than minLength"
            )
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(
                f"{path} is longer than maxLength"
            )
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            raise ValueError(
                f"{path} does not match required pattern"
            )

    if type(value) in (int, float):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(
                f"{path} is smaller than minimum"
            )
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(
                f"{path} is larger than maximum"
            )


def validate_payload_against_schema(
    *,
    schema_id: str,
    payload: object,
) -> None:
    schema = load_schema(schema_id)
    _validate_payload_node(payload, schema, "$")


def validate_model_against_schema(
    model: StrictSchemaModel,
) -> None:
    schema_id = getattr(model, "SCHEMA_ID", None)
    schema_version = getattr(model, "SCHEMA_VERSION", None)

    if not isinstance(schema_id, str) or not schema_id:
        raise TypeError("model must define SCHEMA_ID")
    if type(schema_version) is not int:
        raise TypeError("model must define integer SCHEMA_VERSION")

    payload = model.to_dict()
    if payload.get("schema_id") != schema_id:
        raise ValueError(
            "model schema_id field does not match SCHEMA_ID"
        )
    if payload.get("schema_version") != schema_version:
        raise ValueError(
            "model schema_version field does not match SCHEMA_VERSION"
        )

    validate_payload_against_schema(
        schema_id=schema_id,
        payload=payload,
    )
