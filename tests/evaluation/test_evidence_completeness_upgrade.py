from pchsi.evaluation.evidence_completeness import (
    build_evidence_completeness_report,
    validate_distillation_evidence_complete,
)


def test_episode_evidence_gate_and_report_builder_are_exposed():
    assert callable(validate_distillation_evidence_complete)
    assert callable(build_evidence_completeness_report)
