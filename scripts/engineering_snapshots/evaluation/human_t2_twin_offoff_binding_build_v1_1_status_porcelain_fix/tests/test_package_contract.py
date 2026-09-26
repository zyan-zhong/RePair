from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_package_does_not_execute_evaluation() -> None:
    text = (
        ROOT / "twin_builder.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "run_single_episode(",
        "env.step(",
        "vllm serve",
        "sbatch",
        "srun",
        "AutoModelForCausalLM",
        "PeftModel",
        "PolicyClient(",
    )
    for token in forbidden:
        assert token not in text


def test_package_fixes_exact_parent_candidate_and_select_grid() -> None:
    value = json.loads(
        (ROOT / "PACKAGE_METADATA.json").read_text(
            encoding="utf-8"
        )
    )

    assert value["task_access_manifest"][
        "expected_select_summary_only_count"
    ] == 17
    assert value["replicate_seeds"] == [
        17,
        31,
        47,
        73,
        101,
    ]
    assert value["parent"][
        "adapter_bundle_sha256"
    ] == (
        "b296f2254b1fa1f2e141dffd3f6b5af"
        "903f839df4790ffcb245fd8dd57773ace"
    )
    assert value["candidate"][
        "adapter_bundle_sha256"
    ] == (
        "908acf081e80008800284653c3340c39"
        "7353eef0de08ee044f06810cab2a251e"
    )


def test_package_keeps_evaluation_and_promotion_closed() -> None:
    value = json.loads(
        (ROOT / "PACKAGE_METADATA.json").read_text(
            encoding="utf-8"
        )
    )
    assert value[
        "evaluation_execution_authorized"
    ] is False
    assert value[
        "evaluation_execution_count"
    ] == 0
    assert value[
        "candidate"
    ]["promotion_eligible"] is False
