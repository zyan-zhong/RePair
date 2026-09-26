from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from pchsi.memory.scientific_decision import STAGE_1B
from pchsi.memory.scientific_program import (
    MemoryRepresentationArmV1,
    MemoryScientificProgramV1,
    MemoryScientificStageV1,
    MemoryStageCellV1,
    ScientificQuestionStatusV1,
    build_current_q1_q5_matrix_v1,
)

_HELPER_PATH = Path(__file__).with_name("scientific_authority_test_helpers.py")
_SPEC = importlib.util.spec_from_file_location("_memory_science_program_helpers", _HELPER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_HELPERS = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _HELPERS
_SPEC.loader.exec_module(_HELPERS)
build_authority = _HELPERS.build_authority


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def _a0() -> dict:
    return {
        "schema_id": "FORMAL_A0_RESULT_AUTHORITY_V1",
        "schema_version": 1,
        "authority": "LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY",
        "effect_counts": {"Benefit": 0, "Harm": 0, "Neutral": 9},
        "general_representation_claim_authorized": False,
    }


def _b() -> dict:
    return {
        "schema_id": "FORMAL_B_MINIMAL_Q3_RESULT_AUTHORITY_V1",
        "schema_version": 1,
        "result_authority_sha256": "ba2290e90631b8836ea93106fd1630237c7b45470bc465c1000e7fb18647fb7b",
        "registered_safety_stress_metrics": {
            "coverage": {"denominator": 30, "numerator": 0},
            "unsafe_memory_exposure_rate": {"denominator": 30, "numerator": 0},
        },
    }


def _baseline(tmp_path: Path):
    a0 = tmp_path / "a0.json"
    b = tmp_path / "b.json"
    _write(a0, _a0())
    _write(b, _b())
    return a0, b


def _cell(stage, cell_id, **overrides):
    values = {
        "stage": stage,
        "cell_id": cell_id,
        "panel_sha256": "1" * 64,
        "policy_identity_sha256": "2" * 64,
        "environment_identity_sha256": "3" * 64,
        "snapshot_sha256": None,
        "representation_arm": None,
        "round_index": None,
        "split": "TRAIN_RETRIEVAL_DEV",
        "method_frozen": False,
    }
    values.update(overrides)
    return MemoryStageCellV1(**values)


def test_current_matrix_preserves_known_null_and_zero_coverage(tmp_path):
    a0, b = _baseline(tmp_path)
    matrix = build_current_q1_q5_matrix_v1(a0_result_path=a0, b_result_path=b)
    assert tuple(row.status for row in matrix.rows) == (
        ScientificQuestionStatusV1.OPEN,
        ScientificQuestionStatusV1.PARTIAL_LOCAL_NULL,
        ScientificQuestionStatusV1.MIXED_POLICY_DIRECT,
        ScientificQuestionStatusV1.OPEN,
        ScientificQuestionStatusV1.DEFERRED_OPTIONAL_EXTENSION,
    )


def test_minimal_summary_cannot_upgrade_q1_q3(tmp_path):
    a0, b = _baseline(tmp_path)
    summary = tmp_path / "summary.json"
    _write(summary, {"schema_id": "STAGE_1B_FROZEN_POLICY_FM0_FM3_RESULT_V1", "fm1_minus_fm0_task_success": {"numerator": 1}})
    with pytest.raises(ValueError):
        build_current_q1_q5_matrix_v1(
            a0_result_path=a0,
            b_result_path=b,
            stage1b_result_path=summary,
            expected_fixed_code_head="f" * 40,
            expected_scientific_program_sha256="1" * 64,
        )


def test_artifact_backed_stage1b_authority_updates_only_registered_questions(tmp_path):
    a0, b = _baseline(tmp_path)
    authority, meta = build_authority(tmp_path / "authority", stage=STAGE_1B)
    matrix = build_current_q1_q5_matrix_v1(
        a0_result_path=a0,
        b_result_path=b,
        stage1b_result_path=authority,
        expected_fixed_code_head=meta["fixed_head"],
        expected_scientific_program_sha256=meta["program_sha"],
    )
    statuses = {row.question_id: row.status for row in matrix.rows}
    assert statuses["Q1"] is ScientificQuestionStatusV1.SUPPORTED
    assert statuses["Q2"] is ScientificQuestionStatusV1.NOT_SUPPORTED
    assert statuses["Q3"] is ScientificQuestionStatusV1.SUPPORTED
    assert statuses["Q4"] is ScientificQuestionStatusV1.OPEN
    assert statuses["Q5"] is ScientificQuestionStatusV1.DEFERRED_OPTIONAL_EXTENSION


def test_live_authority_requires_expected_head_and_program(tmp_path):
    a0, b = _baseline(tmp_path)
    authority, _ = build_authority(tmp_path / "authority")
    with pytest.raises(ValueError, match="require the expected fixed code head"):
        build_current_q1_q5_matrix_v1(
            a0_result_path=a0,
            b_result_path=b,
            stage1b_result_path=authority,
        )


def test_memory_closure_may_not_accept_formal_c_or_offoff_without_external_validators(tmp_path):
    a0, b = _baseline(tmp_path)
    external = tmp_path / "external.json"
    _write(external, {"schema_id": "FORGED"})
    with pytest.raises(ValueError, match="Formal-C requires"):
        build_current_q1_q5_matrix_v1(
            a0_result_path=a0,
            b_result_path=b,
            formal_c_result_path=external,
        )
    with pytest.raises(ValueError, match="OFF/OFF requires"):
        build_current_q1_q5_matrix_v1(
            a0_result_path=a0,
            b_result_path=b,
            off_off_result_path=external,
        )


def test_program_scope_retains_external_analyzer_and_training_boundaries():
    cells = (
        _cell(MemoryScientificStageV1.STAGE_0_MEMORY_DIAGNOSTICS, "s0"),
        _cell(MemoryScientificStageV1.STAGE_1A_LOCAL_PAIRED, "s1a"),
        _cell(
            MemoryScientificStageV1.STAGE_1B_FROZEN_POLICY_FM0_FM3,
            "s1b", snapshot_sha256="4" * 64,
            representation_arm=MemoryRepresentationArmV1.FM0_NO_MEMORY,
        ),
        _cell(
            MemoryScientificStageV1.STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY,
            "s2", snapshot_sha256="4" * 64, round_index=0,
        ),
        _cell(
            MemoryScientificStageV1.STAGE_3_FROZEN_FORMAL_EVALUATION,
            "s3", snapshot_sha256="4" * 64,
            representation_arm=MemoryRepresentationArmV1.FM0_NO_MEMORY,
            split="VALID_SEEN", method_frozen=True,
        ),
    )
    program = MemoryScientificProgramV1(
        canonical_base_head="a" * 40,
        cells=cells,
        stage_metrics={stage.value: ("task_success",) for stage in MemoryScientificStageV1},
    )
    assert program.q4_external_analyzer_required is True
    assert program.q5_parametric_internalization_deferred is True
    assert program.scientific_execution_authorized is False
