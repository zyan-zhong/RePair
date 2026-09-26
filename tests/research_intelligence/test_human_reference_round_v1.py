from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.human_reference_round import (
    build_f0f1_handoff,
    build_pre_shadow_projection,
)


def test_pre_shadow_projection_contains_no_human_pre_identity():
    round_evidence = {
        "schema_id": "ROUND_EVIDENCE_PACKAGE_V1",
        "x": 1,
    }
    memory_pack = {
        "schema_id": "RESEARCHER_MEMORY_PACK_V1",
        "records": ["historical-research-evidence"],
    }
    round_sha = domain_hash(
        "ROUND_EVIDENCE_PACKAGE_V1",
        round_evidence,
    )
    memory_file_sha = "a" * 64

    projection = build_pre_shadow_projection(
        round_evidence=round_evidence,
        memory_pack=memory_pack,
        expected_round_evidence_package_sha256=round_sha,
        expected_memory_pack_file_sha256=memory_file_sha,
        observed_memory_pack_file_sha256=memory_file_sha,
    )

    assert set(projection) == {
        "round_evidence_package_sha256",
        "round_evidence_package",
        "researcher_memory_pack_file_sha256",
        "researcher_memory_pack",
    }
    assert projection["round_evidence_package"] == round_evidence
    assert projection["researcher_memory_pack"] == memory_pack
    assert "human_pre" not in str(projection).lower()


def test_materializer_source_has_no_benchmark_skeleton():
    from pathlib import Path

    text = Path(
        "scripts/research_intelligence/"
        "materialize_human_reference_round_inputs_v4.py"
    ).read_text(encoding="utf-8")

    assert "BENCHMARK_LINEAGE_CANDIDATE" not in text
    assert "benchmark_artifact_count" in text
    assert '"benchmark_artifact_count": 0' in text
    assert '"benchmark_results_visible": False' in text
