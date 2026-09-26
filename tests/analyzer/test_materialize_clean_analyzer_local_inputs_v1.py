from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/analyzer/materialize_clean_analyzer_local_inputs_v1.py"
MODULE = ROOT / "src/pchsi/round_control/clean_analyzer_input_materialization.py"


def test_materializer_reuses_existing_scientific_components() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for token in (
        "validate_attempt_bundle",
        "build_clean_analyzer_evidence_pack",
        "build_clean_current_trajectory_binding",
        "build_pi0_i1_analyzer_policy_identity",
        "extract_mechanical_episode_evidence",
        "local_projection",
        "build_scientific_unit_identity",
        'validate_artifact("RUNTIME_INPUT_REGISTRY_V1"',
    ):
        assert token in text


def test_materializer_does_not_use_benchmark_or_old_sampling_scheduler() -> None:
    text = (SCRIPT.read_text(encoding="utf-8") + MODULE.read_text(encoding="utf-8")).lower()
    assert "valid_seen" not in text
    assert "valid_unseen" not in text
    assert "allocate_analysis_sampling" not in text
    assert "mechanical_analysis_sampling_thresholds" not in text


def test_production_adapter_has_no_fixed_reference_state_count() -> None:
    text = MODULE.read_text(encoding="utf-8")
    assert "main_unique_states_target" not in text
    assert "pilot_unique_states" not in text
    assert "maximum_source_state_count" in text
    assert "local_logical_call_cap" in text
    assert "manual_source_state_count_input_allowed" in text
