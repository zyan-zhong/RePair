from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_package_contains_no_training_or_environment_execution_surface() -> None:
    paths = [
        ROOT / "10_BUILD_HANDOFF_REVIEW.py",
        ROOT / "handoff/handoff_builder.py",
        ROOT / "handoff/smoke_review_audit.py",
    ]
    forbidden = (
        "sbatch",
        "srun",
        "run_formal_training",
        "execute_training_stage",
        "optimizer.step",
        ".backward(",
        "env.step(",
        "alfworld",
        "PeftModel",
        "AutoModelForCausalLM",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, (path, token)
