from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_submitter_uses_clean_slurm_environment() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_SMOKE.sh"
    ).read_text(encoding="utf-8")
    assert "--export=NIL" in text


def test_job_executes_smoke_and_review_only() -> None:
    text = (
        ROOT / "slurm/model_init_smoke.sbatch"
    ).read_text(encoding="utf-8")
    assert "python -m smoke.smoke_runner" in text
    assert "python ./20_BUILD_SMOKE_REVIEW.py" in text
    forbidden = (
        "round_training.stage_runner",
        "run_formal_training",
        "optimizer.step",
        "trainer.train",
    )
    for token in forbidden:
        assert token not in text
