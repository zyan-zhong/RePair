from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from submission_contract import activation_identity, build_sbatch_argv


def test_activation_is_deterministic_and_content_bound():
    kwargs=dict(
        capsule_sha256="a"*64,
        execution_binding_file_sha256="b"*64,
        slurm_plan_file_sha256="c"*64,
        allocation_preflight_file_sha256="d"*64,
        implementation_head="commit-k",
    )
    first=activation_identity(**kwargs)
    second=activation_identity(**kwargs)
    assert first==second
    changed=activation_identity(**{**kwargs,"implementation_head":"commit-k+1"})
    assert first!=changed


def test_sbatch_is_held_nonrequeue_and_uses_only_plan_resources(tmp_path):
    plan={
        "schema_id":"ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1",
        "submission_command":"sbatch",
        "submission_resource_argv":[
            "--partition","authority-partition",
            "--nodes","2",
            "--ntasks","1",
            "--gpus","3",
        ],
        "human_selection_required":False,
    }
    argv=build_sbatch_argv(
        slurm_plan=plan,
        script_path=tmp_path/"job.sh",
        stdout_path=tmp_path/"out-%j.log",
        stderr_path=tmp_path/"err-%j.log",
        activation_id="f"*64,
    )
    assert argv[0]=="sbatch"
    assert "--hold" in argv
    assert "--no-requeue" in argv
    assert argv[argv.index("--partition")+1]=="authority-partition"
    assert argv[argv.index("--gpus")+1]=="3"
    assert "--comment" in argv
