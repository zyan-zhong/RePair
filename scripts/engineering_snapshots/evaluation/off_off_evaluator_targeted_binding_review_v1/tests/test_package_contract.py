from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_capture_is_read_only() -> None:
    text = (
        ROOT / "capture_targeted_offoff_binding.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "env.step(",
        "run_single_episode(",
        "sbatch",
        "srun",
        "PeftModel",
        "AutoModelForCausalLM",
    )
    for token in forbidden:
        assert token not in text


def test_capture_targets_existing_e1_stack() -> None:
    text = (
        ROOT / "capture_targeted_offoff_binding.py"
    ).read_text(encoding="utf-8")

    for path in (
        "scripts/evaluation/run_e1_evaluator.py",
        "src/pchsi/evaluation/episode_evaluator.py",
        "src/pchsi/evaluation/result_audit.py",
        "src/pchsi/evaluation/run_schedule.py",
        "src/pchsi/evaluation/select_policy_runtime.py",
        "src/pchsi/evaluation/select_execution_identity.py",
        "src/pchsi/evaluation/condition_execution_binding.py",
    ):
        assert path in text


def test_capture_binds_parent_and_candidate_adapters() -> None:
    text = (
        ROOT / "capture_targeted_offoff_binding.py"
    ).read_text(encoding="utf-8")

    assert (
        "908acf081e80008800284653c3340c397353eef0de08ee044f06810cab2a251e"
        in text
    )
    assert (
        "b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace"
        in text
    )
