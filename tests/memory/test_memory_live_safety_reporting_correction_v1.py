from __future__ import annotations

import csv
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.memory.scientific_decision import (
    FM0,
    FM3,
    STAGE_1B,
    STAGE_2,
    STAGE_3,
    recompute_stage_decisions_v1,
)


_HELPER_PATH = Path(__file__).with_name("scientific_authority_test_helpers.py")
_SPEC = importlib.util.spec_from_file_location(
    "_fm_final_safety_reporting_helpers",
    _HELPER_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
_HELPERS = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _HELPERS
_SPEC.loader.exec_module(_HELPERS)

cell_identity_rows = _HELPERS.cell_identity_rows
make_cell_result = _HELPERS.make_cell_result
rule = _HELPERS.rule
dsha = _HELPERS.dsha
build_authority = _HELPERS.build_authority

SCRIPTS = Path(__file__).parents[2] / "scripts" / "memory"


def _rows(stage: str, manifest_sha: str = "a" * 64):
    return [
        make_cell_result(identity, stage=stage, manifest_sha=manifest_sha)
        for identity in cell_identity_rows(stage)
    ]


def _rehash(row: dict[str, object]) -> None:
    row["cell_result_sha256"] = "0" * 64
    row["cell_result_sha256"] = dsha(
        "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",
        row,
        "cell_result_sha256",
    )


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def test_stage3_unknown_exposure_labels_are_not_zero_evidence() -> None:
    rows = _rows(STAGE_3)
    result = recompute_stage_decisions_v1(
        stage=STAGE_3,
        cell_results=rows,
        decision_rule=rule(STAGE_3, "VALID_UNSEEN"),
        execution_manifest_sha256="a" * 64,
    )
    safety = result["effect_estimates"]["q3_safety_utility"]
    assert (
        safety["exposure_label_authority"]
        == "NOT_EVALUATED_NO_REGISTERED_GOLD_V1"
    )
    assert safety["correct_exposure_count"] is None
    assert safety["wrong_exposure_count"] is None
    assert safety["unsafe_exposure_count"] is None
    assert safety["harm_authority"] == "PAIRED_TASK_SUCCESS_V1"
    assert result["question_decisions"]["Q3"]["disposition"] == "INCONCLUSIVE"


def test_stage3_harm_is_recomputed_from_fm0_fm3_task_success() -> None:
    rows = _rows(STAGE_3)
    fm0 = next(row for row in rows if row["condition"] == FM0)
    fm3 = next(row for row in rows if row["condition"] == FM3)
    fm0["success"] = True
    fm3["success"] = False
    fm3["harm_observed"] = False
    _rehash(fm0)
    _rehash(fm3)

    result = recompute_stage_decisions_v1(
        stage=STAGE_3,
        cell_results=rows,
        decision_rule=rule(STAGE_3, "VALID_UNSEEN"),
        execution_manifest_sha256="a" * 64,
    )
    safety = result["effect_estimates"]["q3_safety_utility"]
    assert safety["harm_count"] == 1
    assert safety["harm_authority"] == "PAIRED_TASK_SUCCESS_V1"
    assert result["question_decisions"]["Q3"]["disposition"] == "NOT_SUPPORTED"


def test_stage2_per_round_harm_is_paired_against_round_zero() -> None:
    rows = _rows(STAGE_2)
    rows[0]["success"] = True
    rows[1]["success"] = False
    rows[1]["harm_observed"] = False
    _rehash(rows[0])
    _rehash(rows[1])

    result = recompute_stage_decisions_v1(
        stage=STAGE_2,
        cell_results=rows,
        decision_rule=rule(STAGE_2),
        execution_manifest_sha256="a" * 64,
    )
    round1 = result["effect_estimates"]["per_round"]["1"]
    assert round1["harm_count"] == 1
    assert round1["harm_authority"] == "PAIRED_TASK_SUCCESS_V1"
    assert (
        round1["exposure_label_authority"]
        == "NOT_EVALUATED_NO_REGISTERED_GOLD_V1"
    )
    assert round1["correct_exposure_count"] is None
    assert round1["wrong_memory_count"] is None
    assert round1["unsafe_memory_count"] is None


def test_paper_export_does_not_render_unknown_stage3_exposure_as_zero(
    tmp_path: Path,
) -> None:
    authorities: dict[str, Path] = {}
    meta = None
    for stage, name in (
        (STAGE_1B, "stage1b"),
        (STAGE_2, "stage2"),
        (STAGE_3, "stage3"),
    ):
        authority, current = build_authority(tmp_path / name, stage=stage)
        authorities[name] = authority
        if meta is None:
            meta = current
        else:
            assert current == meta
    assert meta is not None

    stage0 = tmp_path / "stage0.json"
    _write_json(
        stage0,
        {
            "schema_id": "FAILURE_MEMORY_STAGE0_ROLE_RETRIEVAL_RESULT_V1",
            "schema_version": 1,
            "row_count": 90,
            "policy_exposure_count": 0,
            "analyzer_reference_positive_count": 5,
            "analyzer_recall_at_3": {"numerator": 5, "denominator": 5},
            "researcher_train_record_count": 3,
        },
    )
    a0 = tmp_path / "a0.json"
    _write_json(
        a0,
        {
            "schema_id": "FORMAL_A0_RESULT_AUTHORITY_V1",
            "authority": "LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY",
            "effect_counts": {"Benefit": 0, "Harm": 0, "Neutral": 9},
        },
    )
    b = tmp_path / "b.json"
    _write_json(
        b,
        {
            "schema_id": "FORMAL_B_MINIMAL_Q3_RESULT_AUTHORITY_V1",
            "authority": "FORMAL_B_Q3_RETRIEVAL_APPLICABILITY_SAFETY_ONLY",
            "registered_safety_stress_metrics": {
                "row_count": 30,
                "coverage": {"numerator": 0, "denominator": 30},
                "correct_exposure_count": 0,
                "wrong_exposure_count": 0,
                "unsafe_exposure_count": 0,
                "abstention_count": 30,
            },
        },
    )
    matrix = tmp_path / "matrix.json"
    statuses = {
        "Q1": "SUPPORTED",
        "Q2": "NOT_SUPPORTED",
        "Q3": "SUPPORTED",
        "Q4": "OPEN",
        "Q5": "DEFERRED_OPTIONAL_EXTENSION",
    }
    matrix_value = {
        "schema_id": "FAILURE_MEMORY_Q1_Q5_MATRIX_V1",
        "schema_version": 1,
        "rows": [
            {
                "question_id": question,
                "status": status,
                "authorized_summary": "bounded summary",
                "evidence_sha256s": [],
                "forbidden_claims": [],
                "required_next_authorities": [],
            }
            for question, status in statuses.items()
        ],
        "scientific_completion_rule": (
            "TESTS_AND_INTERFACE_SMOKES_NEVER_REPLACE_REAL_OUTCOMES"
        ),
        "matrix_sha256": "0" * 64,
    }
    payload = {
        "rows": matrix_value["rows"],
        "scientific_completion_rule": matrix_value[
            "scientific_completion_rule"
        ],
    }
    matrix_value["matrix_sha256"] = hashlib.sha256(
        b"FAILURE_MEMORY_Q1_Q5_MATRIX_V1\0" + canonical_json_bytes(payload)
    ).hexdigest()
    _write_json(matrix, matrix_value)

    paper = tmp_path / "paper"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "export_memory_paper_evidence_v2.py"),
            "--stage0-result", str(stage0),
            "--a0-result", str(a0),
            "--b-result", str(b),
            "--stage1b-authority", str(authorities["stage1b"]),
            "--stage2-authority", str(authorities["stage2"]),
            "--stage3-authority", str(authorities["stage3"]),
            "--q1-q5-matrix", str(matrix),
            "--expected-fixed-head", meta["fixed_head"],
            "--expected-scientific-program-sha256", meta["program_sha"],
            "--output-dir", str(paper),
        ],
        check=True,
    )

    with (
        paper / "paper_tables" / "retrieval_applicability_safety.csv"
    ).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    stage3 = next(row for row in rows if row["source"] == "STAGE3")
    stage1b = next(row for row in rows if row["source"] == "STAGE1B")

    assert (
        stage3["exposure_label_authority"]
        == "NOT_EVALUATED_NO_REGISTERED_GOLD_V1"
    )
    assert stage3["correct_exposure_count"] == ""
    assert stage3["wrong_exposure_count"] == ""
    assert stage3["unsafe_exposure_count"] == ""
    assert stage3["harm_authority"] == "PAIRED_TASK_SUCCESS_V1"
    assert (
        stage1b["exposure_label_authority"]
        == "REGISTERED_DIRECT_GOLD_V1"
    )
