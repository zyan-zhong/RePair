"""Minimal closed-schema validation for cognitive-runtime artifacts."""
from __future__ import annotations
from collections.abc import Mapping
import math, re


def _match(value, typ):
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": type(value) is int,
        "number": type(value) in (int,float) and not (
            isinstance(value,float) and not math.isfinite(value)
        ),
        "boolean": type(value) is bool,
        "null": value is None,
    }[typ]


def validate(value: object, schema: Mapping[str,object], path: str = "$") -> None:
    types=schema.get("type")
    if types is not None:
        options=(types,) if isinstance(types,str) else tuple(types)
        if not any(_match(value,t) for t in options):
            raise ValueError(f"{path} has invalid type")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path} does not match const")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path} is not in enum")
    if value is None:
        return
    if isinstance(value,dict):
        props=schema.get("properties")
        if not isinstance(props,dict) or schema.get("additionalProperties") is not False:
            raise ValueError(f"{path} object schema is not closed")
        required=schema.get("required",[])
        missing=set(required)-set(value)
        unknown=set(value)-set(props)
        if missing or unknown:
            raise ValueError(f"{path} fields missing={sorted(missing)} unknown={sorted(unknown)}")
        for key,child in value.items():
            validate(child,props[key],f"{path}.{key}")
    elif isinstance(value,list):
        if len(value)<schema.get("minItems",0):
            raise ValueError(f"{path} shorter than minItems")
        if "maxItems" in schema and len(value)>schema["maxItems"]:
            raise ValueError(f"{path} longer than maxItems")
        item=schema.get("items")
        if not isinstance(item,dict):
            raise ValueError(f"{path} array lacks item schema")
        for index,child in enumerate(value):
            validate(child,item,f"{path}[{index}]")
    elif isinstance(value,str):
        if len(value)<schema.get("minLength",0):
            raise ValueError(f"{path} shorter than minLength")
        if "maxLength" in schema and len(value)>schema["maxLength"]:
            raise ValueError(f"{path} longer than maxLength")
        if "pattern" in schema and re.fullmatch(schema["pattern"],value) is None:
            raise ValueError(f"{path} does not match pattern")
    elif type(value) in (int,float):
        if "minimum" in schema and value<schema["minimum"]:
            raise ValueError(f"{path} below minimum")
        if "maximum" in schema and value>schema["maximum"]:
            raise ValueError(f"{path} above maximum")
