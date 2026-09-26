from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_driver_is_non_executing_for_scientific_evaluation():
    text = (ROOT / "build_generic_select_binding.py").read_text(encoding="utf-8")
    forbidden = (
        "env.step(",
        "run_single_episode(",
        "sbatch",
        "srun",
        "vllm serve",
        "AutoModelForCausalLM",
        "PeftModel",
        "git push",
        "git commit",
    )
    for token in forbidden:
        assert token not in text


def test_driver_uses_isolated_detached_worktree():
    text = (ROOT / "build_generic_select_binding.py").read_text(encoding="utf-8")
    assert '"worktree", "add", "--detach"' in text
    assert "daef26b9cde45182ada534d96335da3ea451f12f" in text


def test_driver_enforces_tdd_red_before_green_patch():
    text = (ROOT / "build_generic_select_binding.py").read_text(encoding="utf-8")
    main = text[text.index("def main()") :]
    assert main.index("run_red()") < main.index("apply_green_patch()")
    assert "TDD_RED_UNEXPECTEDLY_PASSED" in text


def test_driver_binds_human_candidate_identity():
    text = (ROOT / "build_generic_select_binding.py").read_text(encoding="utf-8")
    assert "908acf081e80008800284653c3340c397353eef0de08ee044f06810cab2a251e" in text
    assert "P4-R2-HUMAN-T2-DIAGNOSTIC" in text


def test_driver_does_not_reclassify_task_access():
    text = (ROOT / "build_generic_select_binding.py").read_text(encoding="utf-8")
    assert "TASK_ACCESS_CLASS_CENSUS_V1.json" in text
    assert "SELECT_SUMMARY_ONLY" in text
    assert '"schedule_materialized": False' in text
    assert '"evaluation_executed": False' in text
