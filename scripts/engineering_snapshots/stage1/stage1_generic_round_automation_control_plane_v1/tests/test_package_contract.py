from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_does_not_expose_scientific_execution_surface() -> None:
    production = [
        ROOT / "10_VERIFY_STAGE0_AND_WORKTREE.py",
        ROOT / "20_APPLY_STAGE1_CONTROL_PLANE.py",
        ROOT / "30_BUILD_STAGE1_REVIEW.py",
        ROOT / "RUN_STAGE1_CONTROL_PLANE_BUILD.sh",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in production)
    lowered = text.lower()
    for forbidden in (
        "sbatch ",
        "run_single_episode(",
        "automodelforcausallm",
        "get_peft_model",
        "trainer.train",
        "spawnedalfworldadapter",
        "alfworld_adapter.start",
    ):
        assert forbidden not in lowered


def test_package_binds_exact_stage0_closeout_and_head() -> None:
    constants = (
        ROOT / "stage1_pkg/constants.py"
    ).read_text(encoding="utf-8")
    assert (
        "7d29e40bf7c5f7df8869382071529a90"
        "fc2a44c1f3acc29d0e0b367d941bdba3"
    ) in constants
    assert (
        "daef26b9cde45182ada534d96335da3ea451f12f"
        in constants
    )


def test_package_has_explicit_stage1_approval_gate() -> None:
    run = (
        ROOT / "RUN_STAGE1_CONTROL_PLANE_BUILD.sh"
    ).read_text(encoding="utf-8")
    assert (
        "APPROVE_STAGE1_GENERIC_ROUND_CONTROL_PLANE_V1"
        in run
    )


def test_stage1_payload_is_additive_only() -> None:
    payload_files = {
        path.relative_to(ROOT / "payload").as_posix()
        for path in (ROOT / "payload").rglob("*")
        if path.is_file()
    }
    assert all(
        relative.startswith(("src/pchsi/round_control/", "tests/round_control/", "docs/stage1/"))
        for relative in payload_files
    )
