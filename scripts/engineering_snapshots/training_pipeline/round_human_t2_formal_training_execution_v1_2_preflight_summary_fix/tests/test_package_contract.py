from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_package_metadata_freezes_current_scientific_boundary() -> None:
    value = json.loads(
        (ROOT / "PACKAGE_METADATA.json").read_text(
            encoding="utf-8"
        )
    )
    assert value["training_contract"] == {
        "data_seed": 17,
        "diagnostic_only": True,
        "epochs": 1,
        "optimizer_steps": 3,
        "promotion_eligible": False,
        "rows": 12,
        "target_loss_tokens": 151,
        "training_seed": 17,
    }
    assert value["package_does_not_preapprove_training"] is True
    assert value["pretraining_review_zip_sha256"] == (
        "8d9b88a4e42df9f60003b4081137839a"
        "4a8b186662af5456a376051b424f8ae0"
    )


def test_submitter_requires_explicit_execution_approval() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_FORMAL_TRAINING.sh"
    ).read_text(encoding="utf-8")
    assert "EXPLICIT_FORMAL_TRAINING_EXECUTION_APPROVAL_REQUIRED" in text
    assert 'APPROVE_HUMAN_T2_FORMAL_TRAINING_V1' in text


def test_slurm_requests_no_cluster_managed_cpu_or_memory() -> None:
    text = (
        ROOT / "slurm/human_t2_formal_training.sbatch"
    ).read_text(encoding="utf-8")
    for token in (
        "--cpus-per-task",
        "--cpus-per-gpu",
        "--mem=",
        "--mem-per-cpu",
        "--mem-per-gpu",
    ):
        assert token not in text
    assert "#SBATCH -p gpu_a800" in text
    assert "#SBATCH --gpus=1" in text
    assert "#SBATCH --time=00:10:00" in text


def test_submitter_uses_clean_slurm_environment() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_FORMAL_TRAINING.sh"
    ).read_text(encoding="utf-8")
    assert "--export=NIL" in text
    assert '--chdir="$PACKAGE_ROOT"' in text
