from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

from pchsi.memory.scientific_decision import FM0, FM1, FM2, FM3


SCRIPT = (
    Path(__file__).parents[2]
    / "scripts/memory/run_memory_live_cell_executor_v1.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "_fm_stage1b_translation_test_target",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _manifest():
    cells = []
    for source in ("a" * 64, "b" * 64):
        for arm_id in ("M0", "M1", "M2", "M3"):
            cells.append(
                {
                    "source_state_id": source,
                    "arm": {
                        "arm_id": arm_id,
                        "representation_class": (
                            "M0"
                            if arm_id == "M0"
                            else "FM1"
                            if arm_id == "M1"
                            else "SINGLE_CUE"
                            if arm_id == "M2"
                            else "FM2"
                        ),
                    },
                }
            )
    return {"cells": cells}


def test_stage1b_formal_a_mapping_uses_nested_arm_schema() -> None:
    module = _load()
    manifest = _manifest()
    source = "a" * 64

    assert module._stage1b_a0_cell_index_v1(
        a0_manifest=manifest,
        source_state_id=source,
        condition=FM0,
    ) == 0
    assert module._stage1b_a0_cell_index_v1(
        a0_manifest=manifest,
        source_state_id=source,
        condition=FM1,
    ) == 1
    assert module._stage1b_a0_cell_index_v1(
        a0_manifest=manifest,
        source_state_id=source,
        condition=FM2,
    ) == 3


def test_stage1b_fm3_is_not_aliased_to_formal_a() -> None:
    module = _load()

    assert module._stage1b_route_v1(FM0) == "FORMAL_A"
    assert module._stage1b_route_v1(FM1) == "FORMAL_A"
    assert module._stage1b_route_v1(FM2) == "FORMAL_A"
    assert module._stage1b_route_v1(FM3) == "LIVE_SOURCE_STATE_FM3"

    with pytest.raises(
        SystemExit,
        match="STAGE1B_FM3_HAS_NO_FORMAL_A_ALIAS",
    ):
        module._stage1b_a0_cell_index_v1(
            a0_manifest=_manifest(),
            source_state_id="a" * 64,
            condition=FM3,
        )


def test_stage1b_live_fm3_uses_registered_source_state() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "def _stage1b_live_fm3_v1(" in source
    assert "replay_source_decision_state_hold_open_v1" in source
    assert "RegisteredReplaySourceV1.from_json" in source
    assert "ProjectionClassV1.FM3" in source
    assert '"DIRECT_FIXED_RECORD_NO_RETRIEVAL"' in source
    assert "source.budget_state" in source
    assert "source.model_call_index" in source
    assert "source.interface_feedback_code" in source


def test_stage1b_translation_never_reads_top_level_arm_id() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'cell["arm_id"] == desired_arm' not in source
    assert 'arm.get("arm_id") == desired_arm' in source
