from __future__ import annotations

import pytest

from pchsi.cognitive_runtime.output_validation import validated_artifact_identity
from pchsi.reference_loop.canonical import domain_hash


def finalized(schema_id: str, version: int, field: str, **extra):
    value = {
        "schema_id": schema_id,
        "schema_version": version,
        **extra,
        field: "0" * 64,
    }
    value[field] = domain_hash(schema_id, value, excluded_field=field)
    return value


@pytest.mark.parametrize(
    "stage,schema,version,field",
    [
        ("L-A0", "ANALYZER_LOCAL_RESULT_V2", 2, "local_result_sha256"),
        ("L-A1", "ANALYZER_LOCAL_RESULT_V2", 2, "local_result_sha256"),
        ("G-A2", "ANALYZER_GROUP_RESULT_V2", 2, "group_result_sha256"),
        ("G-A3", "ANALYZER_GROUP_RESULT_V2", 2, "group_result_sha256"),
        ("C", "ANALYZER_COMPONENT_ATTRIBUTION_V1", 1, "attribution_sha256"),
        ("X", "ANALYZER_CROSSCHECK_RESULT_V1", 1, "crosscheck_sha256"),
        ("R-PRE-SHADOW", "API_RESEARCHER_PRE_SHADOW_V1", 1, "shadow_record_sha256"),
        ("R-POST-SHADOW", "API_RESEARCHER_POST_SHADOW_V1", 1, "shadow_record_sha256"),
        (
            "R-PRE-SHADOW-HYDRATED-V2",
            "STRONG_RESEARCHER_PRE_SHADOW_V2",
            2,
            "shadow_record_sha256",
        ),
    ],
)
def test_registered_self_hash_identity(stage, schema, version, field):
    artifact = finalized(schema, version, field)
    assert validated_artifact_identity(stage_id=stage, artifact=artifact) == artifact[field]


def test_input_sha_preceding_output_sha_is_not_misidentified():
    artifact = finalized(
        "API_RESEARCHER_POST_SHADOW_V1",
        1,
        "shadow_record_sha256",
        environment_result_package_sha256="a" * 64,
        human_pre_record_sha256="b" * 64,
    )
    assert validated_artifact_identity(
        stage_id="R-POST-SHADOW",
        artifact=artifact,
    ) == artifact["shadow_record_sha256"]


def test_identity_rejects_self_hash_mismatch():
    artifact = finalized(
        "ANALYZER_COMPONENT_ATTRIBUTION_V1",
        1,
        "attribution_sha256",
    )
    artifact["attribution_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="self-hash mismatch"):
        validated_artifact_identity(stage_id="C", artifact=artifact)


def test_identity_rejects_unknown_stage():
    with pytest.raises(ValueError, match="unsupported"):
        validated_artifact_identity(stage_id="UNKNOWN", artifact={})
