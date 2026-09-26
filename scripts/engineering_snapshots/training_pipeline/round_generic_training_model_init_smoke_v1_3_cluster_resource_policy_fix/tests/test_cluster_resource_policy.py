from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gpu_job_does_not_request_cluster_managed_cpu_or_memory() -> None:
    text = (
        ROOT / "slurm/model_init_smoke.sbatch"
    ).read_text(encoding="utf-8")

    forbidden = (
        "--cpus-per-task",
        "--cpus-per-gpu",
        "--mem=",
        "--mem-per-cpu",
        "--mem-per-gpu",
    )
    for token in forbidden:
        assert token not in text


def test_gpu_job_requests_only_required_gpu_resource_and_short_time() -> None:
    text = (
        ROOT / "slurm/model_init_smoke.sbatch"
    ).read_text(encoding="utf-8")

    assert "#SBATCH -p gpu_a800" in text
    assert "#SBATCH --gpus=1" in text
    assert "#SBATCH --time=00:10:00" in text


def test_submitter_does_not_override_cluster_managed_cpu_or_memory() -> None:
    text = (
        ROOT / "RUN_PREPARE_AND_SUBMIT_SMOKE.sh"
    ).read_text(encoding="utf-8")

    forbidden = (
        "--cpus-per-task",
        "--cpus-per-gpu",
        "--mem=",
        "--mem-per-cpu",
        "--mem-per-gpu",
    )
    for token in forbidden:
        assert token not in text
