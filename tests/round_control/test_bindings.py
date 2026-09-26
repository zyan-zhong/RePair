from pathlib import Path

from pchsi.round_control.bindings import (
    REQUIRED_REUSE_COMPONENT_IDS,
    validate_repo_component_bindings,
)


def test_reuse_binding_registry_contains_stage0_handoff_components() -> None:
    expected = {
        "EVIDENCE_PACKAGE",
        "HIERARCHICAL_ANALYZER",
        "PERSISTENT_FAILURE_EXPERIENCE",
        "RESEARCH_PLANNER_PRE_POST",
        "DETERMINISTIC_DATA_BUILDER",
        "SELECT_EVALUATOR",
        "PROMOTION_ROLLBACK_CONTRACTS",
        "STRONG_TRACE_STORAGE",
    }
    assert expected.issubset(REQUIRED_REUSE_COMPONENT_IDS)


def test_repo_binding_validator_accepts_expected_repo_layout(tmp_path: Path) -> None:
    for relative in (
        "src/pchsi/reference_loop/analyzer_evidence_pack.py",
        "src/pchsi/analyzer/__init__.py",
        "src/pchsi/memory/__init__.py",
        "src/pchsi/research_intelligence/role_neutral.py",
        "src/pchsi/research_intelligence/research_planner_reference_trace.py",
        "src/pchsi/research_intelligence/reference_round.py",
        "src/pchsi/reference_loop/approved_materialization.py",
        "src/pchsi/evaluation/__init__.py",
        "src/pchsi/research_intelligence/takeover.py",
        "src/pchsi/research_intelligence/distillation.py",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")

    result = validate_repo_component_bindings(tmp_path)
    assert result["binding_status"] == "PASS"
