from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from common import finalize


def test_census_contract_is_read_only():
    contract = json.loads(
        (ROOT / "contracts" / "FROZEN_RENDERER_INTERFACE_CENSUS_CONTRACT_V1.json")
        .read_text(encoding="utf-8")
    )
    assert contract["source_materializer_execution_allowed"] is False
    assert contract["model_execution_allowed"] is False
    assert contract["environment_execution_allowed"] is False
    assert contract["trainer_execution_allowed"] is False
    assert contract["adapter_implementation_allowed_in_this_package"] is False


def test_census_uses_ast_not_exec():
    text = (TOOLS / "census_frozen_q2_renderer_interface.py").read_text(
        encoding="utf-8"
    )
    assert "ast.parse" in text
    assert "exec(" not in text
    assert "subprocess" not in text
    assert "importlib" not in text


def test_bridge_has_norm_continuity_and_fresh_answer_reset():
    text = (
        TOOLS / "freeze_reference_takeover_normative_bridge.py"
    ).read_text(encoding="utf-8")
    assert (
        "INHERIT_NORMS_AND_TEACHER_TRACES_RESET_FRESH_ROUND_ANSWERS"
        in text
    )
    assert "strong_research_planner_primary" in text
    assert "routine_strong_calls_zero" in text
    assert "human_reference_same_round_answers_binding" in text


def test_no_training_execution_surface_in_production_tools():
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(TOOLS.glob("*.py"))
    ).lower()
    for token in (
        "env.step(",
        "trainer.train(",
        "model.generate(",
        "openai",
        "vllm",
        "sbatch",
        "srun ",
    ):
        assert token not in text


def test_finalize_is_deterministic():
    a = finalize("X", "sha", {"schema_id": "X", "x": 1})
    b = finalize("X", "sha", {"x": 1, "schema_id": "X"})
    assert a == b
