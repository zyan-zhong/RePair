from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT = Path(__file__).parents[2] / "scripts/memory/build_memory_final_live_inputs_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("_fm_final_builder_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_final_cell_identity_is_deterministic_and_round_sensitive() -> None:
    module = _load()
    one = module._cell_id("stage", "group", "condition", 0)
    again = module._cell_id("stage", "group", "condition", 0)
    later = module._cell_id("stage", "group", "condition", 1)
    assert one == again
    assert one != later
    assert len(one) == 64


def test_schedule_binds_exact_cell_order() -> None:
    module = _load()
    rows = [{"cell_id": "a"}, {"cell_id": "b"}]
    value = module._schedule("stage", rows)
    assert value["cell_ids"] == ["a", "b"]
    assert len(value["schedule_sha256"]) == 64
    changed = module._schedule("stage", list(reversed(rows)))
    assert changed["schedule_sha256"] != value["schedule_sha256"]
