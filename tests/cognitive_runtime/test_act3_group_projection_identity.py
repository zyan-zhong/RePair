import pytest

from pchsi.cognitive_runtime.request_renderer import (
    render_stage_request,
)


def _group_projection(memory):
    sha = "b" * 64
    return {
        "group_id": "1" * 64,
        "group_manifest_sha256": "a" * 64,
        "current_evidence_sha256s": [
            "1" * 64,
            "a" * 64,
            sha,
        ],
        "a1_local_result_sha256s": [sha],
        "a1_local_results": [
            {
                "local_result_sha256": sha,
            }
        ],
        "group_synthesis_input": {},
        "source_contexts": [],
        "memory_pack_sha256": memory,
    }


def test_g_a2_accepts_v4_group_identity_and_evidence_contract():
    rendered = render_stage_request(
        stage_id="G-A2",
        projection=_group_projection(None),
    )
    assert (
        rendered["stage_spec"]["prompt_template_id"]
        == "ANALYZER_G_A2_PROMPT_V4"
    )


def test_g_a3_accepts_v4_group_identity_and_evidence_contract():
    rendered = render_stage_request(
        stage_id="G-A3",
        projection=_group_projection("c" * 64),
    )
    assert (
        rendered["stage_spec"]["prompt_template_id"]
        == "ANALYZER_G_A3_PROMPT_V4"
    )


def test_g_stage_rejects_legacy_singular_only_identity():
    projection = _group_projection(None)
    projection.pop("a1_local_result_sha256s")
    projection.pop("a1_local_results")
    projection["a1_local_result_sha256"] = "b" * 64

    with pytest.raises(
        ValueError,
        match="plural A1 local-result identity",
    ):
        render_stage_request(
            stage_id="G-A2",
            projection=projection,
        )


def test_g_stage_rejects_empty_plural_identity():
    projection = _group_projection(None)
    projection["a1_local_result_sha256s"] = []
    projection["a1_local_results"] = []

    with pytest.raises(
        ValueError,
        match="plural A1 local-result identity",
    ):
        render_stage_request(
            stage_id="G-A2",
            projection=projection,
        )


def test_g_stage_rejects_duplicate_a1_sha_identity():
    projection = _group_projection(None)
    sha = "b" * 64
    projection["a1_local_result_sha256s"] = [
        sha,
        sha,
    ]
    projection["a1_local_results"] = [
        {"local_result_sha256": sha},
        {"local_result_sha256": sha},
    ]

    with pytest.raises(
        ValueError,
        match="sorted unique",
    ):
        render_stage_request(
            stage_id="G-A2",
            projection=projection,
        )


def test_g_stage_rejects_a1_bytes_identity_mismatch():
    projection = _group_projection(None)
    projection["a1_local_results"] = [
        {
            "local_result_sha256":
                "d" * 64,
        }
    ]

    with pytest.raises(
        ValueError,
        match="A1 bytes identity mismatch",
    ):
        render_stage_request(
            stage_id="G-A2",
            projection=projection,
        )
