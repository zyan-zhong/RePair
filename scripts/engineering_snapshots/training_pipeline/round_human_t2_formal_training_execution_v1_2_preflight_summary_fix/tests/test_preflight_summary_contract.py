from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_human_t2_preflight_requires_v21_direct_input_artifact_count() -> None:
    text = (
        ROOT / "20_OFFLINE_FORMAL_TRAINING_PREFLIGHT.py"
    ).read_text(encoding="utf-8")

    assert '"direct_input_artifact_count": 8' in text


def test_human_t2_preflight_retains_exact_training_summary() -> None:
    text = (
        ROOT / "20_OFFLINE_FORMAL_TRAINING_PREFLIGHT.py"
    ).read_text(encoding="utf-8")

    for fragment in (
        '"record_count": 12',
        '"optimizer_step_count": 3',
        '"optimizer_group_target_loss_tokens": [43, 53, 55]',
        '"direct_input_artifact_count": 8',
        '"parent_adapter_bundle_sha256"',
    ):
        assert fragment in text
