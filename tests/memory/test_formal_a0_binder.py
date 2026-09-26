from __future__ import annotations

from pathlib import Path


def test_formal_a_binder_freezes_exact_scientific_inputs():
    source = Path(
        "scripts/memory/bind_formal_a0_inputs_v1.py"
    ).read_text(encoding="utf-8")
    assert "P4-R1-Q2-BAD-TRAIN17" in source
    assert (
        "8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189"
        in source
    )
    assert (
        "613166c9f092795cb03c892ee0046f0af5bf7fc13ba44f7fccb950027c329262"
        in source
    )
    assert "exactly three replay cases" in source
    assert "source-to-governed-record match count must be one" in source
    assert '"scientific_execution_authorized": False' in source


def test_discovery_is_offline_and_content_unique():
    source = Path(
        "scripts/memory/discover_formal_a0_inputs_v1.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "SpawnedAlfworldAdapter",
        "PolicyClient",
        "sbatch",
    ):
        assert forbidden not in source
    assert "_unique_content" in source
    assert "NO_FORMAL_A_REPLAY_MANIFEST_FOUND" in source
