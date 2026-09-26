"""Deterministic helpers for Provider-facing Structured Outputs schema compatibility.

This module does not relax the scientific semantic validator. It only permits
representation-level fixes when a Provider HTTP 400 explicitly identifies a
Structured Outputs schema defect.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def classify_http400_adapter_defect(error: Mapping[str, object]) -> dict[str, Any]:
    message = str(error.get("message") or "")
    param = str(error.get("param") or "")
    code = str(error.get("code") or "")
    lowered = (message + " " + param + " " + code).lower()
    schema_signal = (
        "invalid schema" in lowered
        or "invalid_json_schema" in lowered
        or "response_format" in lowered
        or "text.format.schema" in lowered
    )
    return {
        "eligible": schema_signal,
        "repair_class": (
            "STRUCTURED_OUTPUT_SCHEMA_COMPATIBILITY" if schema_signal else None
        ),
    }


def _const_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    raise ValueError(f"unsupported const type: {type(value).__name__}")


def normalize_const_types(
    schema: Mapping[str, object],
) -> tuple[dict[str, Any], int]:
    """Add an explicit JSON type to const-only nodes, preserving all constraints."""
    root = deepcopy(dict(schema))
    changes = 0

    def walk(value: object) -> None:
        nonlocal changes
        if isinstance(value, dict):
            if "const" in value and "type" not in value:
                value["type"] = _const_type(value["const"])
                changes += 1
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(root)
    return root, changes


def audit_structured_output_schema(schema: Mapping[str, object]) -> dict[str, Any]:
    stats = {
        "object_count": 0,
        "property_count": 0,
        "max_nesting_depth": 0,
        "object_missing_additional_properties_false_count": 0,
        "object_required_mismatch_count": 0,
        "const_without_type_count": 0,
        "root_is_object": schema.get("type") == "object",
        "root_anyof_present": "anyOf" in schema,
    }

    def walk(value: object, depth: int) -> None:
        stats["max_nesting_depth"] = max(stats["max_nesting_depth"], depth)
        if isinstance(value, dict):
            if "const" in value and "type" not in value:
                stats["const_without_type_count"] += 1
            if value.get("type") == "object" and isinstance(value.get("properties"), dict):
                stats["object_count"] += 1
                props = value["properties"]
                stats["property_count"] += len(props)
                if value.get("additionalProperties") is not False:
                    stats["object_missing_additional_properties_false_count"] += 1
                required = value.get("required")
                if not isinstance(required, list) or set(required) != set(props):
                    stats["object_required_mismatch_count"] += 1
            for child in value.values():
                walk(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                walk(child, depth + 1)

    walk(dict(schema), 0)
    return stats
