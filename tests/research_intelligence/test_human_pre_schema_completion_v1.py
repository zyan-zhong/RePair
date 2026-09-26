from __future__ import annotations

import importlib.util
from pathlib import Path

from pchsi.cognitive_runtime.researcher import finalize_human_pre
from pchsi.research_intelligence.human_planner_adjudication import (
    compile_human_planner_artifacts_v1,
)
from pchsi.research_intelligence.human_pre_schema_completion import (
    complete_human_pre_runtime_schema_v1,
)


def _load_fixture():
    path = Path(__file__).with_name(
        "test_human_planner_adjudication_v1.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_human_planner_fixture_schema_completion",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Human Planner fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._fixture()


def _legacy_pre():
    adjudication, dossier, shared = _load_fixture()
    artifacts = compile_human_planner_artifacts_v1(
        adjudication=adjudication,
        dossier=dossier,
        shared_input=shared,
    )
    return artifacts["human_pre_input"]


def test_completion_preserves_existing_scientific_fields():
    legacy = _legacy_pre()
    completed, receipt = complete_human_pre_runtime_schema_v1(legacy)

    for key, value in legacy.items():
        if key == "candidate_bottlenecks":
            continue
        assert completed[key] == value

    for old, new in zip(
        legacy["candidate_bottlenecks"],
        completed["candidate_bottlenecks"],
        strict=True,
    ):
        for key, value in old.items():
            assert new[key] == value


def test_completion_uses_only_unknown_null_and_empty_refs():
    completed, receipt = complete_human_pre_runtime_schema_v1(
        _legacy_pre()
    )

    for row in completed["candidate_bottlenecks"]:
        assert row["evidence_sha256s"] == []
        assert row["counterevidence_sha256s"] == []
        assert row["expected_value_class"] == "UNKNOWN"
        assert row["risk_class"] == "UNKNOWN"
        assert row["expected_environment_steps"] is None
        assert row["expected_model_logical_calls"] is None
        assert row["expected_transport_attempts"] is None
        assert row["expected_gpu_hours"] is None
        assert row["expected_api_cost_usd"] is None

    assert receipt["invented_evidence_refs"] is False
    assert receipt["invented_expected_value"] is False
    assert receipt["invented_risk"] is False
    assert receipt["invented_cost"] is False


def test_completed_payload_satisfies_runtime_human_pre_schema():
    completed, receipt = complete_human_pre_runtime_schema_v1(
        _legacy_pre()
    )
    finalized = finalize_human_pre(completed)

    assert finalized["schema_id"] == "HUMAN_RESEARCHER_PRE_V1"
    assert len(finalized["candidate_bottlenecks"]) == 4
    assert receipt["runtime_schema_validation_passed"] is True
    assert receipt["finalized_preview_pre_record_sha256"] == (
        finalized["pre_record_sha256"]
    )


def test_completion_does_not_mutate_legacy_payload():
    legacy = _legacy_pre()
    snapshot = repr(legacy)
    complete_human_pre_runtime_schema_v1(legacy)
    assert repr(legacy) == snapshot
