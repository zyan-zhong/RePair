from __future__ import annotations

import pytest

from pchsi.memory.component_ports import (
    AnalyzerProposalIngressV1,
    AnalyzerRepairProposalV1,
    MemoryEvidenceRefV1,
    MemoryPortAuthorityV1,
    MemorySourcePartitionV1,
    ResearcherMemoryEvidenceExportV1,
    SameStateVerifierIngressV1,
    VerifierEffectV1,
    build_verified_training_evidence_port_v1,
)


def _fact(char: str = "1") -> MemoryEvidenceRefV1:
    return MemoryEvidenceRefV1(
        evidence_kind="SEQUENCE_FAILURE_EXPERIENCE",
        artifact_sha256=char * 64,
        authority=MemoryPortAuthorityV1.FACT_AUTHORITY,
    )


def _hypothesis(char: str = "2") -> MemoryEvidenceRefV1:
    return MemoryEvidenceRefV1(
        evidence_kind="ANALYZER_HYPOTHESIS",
        artifact_sha256=char * 64,
        authority=MemoryPortAuthorityV1.SEMANTIC_HYPOTHESIS,
    )


def _proposal(condition: str = "C1_HIERARCHICAL_NO_HISTORY"):
    return AnalyzerProposalIngressV1(
        failure_instance_sha256="3" * 64,
        source_state_sha256="4" * 64,
        analyzer_condition=condition,
        factual_evidence_refs=(_fact(),),
        semantic_hypothesis_refs=(_hypothesis(),),
        counterevidence_refs=(),
        historical_memory_view_sha256=(
            "5" * 64 if condition == "C2_HIERARCHICAL_WITH_HISTORY" else None
        ),
        repair_proposals=(
            AnalyzerRepairProposalV1(
                rank=1,
                exact_action="look",
                admissible_menu_sha256="6" * 64,
                proposal_evidence_sha256="7" * 64,
            ),
        ),
        abstained=False,
    )


def test_only_c2_may_bind_historical_memory_view():
    with pytest.raises(ValueError, match="only C2"):
        AnalyzerProposalIngressV1(
            failure_instance_sha256="3" * 64,
            source_state_sha256="4" * 64,
            analyzer_condition="C1_HIERARCHICAL_NO_HISTORY",
            factual_evidence_refs=(_fact(),),
            semantic_hypothesis_refs=(_hypothesis(),),
            counterevidence_refs=(),
            historical_memory_view_sha256="5" * 64,
            repair_proposals=(),
            abstained=True,
        )
    assert _proposal("C2_HIERARCHICAL_WITH_HISTORY").ingress_sha256


def test_analyzer_port_preserves_authority_and_candidate_budget():
    value = _proposal()
    authority = value.to_dict()["authority_boundary"]
    assert authority == {
        "direct_environment_action": False,
        "benefit_harm_authority": False,
        "semantic_hypotheses_are_facts": False,
    }
    with pytest.raises(ValueError, match="at most three"):
        AnalyzerProposalIngressV1(
            failure_instance_sha256="3" * 64,
            source_state_sha256="4" * 64,
            analyzer_condition="C0_SINGLE_REFLECTION",
            factual_evidence_refs=(_fact(),),
            semantic_hypothesis_refs=(_hypothesis(),),
            counterevidence_refs=(),
            historical_memory_view_sha256=None,
            repair_proposals=tuple(
                AnalyzerRepairProposalV1(
                    rank=index,
                    exact_action=f"action {index}",
                    admissible_menu_sha256="6" * 64,
                    proposal_evidence_sha256=str(index) * 64,
                )
                for index in (1, 2, 3, 3)
            ),
            abstained=False,
        )


def _verifier(effect: VerifierEffectV1, f0: bool, f1: bool):
    return SameStateVerifierIngressV1(
        failure_instance_sha256="1" * 64,
        candidate_sha256="2" * 64,
        source_state_sha256="3" * 64,
        f0_evidence_sha256="4" * 64,
        f1_evidence_sha256="5" * 64,
        policy_identity_sha256="6" * 64,
        environment_identity_sha256="7" * 64,
        effect=effect,
        f0_terminal_success=f0,
        f1_terminal_success=f1,
        scientific_execution_complete=True,
    )


def test_verifier_is_effect_authority_and_training_port_is_typed():
    benefit = _verifier(VerifierEffectV1.BENEFIT, False, True)
    assert benefit.to_dict()["effect_authority"] == (
        "SAME_STATE_ENVIRONMENT_F0_F1"
    )
    port = build_verified_training_evidence_port_v1(
        verifier=benefit,
        source_partition=MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,
        policy_visible_input_sha256="8" * 64,
        candidate_output_sha256="9" * 64,
    )
    assert port.positive_sft_eligible is True
    assert port.preference_chosen_eligible is True
    assert port.training_execution_performed is False

    heldout = build_verified_training_evidence_port_v1(
        verifier=benefit,
        source_partition=MemorySourcePartitionV1.VALID_UNSEEN,
        policy_visible_input_sha256="8" * 64,
        candidate_output_sha256="9" * 64,
    )
    assert heldout.positive_sft_eligible is False

    harm = _verifier(VerifierEffectV1.HARM, True, False)
    rejected = build_verified_training_evidence_port_v1(
        verifier=harm,
        source_partition=MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,
        policy_visible_input_sha256="8" * 64,
        candidate_output_sha256="9" * 64,
    )
    assert rejected.preference_rejected_eligible is True
    assert rejected.positive_sft_eligible is False


def test_researcher_export_rejects_heldout_per_task_data():
    with pytest.raises(ValueError, match="aggregate-only"):
        ResearcherMemoryEvidenceExportV1(
            round_id="round-1",
            snapshot_sha256="1" * 64,
            memory_record_sha256s=("2" * 64,),
            analyzer_ingress_sha256s=("3" * 64,),
            verifier_ingress_sha256s=("4" * 64,),
            no_go_or_regression_sha256s=(),
            cost_evidence_sha256s=(),
            heldout_aggregate_metrics={
                "valid_unseen": {"trajectory": ["look"]}
            },
        )
