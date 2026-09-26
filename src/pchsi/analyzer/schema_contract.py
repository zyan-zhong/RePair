"""Closed Analyzer JSON-Schema registry and deeply immutable typed loaders."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math
from pathlib import Path
import re
from types import MappingProxyType

from pchsi.reference_loop.canonical import (
    canonical_json_bytes,
    domain_hash,
    ensure_regular_no_symlink,
    strict_json_loads,
)

EXPECTED_ANALYZER_SCHEMAS = MappingProxyType(
    {
        'ANALYZER_ANALYSIS_BUDGET_V2': 'analyzer_analysis_budget_v2.json',
        'ANALYZER_CAPABILITY_PROFILE_V1': 'analyzer_capability_profile_v1.json',
        'ANALYZER_COMPONENT_ATTRIBUTION_V1': 'analyzer_component_attribution_v1.json',
        'ANALYZER_CROSSCHECK_RESULT_V1': 'analyzer_crosscheck_result_v1.json',
        'ANALYZER_ERROR_INSTANCE_MEMBERSHIP_V1': 'analyzer_error_instance_membership_v1.json',
        'ANALYZER_GROUP_MANIFEST_V1': 'analyzer_group_manifest_v1.json',
        'ANALYZER_GROUP_RESULT_V1': 'analyzer_group_result_v1.json',
        'ANALYZER_GROUP_RESULT_V2': 'analyzer_group_result_v2.json',
        'ANALYZER_LOCAL_RESULT_V2': 'analyzer_local_result_v2.json',
        'ANALYZER_MECHANICAL_CENSUS_V1': 'analyzer_mechanical_census_v1.json',
        'ANALYZER_OUTCOME_ROUTE_V1': 'analyzer_outcome_route_v1.json',
        'ANALYZER_POLICY_BEHAVIOR_PROFILE_V1': 'analyzer_policy_behavior_profile_v1.json',
        'ANALYZER_REGRESSION_GUARD_V1': 'analyzer_regression_guard_v1.json',
        'ANALYZER_REPAIR_CANDIDATE_V1': 'analyzer_repair_candidate_v1.json',
        'ANALYZER_SUCCESS_OPTIMIZATION_CANDIDATE_V1': 'analyzer_success_optimization_candidate_v1.json',
        'ANALYZER_SUCCESS_WORKFLOW_REFERENCE_V1': 'analyzer_success_workflow_reference_v1.json',
        'COGNITIVE_ROLE_TRACE_V1': 'cognitive_role_trace_v1.json',
        'REPAIR_EFFECT_DECOMPOSITION_RESULT_V1': 'repair_effect_decomposition_result_v1.json',
        'REPAIR_EFFECT_DECOMPOSITION_TRACE_V1': 'repair_effect_decomposition_trace_v1.json',
        'ANALYZER_GROUP_SYNTHESIS_INPUT_V1': 'analyzer_group_synthesis_input_v1.json',
        'ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1': 'analyzer_source_conditioned_proposal_v1.json'
    }
)

_ALLOWED_KEYWORDS = frozenset({
    "$schema", "$id", "title", "description", "type", "properties", "required",
    "additionalProperties", "items", "minItems", "maxItems", "minLength",
    "maxLength", "pattern", "minimum", "maximum", "enum", "const",
})
_ALLOWED_TYPES = frozenset(
    {"object", "array", "string", "integer", "number", "boolean", "null"}
)


def schema_directory() -> Path:
    path = Path(__file__).resolve().parents[3] / "configs" / "analyzer" / "schemas"
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"Analyzer schema directory is invalid: {path}")
    return path


def _types(node: Mapping[str, object]) -> tuple[str, ...]:
    value = node.get("type")
    if isinstance(value, str):
        out = (value,)
    elif isinstance(value, list) and value and all(isinstance(x, str) for x in value):
        out = tuple(value)
    else:
        raise ValueError("schema type must be text or a non-empty text array")
    if len(set(out)) != len(out) or set(out) - _ALLOWED_TYPES:
        raise ValueError("schema type is invalid")
    return out


def _validate_schema_node(node: object, path: str) -> None:
    if not isinstance(node, dict):
        raise ValueError(f"{path} must be a schema object")
    unknown = set(node) - _ALLOWED_KEYWORDS
    if unknown:
        raise ValueError(f"{path} has unsupported keywords: {sorted(unknown)}")
    types = _types(node) if "type" in node else ()
    if "object" in types and node.get("additionalProperties") is not False:
        raise ValueError(f"{path} object schema must set additionalProperties=false")
    properties = node.get("properties")
    if properties is not None:
        if not isinstance(properties, dict):
            raise ValueError(f"{path}.properties must be object")
        for name, child in properties.items():
            if not isinstance(name, str) or not name:
                raise ValueError(f"{path}.properties has invalid name")
            _validate_schema_node(child, f"{path}.properties[{name!r}]")
    required = node.get("required")
    if required is not None:
        if (
            not isinstance(required, list)
            or any(not isinstance(x, str) or not x for x in required)
            or len(required) != len(set(required))
        ):
            raise ValueError(f"{path}.required must be a unique text array")
        if not isinstance(properties, dict) or set(required) - set(properties):
            raise ValueError(f"{path}.required contains unknown fields")
    if "additionalProperties" in node and node["additionalProperties"] is not False:
        raise ValueError(f"{path}.additionalProperties must be false")
    if "items" in node:
        _validate_schema_node(node["items"], f"{path}.items")
    for key in ("minItems", "maxItems", "minLength", "maxLength"):
        if key in node and (type(node[key]) is not int or node[key] < 0):
            raise ValueError(f"{path}.{key} must be non-negative integer")
    for key in ("minimum", "maximum"):
        if key in node:
            value = node[key]
            if type(value) not in (int, float) or (
                isinstance(value, float) and not math.isfinite(value)
            ):
                raise ValueError(f"{path}.{key} must be finite numeric")
    if "pattern" in node:
        if not isinstance(node["pattern"], str):
            raise ValueError(f"{path}.pattern must be text")
        re.compile(node["pattern"])
    if "enum" in node and (
        not isinstance(node["enum"], list) or not node["enum"]
    ):
        raise ValueError(f"{path}.enum must be non-empty array")


def validate_schema_definition(schema: object) -> None:
    _validate_schema_node(schema, "$")
    if not isinstance(schema, dict):
        raise ValueError("schema must be object")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValueError("top-level Analyzer schema must be a closed object")
    if not isinstance(schema.get("$id"), str) or not schema["$id"]:
        raise ValueError("schema $id must be non-empty")


def _inventory() -> dict[str, Path]:
    root = schema_directory()
    observed = {
        p.name for p in root.glob("*.json")
        if p.is_file() and not p.is_symlink()
    }
    expected = set(EXPECTED_ANALYZER_SCHEMAS.values())
    if observed != expected:
        raise ValueError(
            f"Analyzer schema inventory mismatch: "
            f"missing={sorted(expected-observed)}, unknown={sorted(observed-expected)}"
        )
    result: dict[str, Path] = {}
    for schema_id, filename in EXPECTED_ANALYZER_SCHEMAS.items():
        path = ensure_regular_no_symlink(root / filename, name="Analyzer schema")
        value = strict_json_loads(path.read_bytes())
        if not isinstance(value, dict) or value.get("$id") != schema_id:
            raise ValueError(f"Analyzer schema identity mismatch: {filename}")
        validate_schema_definition(value)
        result[schema_id] = path
    return result


def load_schema(schema_id: str) -> dict[str, object]:
    if not isinstance(schema_id, str) or not schema_id:
        raise ValueError("schema_id must be non-empty")
    try:
        path = _inventory()[schema_id]
    except KeyError as error:
        raise ValueError(f"unknown Analyzer schema: {schema_id}") from error
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("schema must be object")
    return value


def _matches(value: object, expected: str) -> bool:
    return {
        "null": value is None,
        "boolean": type(value) is bool,
        "integer": type(value) is int,
        "number": type(value) in (int, float)
            and not (isinstance(value, float) and not math.isfinite(value)),
        "string": isinstance(value, str),
        "array": isinstance(value, (list, tuple))
            and not isinstance(value, (str, bytes, bytearray)),
        "object": isinstance(value, dict),
    }[expected]


def _validate(value: object, schema: Mapping[str, object], path: str) -> None:
    type_spec = schema.get("type")
    if type_spec is not None:
        expected = (type_spec,) if isinstance(type_spec, str) else tuple(type_spec)
        if not any(_matches(value, str(item)) for item in expected):
            raise ValueError(f"{path} has invalid JSON type")
    if value is None:
        if "const" in schema and value != schema["const"]:
            raise ValueError(f"{path} does not match const")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path} is not in enum")
        return
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path} does not match const")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path} is not in enum")
    if isinstance(value, dict):
        props = schema.get("properties")
        required = schema.get("required", [])
        if not isinstance(props, dict) or not isinstance(required, list):
            raise ValueError(f"{path} has malformed object schema")
        missing = sorted(set(required) - set(value))
        if missing:
            raise ValueError(f"{path} missing required fields: {missing}")
        if schema.get("additionalProperties") is not False:
            raise ValueError(f"{path} object schema is not fail-closed")
        unknown = sorted(set(value) - set(props))
        if unknown:
            raise ValueError(f"{path} contains unknown fields: {unknown}")
        for key, child in value.items():
            child_schema = props[key]
            if not isinstance(child_schema, dict):
                raise ValueError(f"{path}.{key} has malformed child schema")
            _validate(child, child_schema, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValueError(f"{path} shorter than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(f"{path} longer than maxItems")
        item_schema = schema.get("items")
        if not isinstance(item_schema, dict):
            raise ValueError(f"{path} array schema has no closed item schema")
        for index, item in enumerate(value):
            _validate(item, item_schema, f"{path}[{index}]")
    elif isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(f"{path} shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(f"{path} longer than maxLength")
        if isinstance(schema.get("pattern"), str) and re.search(schema["pattern"], value) is None:
            raise ValueError(f"{path} does not match pattern")
    elif type(value) in (int, float):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path} below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{path} above maximum")


def validate_payload_against_schema(*, schema_id: str, payload: object) -> None:
    _validate(payload, load_schema(schema_id), "$")


def verify_domain_hash(
    *,
    payload: Mapping[str, object],
    domain: str,
    hash_field: str,
) -> None:
    declared = payload.get(hash_field)
    if not isinstance(declared, str):
        raise ValueError(f"{hash_field} is missing")
    observed = domain_hash(domain, payload, excluded_field=hash_field)
    if declared != observed:
        raise ValueError(f"{hash_field} mismatch")


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class TypedAnalyzerArtifact:
    schema_id: str
    schema_version: int
    payload: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        value = _thaw(self.payload)
        if not isinstance(value, dict):
            raise AssertionError("typed payload must thaw to object")
        return value


SemanticValidator = Callable[[Mapping[str, object]], None]


def load_typed_artifact(
    path: Path,
    *,
    expected_schema_id: str,
    semantic_validator: SemanticValidator | None = None,
) -> TypedAnalyzerArtifact:
    source = ensure_regular_no_symlink(path, name="Analyzer artifact")
    raw = source.read_bytes()
    payload = strict_json_loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Analyzer artifact must be object")
    if canonical_json_bytes(payload) != raw:
        raise ValueError("Analyzer artifact must be canonical JSON")
    if payload.get("schema_id") != expected_schema_id:
        raise ValueError("Analyzer artifact schema_id mismatch")
    validate_payload_against_schema(
        schema_id=expected_schema_id,
        payload=payload,
    )
    if semantic_validator is not None:
        semantic_validator(payload)
    version = payload.get("schema_version")
    if type(version) is not int:
        raise ValueError("schema_version must be integer")
    return TypedAnalyzerArtifact(
        schema_id=expected_schema_id,
        schema_version=version,
        payload=_freeze(payload),
    )
