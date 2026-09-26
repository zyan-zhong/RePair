from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_authorization_preparer_can_reuse_exact_existing_authorization() -> None:
    text = (
        ROOT / "10_PREPARE_FORMAL_AUTHORIZATION.py"
    ).read_text(encoding="utf-8")
    assert "FORMAL_TRAINING_AUTHORIZATION_REUSED" in text
    assert "EXISTING_AUTHORIZATION_CONTRACT_CHANGED" in text
    assert "EXISTING_AUTHORIZATION_WITNESS_BINDING_BROKEN" in text


def test_submitter_has_single_attempt_submission_guard() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_FORMAL_TRAINING.sh"
    ).read_text(encoding="utf-8")
    assert "submission_guard_v1" in text
    assert "FORMAL_TRAINING_ATTEMPT_ALREADY_SUBMITTED_OR_GUARDED" in text
    assert '"$SUBMISSION_GUARD/JOB_ID.txt"' in text


def test_submitter_releases_guard_only_when_sbatch_fails() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_FORMAL_TRAINING.sh"
    ).read_text(encoding="utf-8")
    assert 'rmdir "$SUBMISSION_GUARD" 2>/dev/null' in text
