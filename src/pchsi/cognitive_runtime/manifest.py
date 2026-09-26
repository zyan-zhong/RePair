from __future__ import annotations
from pathlib import Path
from pchsi.reference_loop.canonical import domain_hash, strict_json_loads


def manifest_path() -> Path:
    return Path(__file__).resolve().parents[3]/"configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json"


def load_runtime_manifest(path: Path|None=None) -> dict[str,object]:
    source=manifest_path() if path is None else path
    value=strict_json_loads(source.read_bytes())
    if not isinstance(value,dict):
        raise ValueError("runtime manifest must be object")
    observed=domain_hash(
        "UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1",value,
        excluded_field="runtime_manifest_sha256",
    )
    if value.get("runtime_manifest_sha256")!=observed:
        raise ValueError("runtime manifest SHA mismatch")
    if value.get("sdk_automatic_retries")!=0:
        raise ValueError("SDK automatic retries must be disabled")
    if value.get("ambiguous_post_send_automatic_retry") is not False:
        raise ValueError("ambiguous post-send automatic retry is forbidden")
    rows=value.get("stage_rows")
    if not isinstance(rows,list) or len({x["stage_id"] for x in rows})!=len(rows):
        raise ValueError("runtime stage rows invalid")
    return value


def stage_spec(stage_id: str, manifest: dict[str,object]|None=None) -> dict[str,object]:
    value=load_runtime_manifest() if manifest is None else manifest
    rows=[x for x in value["stage_rows"] if x["stage_id"]==stage_id]
    if len(rows)!=1:
        raise ValueError(f"unknown stage: {stage_id}")
    return dict(rows[0])
