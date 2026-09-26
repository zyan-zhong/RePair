from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def test_operational_policy_disables_scientific_task_retry():
    obj=json.loads((ROOT/"V1232_LIVE_ROLLOUT_OPERATIONAL_POLICY_V1.json").read_text())
    assert obj["task_retry_count"]==0
    assert obj["job_requeue_authorized"] is False
    assert obj["submission_hold_before_durable_job_id"] is True

def test_generic_production_has_no_current_experiment_literals():
    text="\n".join(
        (ROOT/name).read_text(encoding="utf-8")
        for name in (
            "submit_v1232.py",
            "submission_contract.py",
            "live_rollout_job.py",
        )
    )
    forbidden=(
        "STRONG-PRIMARY-R1-PI0-I1",
        "PI0_CLEAN",
        "gpu_a800",
        "2843",
        "07221cbfa374e5ac",
        "8ebdf8feaa3f5287",
        "309a2441f31d210f",
        "Qwen2.5-3B-Instruct",
    )
    for token in forbidden:
        assert token not in text

def test_live_job_does_not_submit_slurm_or_train():
    text=(ROOT/"live_rollout_job.py").read_text(encoding="utf-8")
    assert '["sbatch"' not in text
    assert "subprocess.run(['sbatch'" not in text
    assert "torch.optim" not in text
    assert ".backward(" not in text
    assert "trainer.train" not in text.lower()
