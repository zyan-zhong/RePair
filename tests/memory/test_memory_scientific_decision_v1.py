from __future__ import annotations

import copy

import pytest

from pchsi.memory.scientific_decision import (
    FM0, FM1, FM2, FM3, ROUND_ACTIVE,
    STAGE_1B, STAGE_2,
    recompute_stage_decisions_v1,
    validate_cell_result_v1,
)
import importlib.util
import sys
from pathlib import Path

_HELPER_PATH = Path(__file__).with_name("scientific_authority_test_helpers.py")
_SPEC = importlib.util.spec_from_file_location("_memory_science_test_helpers", _HELPER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_HELPERS = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _HELPERS
_SPEC.loader.exec_module(_HELPERS)
cell_identity_rows = _HELPERS.cell_identity_rows
make_cell_result = _HELPERS.make_cell_result
rule = _HELPERS.rule
dsha = _HELPERS.dsha


def _rows(stage: str, manifest_sha: str = "a" * 64):
    return [
        make_cell_result(identity, stage=stage, manifest_sha=manifest_sha)
        for identity in cell_identity_rows(stage)
    ]


def test_stage1b_decisions_are_recomputed_from_mechanical_cells():
    result = recompute_stage_decisions_v1(
        stage=STAGE_1B,
        cell_results=_rows(STAGE_1B),
        decision_rule=rule(STAGE_1B),
        execution_manifest_sha256="a" * 64,
    )
    assert result["question_decisions"]["Q1"]["disposition"] == "SUPPORTED"
    assert result["question_decisions"]["Q2"]["disposition"] == "NOT_SUPPORTED"
    assert result["question_decisions"]["Q3"]["disposition"] == "SUPPORTED"
    assert result["effect_estimates"]["q1_pair"]["benefit_count"] == 1


def test_zero_coverage_is_inconclusive_not_safe_utility():
    rows = _rows(STAGE_1B)
    fm3 = next(row for row in rows if row["condition"] == FM3)
    fm3.update({
        "memory_exposed": False,
        "correct_memory_exposure": False,
        "abstained": True,
    })
    fm3["cell_result_sha256"] = "0" * 64
    fm3["cell_result_sha256"] = dsha(
        "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1", fm3, "cell_result_sha256"
    )
    result = recompute_stage_decisions_v1(
        stage=STAGE_1B,
        cell_results=rows,
        decision_rule=rule(STAGE_1B),
        execution_manifest_sha256="a" * 64,
    )
    assert result["question_decisions"]["Q3"]["disposition"] == "INCONCLUSIVE"
    assert result["effect_estimates"]["q3_safety_utility"]["coverage_count"] == 0


def test_cell_executor_cannot_smuggle_question_dispositions():
    row = _rows(STAGE_1B)[0]
    row["registered_question_decisions"] = {"Q1": {"disposition": "SUPPORTED"}}
    with pytest.raises(ValueError, match="fields mismatch"):
        validate_cell_result_v1(
            row,
            expected_stage=STAGE_1B,
            expected_execution_manifest_sha256="a" * 64,
        )


def test_stage2_requires_round_zero_and_multiple_rounds():
    rows = _rows(STAGE_2)
    result = recompute_stage_decisions_v1(
        stage=STAGE_2,
        cell_results=rows,
        decision_rule=rule(STAGE_2),
        execution_manifest_sha256="a" * 64,
    )
    assert result["question_decisions"]["Q1"]["disposition"] == "SUPPORTED"
    broken = [copy.deepcopy(rows[1])]
    with pytest.raises(ValueError, match="round population"):
        recompute_stage_decisions_v1(
            stage=STAGE_2,
            cell_results=broken,
            decision_rule=rule(STAGE_2),
            execution_manifest_sha256="a" * 64,
        )


def _rehash_cell(row: dict) -> None:
    row["cell_result_sha256"] = "0" * 64
    row["cell_result_sha256"] = dsha(
        "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",
        row,
        "cell_result_sha256",
    )


def test_stage1b_rejects_duplicate_registered_arm():
    rows = _rows(STAGE_1B)
    duplicate = copy.deepcopy(next(row for row in rows if row["condition"] == FM3))
    duplicate["cell_id"] = "g1-FM3-duplicate"
    _rehash_cell(duplicate)
    with pytest.raises(ValueError, match="registered comparison arm repeats"):
        recompute_stage_decisions_v1(
            stage=STAGE_1B,
            cell_results=[*rows, duplicate],
            decision_rule=rule(STAGE_1B),
            execution_manifest_sha256="a" * 64,
        )


def test_stage2_rejects_noncontiguous_rounds():
    rows = _rows(STAGE_2)
    rows[1]["round_index"] = 2
    _rehash_cell(rows[1])
    with pytest.raises(ValueError, match="contiguous from round zero"):
        recompute_stage_decisions_v1(
            stage=STAGE_2,
            cell_results=rows,
            decision_rule=rule(STAGE_2),
            execution_manifest_sha256="a" * 64,
        )


def test_stage2_rejects_duplicate_group_round():
    rows = _rows(STAGE_2)
    duplicate = copy.deepcopy(rows[1])
    duplicate["cell_id"] = "r1-g1-duplicate"
    _rehash_cell(duplicate)
    with pytest.raises(ValueError, match="comparison group repeats within round 1"):
        recompute_stage_decisions_v1(
            stage=STAGE_2,
            cell_results=[*rows, duplicate],
            decision_rule=rule(STAGE_2),
            execution_manifest_sha256="a" * 64,
        )


def test_stage2_rejects_missing_group_round():
    rows = _rows(STAGE_2)
    extra_round0 = copy.deepcopy(rows[0])
    extra_round0.update({
        "cell_id": "r0-g2",
        "comparison_group_id": "g2",
        "task_id": "task-g2",
    })
    _rehash_cell(extra_round0)
    with pytest.raises(ValueError, match="comparison-group population differs in round 1"):
        recompute_stage_decisions_v1(
            stage=STAGE_2,
            cell_results=[*rows, extra_round0],
            decision_rule=rule(STAGE_2),
            execution_manifest_sha256="a" * 64,
        )
