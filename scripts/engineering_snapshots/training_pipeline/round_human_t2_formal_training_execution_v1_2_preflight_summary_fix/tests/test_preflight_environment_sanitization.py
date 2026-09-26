from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_submitter_unsets_all_forbidden_ambient_variables_for_preflight() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_FORMAL_TRAINING.sh"
    ).read_text(encoding="utf-8")

    for name in (
        "OUTPUT_ROOT",
        "REPRO_ROOT",
        "SOURCE_ADAPTER_ROOT",
        "NATIVE_ROOT",
        "MAINLINE_ROOT",
        "PREFLIGHT_ROOT",
        "REVIEW_ROOT",
    ):
        assert f"-u {name}" in text

    assert "20_OFFLINE_FORMAL_TRAINING_PREFLIGHT.py" in text


def test_submitter_does_not_mutate_parent_shell_with_unset_commands() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_FORMAL_TRAINING.sh"
    ).read_text(encoding="utf-8")

    forbidden_direct_unsets = (
        "unset OUTPUT_ROOT",
        "unset REPRO_ROOT",
        "unset SOURCE_ADAPTER_ROOT",
        "unset NATIVE_ROOT",
        "unset MAINLINE_ROOT",
        "unset PREFLIGHT_ROOT",
        "unset REVIEW_ROOT",
    )
    for token in forbidden_direct_unsets:
        assert token not in text


def test_offline_preflight_itself_remains_fail_closed() -> None:
    text = (
        ROOT / "20_OFFLINE_FORMAL_TRAINING_PREFLIGHT.py"
    ).read_text(encoding="utf-8")

    assert "reject_ambient_environment(context)" in text
