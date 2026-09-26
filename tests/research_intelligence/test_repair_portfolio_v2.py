from __future__ import annotations

import hashlib

import pytest

from pchsi.research_intelligence.repair_portfolio import (
    PortfolioDecisionV1,
    RepairCandidateOriginV1,
    RepairDispositionV1,
    RepairLineageV1,
    RepairProgramKindV1,
    ResearchRepairCandidateV1,
    ResearchRepairPortfolioV1,
    ResearchRepairProgramV1,
)


D = hashlib.sha256(b"evidence").hexdigest()
D2 = hashlib.sha256(b"analyzer").hexdigest()


def lineage(*, composed: bool = False) -> RepairLineageV1:
    return RepairLineageV1(
        source_state_ids=("state-1",),
        source_candidate_ids=("a1", "a2") if composed else ("a1",),
        source_group_ids=("group-1",),
        analyzer_artifact_sha256s=(D2,),
        memory_record_ids=("memory-1",) if composed else (),
        current_evidence_sha256s=(D,),
    )


def candidate(
    candidate_id: str,
    *,
    origin: RepairCandidateOriginV1 = RepairCandidateOriginV1.ANALYZER,
    disposition: RepairDispositionV1 = RepairDispositionV1.SELECTED,
) -> ResearchRepairCandidateV1:
    return ResearchRepairCandidateV1(
        candidate_id=candidate_id,
        principal_change_id="change-1",
        origin=origin,
        repair_description="Switch from stale search to verified phase transition.",
        repair_contract="SOURCE_BOUND_REPAIR_V1",
        mechanism_target="PROGRESS_AND_PHASE_TRACKING",
        task_family_scope=("pick_clean_then_place_in_recep",),
        estimated_value=0.7,
        estimated_harm_risk=0.1,
        estimated_verification_calls=5,
        evidence_support=0.8,
        novelty_or_nonduplication_reason="Not a duplicate of prior one-action correction.",
        disposition=disposition,
        disposition_reason="Selected for high expected verified yield.",
        lineage=lineage(composed=origin is RepairCandidateOriginV1.RESEARCHER_COMPOSED),
    )


def test_planner_may_compose_high_value_repair_program_with_lineage() -> None:
    c1 = candidate("c1")
    c2 = candidate("c2", origin=RepairCandidateOriginV1.RESEARCHER_COMPOSED)
    program = ResearchRepairProgramV1(
        program_id="program-1",
        principal_change_id="change-1",
        kind=RepairProgramKindV1.COMPOSED_REPAIR_PROGRAM,
        candidate_ids=("c1", "c2"),
        source_state_ids=("state-1",),
        falsifiable_hypothesis="A phase-aware recovery program will flip registered failures.",
        high_value_rationale="Targets a recurring mechanism across a protected family.",
        generalization_scope="Registered source states plus held task-family scope.",
        deterministic_projector_contract="DETERMINISTIC_SOURCE_REPAIR_PROJECTOR_V1",
        verification_protocol_id="F0F1_REPAIR_VERIFICATION_V2",
        estimated_verification_calls=10,
    )
    portfolio = ResearchRepairPortfolioV1(
        schema_version="RESEARCH_REPAIR_PORTFOLIO_V1",
        round_id="round-pi1-pi2",
        parent_policy_id="PI1_PILOT_DISTILLED",
        evidence_cutoff_sha256=D,
        principal_change_id="change-1",
        researcher_mode="HUMAN_REFERENCE",
        decision=PortfolioDecisionV1.SELECT_ONE_PROGRAM,
        verification_call_budget=12,
        candidates=(c1, c2),
        programs=(program,),
        selected_program_id="program-1",
        abstention_reason=None,
    )
    payload = portfolio.to_dict()
    assert payload["authority_boundary"]["may_discover_or_compose_repair_programs"] is True
    assert payload["authority_boundary"]["may_assign_benefit_harm_neutral_uncertain"] is False


def test_researcher_composed_candidate_requires_multiple_lineage_sources() -> None:
    bad = candidate("bad", origin=RepairCandidateOriginV1.RESEARCHER_COMPOSED)
    bad = ResearchRepairCandidateV1(
        **{
            **bad.__dict__,
            "lineage": RepairLineageV1(
                source_state_ids=("state-1",),
                source_candidate_ids=("a1",),
                source_group_ids=(),
                analyzer_artifact_sha256s=(D2,),
                memory_record_ids=(),
                current_evidence_sha256s=(D,),
            ),
        }
    )
    with pytest.raises(ValueError, match="at least two explicit source references"):
        bad.validate()


def test_selected_program_cannot_exceed_verification_budget() -> None:
    c1 = candidate("c1")
    program = ResearchRepairProgramV1(
        program_id="program-1",
        principal_change_id="change-1",
        kind=RepairProgramKindV1.DIRECT_SOURCE_REPAIR,
        candidate_ids=("c1",),
        source_state_ids=("state-1",),
        falsifiable_hypothesis="Registered repair flips the state.",
        high_value_rationale="High support and low harm estimate.",
        generalization_scope="Registered source state only.",
        deterministic_projector_contract="DETERMINISTIC_SOURCE_REPAIR_PROJECTOR_V1",
        verification_protocol_id="F0F1_REPAIR_VERIFICATION_V2",
        estimated_verification_calls=10,
    )
    portfolio = ResearchRepairPortfolioV1(
        schema_version="RESEARCH_REPAIR_PORTFOLIO_V1",
        round_id="round-pi1-pi2",
        parent_policy_id="PI1_PILOT_DISTILLED",
        evidence_cutoff_sha256=D,
        principal_change_id="change-1",
        researcher_mode="HUMAN_REFERENCE",
        decision=PortfolioDecisionV1.SELECT_ONE_PROGRAM,
        verification_call_budget=5,
        candidates=(c1,),
        programs=(program,),
        selected_program_id="program-1",
        abstention_reason=None,
    )
    with pytest.raises(ValueError, match="exceeds verification budget"):
        portfolio.validate()
