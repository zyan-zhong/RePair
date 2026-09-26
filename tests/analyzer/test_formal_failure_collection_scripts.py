from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_formal_collection_scripts_exist():
    assert (
        ROOT / "scripts/analyzer/build_formal_failure_collection_panel_v1.py"
    ).is_file()
    assert (
        ROOT / "scripts/analyzer/run_formal_failure_collection_v1.py"
    ).is_file()


def test_formal_live_runner_reuses_evaluator_not_analyzer_or_memory():
    text = (
        ROOT / "scripts/analyzer/run_formal_failure_collection_v1.py"
    ).read_text(encoding="utf-8")
    assert "run_single_episode" in text
    assert "SpawnedAlfworldAdapter" in text
    assert "MEMORY_OFF_M0" in (
        ROOT / "src/pchsi/analyzer/formal_failure_collection.py"
    ).read_text(encoding="utf-8")
    assert "HIERARCHICAL_ANALYZER" not in text
    assert "ANALYZER_G_" not in text
    assert "memory_pack" not in text.lower()


def test_formal_collection_is_not_benchmark_or_model_selection():
    text = (
        ROOT / "scripts/analyzer/run_formal_failure_collection_v1.py"
    ).read_text(encoding="utf-8")
    assert "BENCHMARK_TABLE_ELIGIBLE=false" in text
    assert "PI1_PERFORMANCE_CLAIM_ELIGIBLE=false" in text
    assert "MODEL_SELECTION_ELIGIBLE=false" in text
