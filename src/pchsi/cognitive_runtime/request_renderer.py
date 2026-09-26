from __future__ import annotations
from pathlib import Path
from collections.abc import Mapping
import json, os
from pchsi.reference_loop.canonical import canonical_json_bytes, domain_hash, sha256_file
from .manifest import load_runtime_manifest, stage_spec
from .schema_registry import load_schema
from pchsi.analyzer.component_attribution import load_taxonomy


_LOCAL_STAGES = frozenset({"L-A0", "L-A1"})
_CATALOG_SECTIONS = (
    "trajectory_calls",
    "mechanical_facts",
    "counterexamples",
)
_EVIDENCE_REFERENCE_FIELDS = frozenset(
    {
        "artifact_sha256",
        "evidence_kind",
        "local_selector",
        "authority",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _assert_projection(stage: str, projection: Mapping[str,object]) -> None:
    memory=projection.get("memory_pack_sha256")
    if stage in {"L-A0","L-A1","G-A2"} and memory is not None:
        raise ValueError(f"{stage} must be Memory-blind")
    if stage=="G-A3" and not isinstance(memory,str):
        raise ValueError("G-A3 requires one frozen Memory pack")
    if stage in {"G-A2","G-A3"}:
        identities = projection.get("a1_local_result_sha256s")
        local_results = projection.get("a1_local_results")

        def valid_sha(value: object) -> bool:
            return (
                isinstance(value, str)
                and len(value) == 64
                and all(
                    character in "0123456789abcdef"
                    for character in value
                )
            )

        if (
            not isinstance(identities, list)
            or not identities
            or any(
                not valid_sha(value)
                for value in identities
            )
        ):
            raise ValueError(
                f"{stage} requires non-empty plural A1 local-result identity"
            )

        if identities != sorted(set(identities)):
            raise ValueError(
                f"{stage} A1 local-result identities must be sorted unique"
            )

        if (
            not isinstance(local_results, list)
            or len(local_results) != len(identities)
        ):
            raise ValueError(
                f"{stage} A1 local-result bytes/count mismatch"
            )

        observed = []

        for row in local_results:
            if not isinstance(row, Mapping):
                raise ValueError(
                    f"{stage} A1 local-result bytes must be objects"
                )

            identity = row.get("local_result_sha256")

            if not valid_sha(identity):
                raise ValueError(
                    f"{stage} A1 local-result object lacks valid identity"
                )

            observed.append(identity)

        if observed != identities:
            raise ValueError(
                f"{stage} A1 bytes identity mismatch"
            )


def _local_selector_allowlist(
    projection: Mapping[str, object],
) -> tuple[str, ...]:
    catalog = projection.get("evidence_reference_catalog")
    if not isinstance(catalog, Mapping):
        raise ValueError("local evidence reference catalog must be one object")

    selectors: set[str] = set()

    for section in _CATALOG_SECTIONS:
        rows = catalog.get(section)
        if not isinstance(rows, list):
            raise ValueError(
                f"local evidence reference catalog section must be array: {section}"
            )

        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError(
                    f"local evidence reference catalog row must be object: {section}"
                )

            selector = row.get("local_selector")
            if (
                not isinstance(selector, str)
                or not selector
                or len(selector) > 512
            ):
                raise ValueError(
                    "local evidence reference selector must be non-empty text "
                    "with length <= 512"
                )

            selectors.add(selector)

    if not selectors:
        raise ValueError("local evidence reference selector allowlist is empty")

    return tuple(sorted(selectors))


def _specialize_local_selector_enums(
    schema: Mapping[str, object],
    selectors: tuple[str, ...],
) -> dict[str, object]:
    match_count = 0

    def walk(value: object) -> object:
        nonlocal match_count

        if isinstance(value, Mapping):
            copied = {
                str(key): walk(child)
                for key, child in value.items()
            }

            properties = copied.get("properties")
            required = copied.get("required")

            if (
                isinstance(properties, dict)
                and isinstance(required, list)
                and _EVIDENCE_REFERENCE_FIELDS.issubset(
                    {
                        str(field)
                        for field in required
                    }
                )
            ):
                local_selector = properties.get("local_selector")

                if not isinstance(local_selector, dict):
                    raise ValueError(
                        "evidence reference local_selector schema must be object"
                    )

                specialized = dict(local_selector)
                specialized["enum"] = list(selectors)
                properties["local_selector"] = specialized
                match_count += 1

            return copied

        if isinstance(value, list):
            return [
                walk(child)
                for child in value
            ]

        return value

    specialized = walk(schema)

    if not isinstance(specialized, dict):
        raise ValueError("provider output schema must remain one object")

    if match_count == 0:
        raise ValueError(
            "local output schema contains no evidence-reference selector fields"
        )

    return specialized


def _specialize_component_taxonomy_enums(
    schema: Mapping[str, object],
) -> dict[str, object]:
    taxonomy = tuple(load_taxonomy())
    if not taxonomy or len(taxonomy) != len(set(taxonomy)):
        raise ValueError("C capability taxonomy must be non-empty and unique")

    def copy_json(value: object) -> object:
        if isinstance(value, Mapping):
            return {
                str(key): copy_json(child)
                for key, child in value.items()
            }
        if isinstance(value, list):
            return [copy_json(child) for child in value]
        return value

    copied = copy_json(schema)
    if not isinstance(copied, dict):
        raise ValueError("C output schema must remain one object")

    properties = copied.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("C output schema properties must be one object")

    principal = properties.get("principal_component")
    secondary = properties.get("secondary_components")
    if not isinstance(principal, dict):
        raise ValueError("C principal_component schema must be one object")
    if not isinstance(secondary, dict):
        raise ValueError("C secondary_components schema must be one object")
    items = secondary.get("items")
    if not isinstance(items, dict):
        raise ValueError("C secondary_components.items must be one object")

    principal_specialized = dict(principal)
    principal_specialized["enum"] = list(taxonomy)
    items_specialized = dict(items)
    items_specialized["enum"] = list(taxonomy)

    properties["principal_component"] = principal_specialized
    secondary_specialized = dict(secondary)
    secondary_specialized["items"] = items_specialized
    properties["secondary_components"] = secondary_specialized

    return copied


def render_stage_request(*, stage_id: str, projection: Mapping[str,object]) -> dict[str,object]:
    manifest=load_runtime_manifest(); spec=stage_spec(stage_id,manifest)
    if spec["role"]=="DETERMINISTIC":
        raise ValueError("deterministic P stage has no model request")
    _assert_projection(stage_id,projection)
    root=_repo_root()
    missing=[x for x in spec.get("required_projection_identity_fields",[]) if x not in projection]
    if missing:
        raise ValueError(f"input projection missing frozen identity fields: {missing}")
    prompt_path=root/spec["prompt_relative_path"]
    if sha256_file(prompt_path)!=spec["prompt_sha256"]:
        raise ValueError("prompt SHA mismatch")
    prompt=prompt_path.read_text(encoding="utf-8")
    schema_id=spec["output_schema_id"]
    if spec["output_schema_relative_path"] is not None:
        schema_path=root/spec["output_schema_relative_path"]
        if sha256_file(schema_path)!=spec["output_schema_sha256"]:
            raise ValueError("output schema SHA mismatch")
        schema=json.loads(schema_path.read_text(encoding="utf-8"))
    else:
        schema=load_schema(schema_id) if schema_id else None

    if stage_id in _LOCAL_STAGES:
        if not isinstance(schema, Mapping):
            raise ValueError("local Analyzer output schema must be one object")
        selectors = _local_selector_allowlist(projection)
        schema = _specialize_local_selector_enums(schema, selectors)

    if stage_id == "C":
        if not isinstance(schema, Mapping):
            raise ValueError("C Analyzer output schema must be one object")
        schema = _specialize_component_taxonomy_enums(schema)

    if "OPENAI_API_KEY" in json.dumps(projection,sort_keys=True):
        raise ValueError("secret marker leaked into projection")
    request={
        "model":manifest["requested_model"],
        "input":[
            {"role":"system","content":[{"type":"input_text","text":prompt}]},
            {"role":"user","content":[{"type":"input_text","text":
                canonical_json_bytes(dict(projection)).decode("utf-8")}]},
        ],
        "reasoning":{"effort":manifest["reasoning"]["effort"]},
        "tools":[],"store":False,"truncation":"disabled",
        "max_output_tokens":spec["max_output_tokens"],
        "text":{"format":{"type":"json_schema","name":schema_id.lower(),
                             "strict":True,"schema":schema}},
    }
    request_sha=domain_hash("COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1",request)
    return {"stage_id":stage_id,"stage_spec":spec,"input_projection":dict(projection),
            "input_projection_sha256":domain_hash("COGNITIVE_INPUT_PROJECTION_V1",projection),
            "provider_request":request,"request_body_sha256":request_sha,
            "runtime_manifest_sha256":manifest["runtime_manifest_sha256"]}
