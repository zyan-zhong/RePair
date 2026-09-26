from pchsi.round_control.role_authority import (
    AuthorityPhaseV1,
    ResearchRoleV1,
    resolve_authority_plan,
)


def test_human_reference_phase_records_strong_shadow() -> None:
    plan = resolve_authority_plan(
        phase=AuthorityPhaseV1.HUMAN_PRIMARY_STRONG_SHADOW,
        takeover_evaluation=None,
    )
    assert plan.primary_actor(ResearchRoleV1.ANALYZER) == "HUMAN"
    assert "STRONG" in plan.shadow_actors(ResearchRoleV1.ANALYZER)
    assert plan.strong_trace_capture_required is True


def test_strong_primary_requires_existing_takeover_gate() -> None:
    try:
        resolve_authority_plan(
            phase=AuthorityPhaseV1.STRONG_PRIMARY_LOCAL_SHADOW,
            takeover_evaluation=None,
        )
    except ValueError as exc:
        assert "takeover" in str(exc).lower()
    else:
        raise AssertionError("strong primary was authorized without gate")


def test_local_primary_requires_local_gate() -> None:
    evaluation = {
        "schema_id": "RESEARCH_PLANNER_TAKEOVER_EVALUATION_V1",
        "strong_research_planner_primary_eligible": True,
        "local_training_and_shadow_eligible": True,
        "local_research_planner_primary_eligible": False,
    }
    try:
        resolve_authority_plan(
            phase=AuthorityPhaseV1.LOCAL_PRIMARY_STRONG_AUDIT,
            takeover_evaluation=evaluation,
        )
    except ValueError as exc:
        assert "local" in str(exc).lower()
    else:
        raise AssertionError("local primary was authorized without gate")
