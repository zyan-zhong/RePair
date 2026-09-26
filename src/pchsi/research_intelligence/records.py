from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pchsi.cognitive_runtime.researcher import (
    finalize_field_adjudication,
    finalize_human_pre,
)
from pchsi.cognitive_runtime.schema_registry import validate_artifact

from .common import finalize_hash, write_json_new


def freeze_human_pre(value: Mapping[str, object], output: Path) -> dict[str, object]:
    out = finalize_human_pre(value)
    write_json_new(output, out)
    return out


def finalize_human_post(value: Mapping[str, object]) -> dict[str, object]:
    out = {
        "schema_id": "HUMAN_RESEARCHER_POST_V1",
        "schema_version": 1,
        **dict(value),
        "post_record_sha256": "0" * 64,
    }
    out = finalize_hash(
        domain="HUMAN_RESEARCHER_POST_V1",
        field="post_record_sha256",
        value=out,
    )
    validate_artifact("HUMAN_RESEARCHER_POST_V1", out)
    return out


def freeze_human_post(value: Mapping[str, object], output: Path) -> dict[str, object]:
    out = finalize_human_post(value)
    write_json_new(output, out)
    return out


def freeze_field_adjudication(
    value: Mapping[str, object],
    output: Path,
) -> dict[str, object]:
    out = finalize_field_adjudication(value)
    write_json_new(output, out)
    return out
