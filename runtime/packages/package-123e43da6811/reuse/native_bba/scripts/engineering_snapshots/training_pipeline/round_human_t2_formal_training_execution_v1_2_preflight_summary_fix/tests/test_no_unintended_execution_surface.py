from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_authorization_and_review_code_do_not_train_directly() -> None:
    paths = [
        ROOT / "10_PREPARE_FORMAL_AUTHORIZATION.py",
        ROOT / "20_OFFLINE_FORMAL_TRAINING_PREFLIGHT.py",
        ROOT / "30_BUILD_FORMAL_TRAINING_REVIEW.py",
    ]
    forbidden = (
        "run_formal_training(",
        "optimizer.step(",
        ".backward(",
        "AutoModelForCausalLM",
        "PeftModel",
        "env.step(",
        "alfworld",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, (path, token)


def test_only_batch_script_invokes_reviewed_generic_stage_runner() -> None:
    text = (
        ROOT / "slurm/human_t2_formal_training.sbatch"
    ).read_text(encoding="utf-8")
    assert "python -m round_training.stage_runner" in text
    assert "30_BUILD_FORMAL_TRAINING_REVIEW.py" in text
