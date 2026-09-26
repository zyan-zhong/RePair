from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_script_does_not_execute_evaluation() -> None:
    text = (
        ROOT / "10_AUDIT_AND_DISCOVER.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "env.step(",
        "run_single_episode(",
        "run_e1_evaluator(",
        "subprocess.run([\"sbatch\"",
        "PeftModel",
        "AutoModelForCausalLM",
    )
    for token in forbidden:
        assert token not in text


def test_handoff_draft_requires_memory_and_harness_off() -> None:
    text = (
        ROOT / "10_AUDIT_AND_DISCOVER.py"
    ).read_text(encoding="utf-8")

    assert '"parent_memory": "OFF"' in text
    assert '"parent_harness": "OFF"' in text
    assert '"candidate_memory": "OFF"' in text
    assert '"candidate_harness": "OFF"' in text
    assert '"evaluation_execution_authorized": False' in text


def test_candidate_adapter_identity_is_fixed() -> None:
    text = (
        ROOT / "10_AUDIT_AND_DISCOVER.py"
    ).read_text(encoding="utf-8")

    assert "EXPECTED_CANDIDATE_ADAPTER" in text
    assert "908acf081e80008800284653c3340c39" in text
    assert "7353eef0de08ee044f06810cab2a251e" in text
