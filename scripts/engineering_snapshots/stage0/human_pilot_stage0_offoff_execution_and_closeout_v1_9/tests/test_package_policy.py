from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_slurm_requests_only_gpu_partition_and_reasonable_time() -> None:
    text = (
        ROOT / "slurm/human_pilot_stage0_offoff.sbatch"
    ).read_text(encoding="utf-8")
    assert "#SBATCH -p gpu_a800" in text
    assert "#SBATCH --gpus=1" in text
    assert "#SBATCH --time=00:45:00" in text
    for token in (
        "--cpus-per-task",
        "--cpus-per-gpu",
        "--mem=",
        "--mem-per-cpu",
        "--mem-per-gpu",
    ):
        assert token not in text


def test_package_reuses_existing_evaluator_and_does_not_implement_env_step() -> None:
    text = (
        ROOT / "stage0/live_runner.py"
    ).read_text(encoding="utf-8")
    assert "run_single_episode" in text
    assert "SpawnedAlfworldAdapter" in text
    assert "env.step(" not in text
    assert ".step(" not in text


def test_package_never_commits_pushes_or_claims_paper_efficacy() -> None:
    production = [
        ROOT / "stage0/live_runner.py",
        ROOT / "stage0/preflight.py",
        ROOT / "stage0/result_audit.py",
        ROOT / "stage0/closeout.py",
        ROOT / "RUN_PREFLIGHT_AND_SUBMIT.sh",
    ]
    joined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in production
    )
    assert "git push" not in joined
    assert "git commit" not in joined
    assert '"paper_efficacy_evidence": False' in (
        ROOT / "stage0/closeout.py"
    ).read_text(encoding="utf-8")



def test_final_result_audit_reloads_every_published_attempt() -> None:
    text = (
        ROOT / "stage0/result_audit.py"
    ).read_text(encoding="utf-8")
    assert "audit_receipt_attempts" in text
    assert "load_attempt_directory_v1" in text



def test_closeout_uses_staging_directory_before_publishing_review_root() -> None:
    text = (
        ROOT / "stage0/result_audit.py"
    ).read_text(encoding="utf-8")
    assert "review_v1.staging" in text
    assert "os.replace" in text
    assert "atomic_publish_zip" in text



def test_submitter_blocks_duplicate_active_slurm_job() -> None:
    text = (
        ROOT / "RUN_PREFLIGHT_AND_SUBMIT.sh"
    ).read_text(encoding="utf-8")
    assert "LAST_STAGE0_JOB_ID.txt" in text
    assert "STAGE0_PREVIOUS_JOB_STILL_ACTIVE" in text
    assert "squeue" in text



def test_live_runner_supports_graceful_time_boundary_between_pairs() -> None:
    live = (
        ROOT / "stage0/live_runner.py"
    ).read_text(encoding="utf-8")
    entry = (
        ROOT / "stage0/slurm_entry.py"
    ).read_text(encoding="utf-8")
    assert "stop_before_monotonic" in live
    assert "graceful_partial" in live
    assert "STAGE0_GRACEFUL_PARTIAL_COMPLETE" in entry



def test_offline_preflight_audits_exact_runtime_versions() -> None:
    text = (
        ROOT / "stage0/preflight.py"
    ).read_text(encoding="utf-8")
    assert "runtime_imports.log" in text
    assert 'vllm.__version__ == "0.11.0"' in text
    assert 'transformers.__version__ == "4.57.3"' in text
    assert 'torch.__version__ == "2.8.0+cu128"' in text



def test_submitter_activates_exact_frozen_environment() -> None:
    text = (
        ROOT / "RUN_PREFLIGHT_AND_SUBMIT.sh"
    ).read_text(encoding="utf-8")
    assert (
        "/data/apps/miniforge3/25.11.0-1/etc/profile.d/conda.sh"
        in text
    )
    assert (
        "/data/home/scwb204/run/sdar_repro/conda_envs/"
        "sdar_sft_py312"
        in text
    )
    assert "conda activate" in text



def test_stage0_sbatch_does_not_depend_on_module_shell_function() -> None:
    text = (
        ROOT / "slurm/human_pilot_stage0_offoff.sbatch"
    ).read_text(encoding="utf-8")

    assert "module purge" not in text
    assert "module load" not in text
    assert "command -v module" not in text


def test_stage0_sbatch_uses_exact_conda_bootstrap_with_explicit_rc_checks() -> None:
    text = (
        ROOT / "slurm/human_pilot_stage0_offoff.sbatch"
    ).read_text(encoding="utf-8")

    assert text.startswith("#!/bin/bash\n")
    assert (
        'CONDA_SH="/data/apps/miniforge3/25.11.0-1/etc/profile.d/conda.sh"'
        in text
    )
    assert (
        'CONDA_ENV="/data/home/scwb204/run/sdar_repro/conda_envs/'
        'sdar_sft_py312"'
        in text
    )
    assert '. "$CONDA_SH"' in text
    assert 'conda activate "$CONDA_ENV"' in text
    assert "STOP=CONDA_INITIALIZATION_FAILED" in text
    assert "STOP=CONDA_ACTIVATION_FAILED" in text
    assert "set -euo pipefail" not in text


def test_patch_release_uses_isolated_preflight_and_authorization_receipt_roots() -> None:
    text = (
        ROOT / "stage0/constants.py"
    ).read_text(encoding="utf-8")

    assert 'PREFLIGHT_ROOT = STAGE0_ROOT / "preflight_v1_9"' in text
    assert (
        'AUTHORIZATION_ROOT = '
        'STAGE0_ROOT / "authorization_v1_9"'
        in text
    )



def test_v16_requests_short_backfill_friendly_time_window() -> None:
    text = (
        ROOT / "slurm/human_pilot_stage0_offoff.sbatch"
    ).read_text(encoding="utf-8")

    assert "#SBATCH --time=00:45:00" in text
    assert "#SBATCH --time=02:00:00" not in text


def test_v16_graceful_cutoff_matches_short_allocation() -> None:
    text = (
        ROOT / "stage0/slurm_entry.py"
    ).read_text(encoding="utf-8")

    assert "30 * 60" in text
    assert "100 * 60" not in text


def test_v16_uses_new_preflight_and_authorization_roots() -> None:
    text = (
        ROOT / "stage0/constants.py"
    ).read_text(encoding="utf-8")

    assert 'PREFLIGHT_ROOT = STAGE0_ROOT / "preflight_v1_9"' in text
    assert (
        'AUTHORIZATION_ROOT = '
        'STAGE0_ROOT / "authorization_v1_9"'
        in text
    )
