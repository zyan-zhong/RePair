from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_submitter_accepts_same_directory_identity_across_aliases() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_SMOKE.sh"
    ).read_text(encoding="utf-8")

    assert 'realpath -e "$EXPECTED_PACKAGE_ROOT_LOGICAL"' in text
    assert 'test ! "$PACKAGE_ROOT" -ef "$EXPECTED_PACKAGE_ROOT_LOGICAL"' in text
    assert "PACKAGE_ROOT_IDENTITY_PASS" in text
    assert 'test "$PACKAGE_ROOT" != "$EXPECTED_PACKAGE_ROOT"' not in text


def test_submitter_binds_slurm_to_physical_package_root() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_SMOKE.sh"
    ).read_text(encoding="utf-8")

    assert "--export=NIL" in text
    assert '--chdir="$PACKAGE_ROOT"' in text


def test_batch_script_uses_slurm_working_directory() -> None:
    text = (
        ROOT / "slurm/model_init_smoke.sbatch"
    ).read_text(encoding="utf-8")

    assert 'PACKAGE_ROOT="$(pwd -P)"' in text
    assert (
        'EXPECTED_PACKAGE_BASENAME='
        '"round_generic_training_model_init_smoke_v1_3_cluster_resource_policy_fix"'
    ) in text
    assert 'PACKAGE_ROOT="/data/home/' not in text
