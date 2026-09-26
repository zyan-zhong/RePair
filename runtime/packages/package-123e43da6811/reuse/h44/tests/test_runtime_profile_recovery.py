import json
from pathlib import Path
import importlib
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
VENDOR=ROOT/'vendor'
if str(VENDOR) not in sys.path: sys.path.insert(0,str(VENDOR))


def runtime_fixture():
    return {
        'base_model_local_path':'/data/run01/scwb204/sdar_repro/clean_model_snapshots/Qwen2.5-3B-Instruct/aa8e72537993ba99e69dfaafa59ed015b17504d1',
        'served_model_name':'PI0-CLEAN-QWEN25-3B-INSTRUCT',
        'context_window_tokens':32768,
        'policy_base_url':'http://127.0.0.1:8000',
        'vllm_version':'0.11.0',
    }


def test_engine_profile_receipt_direct_reuse_surface_exists_and_binds_runtime():
    mod=importlib.import_module('policy_runtime_engine_profile')
    assert callable(getattr(mod,'normalize_profile',None))
    profile=json.loads((ROOT/'assets/ENGINE_PROFILE_FROM_LEDGER.json').read_text())
    normalized=mod.normalize_profile(profile,runtime=runtime_fixture())
    assert normalized['status']=='RESOLVED_UNIQUE_COMPATIBLE_POLICY_ENGINE_PROFILE'
    assert normalized['engine_profile_sha256']=='309a2441f31d210f9043dbb465c1e631ed175ca7179851e301b8e8aefca5a221'
    assert normalized['tensor_parallel_size']==1


def test_cluster_policy_uses_historical_authority_field_and_gpu_count_from_tp():
    slurm=importlib.import_module('policy_runtime_slurm_execution')
    policy=slurm.load_cluster_policy(ROOT/'vendor/POLICY_RUNTIME_SLURM_CLUSTER_EXECUTION_POLICY_V1.json')
    assert policy['inference_partition_default']=='gpu_a800'
    assert policy['gpu_count_rule']=='TENSOR_PARALLEL_SIZE'
    profile=importlib.import_module('policy_runtime_engine_profile').normalize_profile(
        json.loads((ROOT/'assets/ENGINE_PROFILE_FROM_LEDGER.json').read_text()),runtime=runtime_fixture())
    launch=importlib.import_module('policy_runtime_engine_profile').build_current_runtime_service_launch_contract(
        runtime_fixture(),profile,python_executable=sys.executable)
    contract=slurm.build_slurm_execution_contract(
        launch_contract=launch,engine_profile=profile,cluster_policy=policy,
        source_integration_root='/tmp/source',retry_integration_root='/tmp/retry',repo='/tmp/repo',
        python_executable=sys.executable,package_root=str(ROOT),launch_contract_path='/tmp/launch.json',
        execution_root='/tmp/exec',service_ready_timeout_seconds=600,branch_operational_timeout_seconds=3600,
        termination_grace_seconds=30)
    assert contract['partition']=='gpu_a800'
    assert contract['gpus']==profile['tensor_parallel_size']
    argv=slurm.build_sbatch_argv(contract,'job.sh','out.log','err.log')
    assert argv[argv.index('--partition')+1]=='gpu_a800'
    assert argv[argv.index('--gpus')+1]=='1'


def test_gpu_job_import_surface_matches_vendored_runtime_contract():
    # This is the exact import seam that failed on the server.
    if 'gpu_job' in sys.modules: del sys.modules['gpu_job']
    import gpu_job
    assert callable(gpu_job.normalize_profile)


def test_gpu_job_uses_existing_readiness_probe_not_nonexistent_service_helpers():
    import policy_runtime_service as svc
    assert callable(svc.wait_for_policy_runtime_service)
    assert callable(svc.readiness_with_sha)
    assert not hasattr(svc,'start_service')


def test_controller_engine_profile_and_cluster_policy_seam_reaches_sbatch_argv(tmp_path,monkeypatch):
    import controller
    from io_utils import canonical,sha,put_json
    runtime=runtime_fixture()
    runtime_path=tmp_path/'runtime.json';put_json(runtime_path,runtime)
    plan={
      'schema_id':'CURRENT_ACCEPTED_PRE_NATIVE_EXECUTION_PLAN_V1','round_id':'r1',
      'runtime_path':str(runtime_path),'runtime_file_sha256':__import__('io_utils').digest_file(runtime_path),
      'source_request':{'parent_policy_id':'parent'},'handoff':{'branch_plan':[]},'states':[],
      'branch_bindings':[],'operations':{'time_limit':'00:10:00'},
    }
    plan['plan_sha256']=sha(canonical(plan));put_json(tmp_path/'EXECUTION_PLAN.json',plan)
    captured={}
    class R: returncode=0
    def fake_run(argv,**kwargs):
        captured['argv']=list(argv)
        put_json(tmp_path/'GPU_JOB_TERMINAL.json',{'plan_sha256':plan['plan_sha256'],'status':'VERIFIED_COMPLETE'})
        return R()
    monkeypatch.setattr(controller.subprocess,'run',fake_run)
    monkeypatch.setattr('independent_verifier.verify_plan',lambda *a,**k:{
      'environment_result_package_sha256':'a'*64,'status':'VERIFIED_COMPLETE','scientifically_complete_pair_count':1})
    monkeypatch.setattr('strong_post.execute_post',lambda *a,**k:{
      'status':'CAUSAL_ROUND_POST_NO_TRAIN_RECORDED_RESIDENT_HANDOFF_PENDING','training_recommendation':'NO_TRAIN','provider_calls':0})
    assert controller.run_controller(tmp_path)==0
    argv=captured['argv']
    assert argv[argv.index('--partition')+1]=='gpu_a800'
    assert argv[argv.index('--gpus')+1]=='1'
