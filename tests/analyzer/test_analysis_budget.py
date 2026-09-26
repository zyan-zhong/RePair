from __future__ import annotations
import importlib
from pathlib import Path
import pytest
from pchsi.reference_loop.canonical import domain_hash


def _m():
    return importlib.import_module("pchsi.analyzer.analysis_sampling")


def _census(*, success=6, failure=4, families=("f1","f2")):
    rows = []
    per = max(1, failure // len(families))
    for fam in families:
        rows.append({
            "task_family": fam,
            "registered_count": per,
            "scientific_count": per,
            "success_count": 0,
            "failure_count": per,
            "protocol_invalid_primary_count": 0,
            "evidence_incomplete_primary_count": 0,
            "infrastructure_unavailable_primary_count": 0,
        })
    rows.append({
        "task_family": "success-family",
        "registered_count": success,
        "scientific_count": success,
        "success_count": success,
        "failure_count": 0,
        "protocol_invalid_primary_count": 0,
        "evidence_incomplete_primary_count": 0,
        "infrastructure_unavailable_primary_count": 0,
    })
    value = {
        "schema_id": "ANALYZER_MECHANICAL_CENSUS_V1",
        "schema_version": 1,
        "registered_unit_count": sum(x["registered_count"] for x in rows),
        "scientific_outcome_count": sum(x["scientific_count"] for x in rows),
        "registered_route_sha256s": [
            f"{i:064x}" for i in range(sum(x["registered_count"] for x in rows))
        ],
        "status_counts": {
            "SCIENTIFIC_OUTCOME_AVAILABLE": sum(x["scientific_count"] for x in rows),
            "PROTOCOL_INVALID": 0,
            "EVIDENCE_INCOMPLETE": 0,
            "INFRASTRUCTURE_UNAVAILABLE": 0,
        },
        "outcome_counts": {
            "SUCCESS": success,
            "FAILURE": sum(x["failure_count"] for x in rows),
        },
        "incident_counts": {
            "protocol_invalid": 0,
            "evidence_incomplete": 0,
            "infrastructure_unavailable": 0,
        },
        "reason_census": [],
        "task_family_rows": rows,
        "missingness_preserved": True,
        "census_sha256": "0"*64,
    }
    value["census_sha256"] = domain_hash(
        "ANALYZER_MECHANICAL_CENSUS_V1",
        value,
        excluded_field="census_sha256",
    )
    return value


def _units(m, failure_families=("f1","f2"), success=10):
    rows = [
        m.AnalysisUnit(
            unit_id=f"fail-{i}", task_id=f"t-{i}", gamefile_sha256=f"{i+1:064x}",
            task_family=fam, outcome=m.TrajectoryOutcome.FAILURE, frozen_order=i,
        )
        for i, fam in enumerate(failure_families)
    ]
    rows += [
        m.AnalysisUnit(
            unit_id=f"success-{i}", task_id=f"s-{i}", gamefile_sha256=f"{i+100:064x}",
            task_family="success-family", outcome=m.TrajectoryOutcome.SUCCESS,
            frozen_order=100+i,
        )
        for i in range(success)
    ]
    return rows


def test_largest_remainder_small_budget_preserves_success_reference() -> None:
    m = _m()
    census = _census(success=6, failure=1, families=("f1",))
    result = m.allocate_analysis_sampling(
        units=_units(m, failure_families=("f1",), success=6),
        census=census,
        total_analysis_budget=2,
    )
    assert (result["failure_quota"], result["success_quota"]) == (1, 1)


def test_every_failing_family_gets_floor_before_success() -> None:
    m = _m()
    census = _census(success=10, failure=3, families=("f1","f2","f3"))
    result = m.allocate_analysis_sampling(
        units=_units(m, failure_families=("f1","f2","f3"), success=10),
        census=census,
        total_analysis_budget=3,
    )
    assert result["success_quota"] == 0
    assert {x["task_family"] for x in result["failure_family_rows"]
            if x["selected_failure_count"]} == {"f1","f2","f3"}


def test_free_policy_override_is_not_public_api() -> None:
    m = _m()
    import inspect
    assert "policy" not in inspect.signature(m.allocate_analysis_sampling).parameters
    assert "policy" not in inspect.signature(m.select_analysis_regime).parameters


def test_missing_or_altered_human_approval_is_rejected(tmp_path: Path) -> None:
    m = _m()
    value = dict(m.load_sampling_approval())
    value["failure_share_by_regime"] = dict(value["failure_share_by_regime"])
    value["failure_share_by_regime"]["FAILURE_CRITICAL"] = 0.83
    path = tmp_path/"bad.json"
    import json
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        m.load_sampling_approval(path)
