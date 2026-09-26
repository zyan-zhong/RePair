from pchsi.round_control.benchmark_sealing import (
    BenchmarkSplitV1,
    BenchmarkResultSealV1,
)
from pchsi.round_control.retention import (
    ArtifactKindV1,
    decide_cross_round_retention,
)


def test_pilot_semantic_artifacts_are_forbidden_from_clean_round() -> None:
    decision = decide_cross_round_retention(
        origin_round_role="PILOT_ENGINEERING_ROUND_V1",
        artifact_kind=ArtifactKindV1.TASK_SPECIFIC_REPAIR,
        access_class="PILOT_CONTAMINATED",
    )
    assert decision.allowed is False


def test_clean_strong_trace_can_be_retained_for_localization() -> None:
    decision = decide_cross_round_retention(
        origin_round_role="CLEAN_TRAIN_ROUND_V1",
        artifact_kind=ArtifactKindV1.STRONG_STRUCTURED_TRACE,
        access_class="TRAIN_REFERENCE_ROUND",
    )
    assert decision.allowed is True
    assert decision.destination == "LOCALIZATION_SUPERVISION"


def test_benchmark_cannot_be_revealed_before_all_models_are_frozen() -> None:
    seal = BenchmarkResultSealV1.create(
        benchmark_split=BenchmarkSplitV1.VALID_UNSEEN,
        checkpoint_id="pi0-clean",
        shared_protocol_sha256="c" * 64,
        result_artifact_sha256="d" * 64,
    )
    assert seal.revealed is False
    try:
        seal.reveal(all_comparison_models_frozen=False)
    except ValueError as exc:
        assert "frozen" in str(exc).lower()
    else:
        raise AssertionError("benchmark result was revealed early")
