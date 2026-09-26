"""Single-allocation policy service and current frozen native branches."""
from __future__ import annotations
import argparse
import os
import socket
import sys
import time
import subprocess
import signal
from pathlib import Path
from io_utils import canonical,sha,read_json,put_json,digest_file
from native_branch import execute_native_branch
from independent_verifier import verify_plan
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
from policy_runtime_engine_profile import normalize_profile,build_current_runtime_service_launch_contract
from policy_runtime_slurm_execution import load_cluster_policy
from policy_runtime_service import wait_for_policy_runtime_service,readiness_with_sha


def run_allocation(plan_path:Path):
    if not os.environ.get('SLURM_JOB_ID'):
        raise ValueError('GPU execution requires a Slurm allocation; login execution forbidden')
    run_root=plan_path.parent;plan=read_json(plan_path)
    if plan.get('plan_sha256')!=sha(canonical({k:v for k,v in plan.items() if k!='plan_sha256'})):
        raise ValueError('plan SHA mismatch')
    proc=None
    result={'schema_id':'CURRENT_NATIVE_GPU_JOB_RESULT_V1','plan_sha256':plan['plan_sha256'],
            'status':'NOT_STARTED','max10_released':False}
    try:
        if not plan['branch_bindings']:
            result['status']='NO_EXECUTABLE_SELECTED_SEMANTICS'
        else:
            runtime=read_json(Path(plan['runtime_path']))
            if digest_file(Path(plan['runtime_path']))!=plan['runtime_file_sha256']:
                raise ValueError('runtime file changed')
            import torch
            import vllm
            if vllm.__version__!=runtime['vllm_version']:
                raise ValueError('vLLM version differs from current frozen runtime')
            profile=normalize_profile(read_json(ROOT/'assets/ENGINE_PROFILE_FROM_LEDGER.json'),runtime=runtime)
            cluster=load_cluster_policy(ROOT/'vendor/POLICY_RUNTIME_SLURM_CLUSTER_EXECUTION_POLICY_V1.json')
            if os.environ.get('SLURM_JOB_PARTITION') != cluster['inference_partition_default']:
                raise ValueError('Slurm partition differs from frozen cluster policy')
            if not (os.environ.get('SLURM_JOB_NODELIST') or os.environ.get('SLURM_NODELIST')):
                raise ValueError('Slurm node list missing')
            if torch.cuda.device_count() < profile['tensor_parallel_size']:
                raise ValueError('CUDA visible device count below engine-profile tensor parallel size')
            # Endpoint routing is deployment state, not model/prompt/decoding authority.
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            service_runtime=dict(runtime);service_runtime['policy_base_url']=f'http://127.0.0.1:{port}'
            if {k:v for k,v in service_runtime.items() if k!='policy_base_url'}!={k:v for k,v in runtime.items() if k!='policy_base_url'}:
                raise ValueError('service routing altered scientific runtime')
            launch=build_current_runtime_service_launch_contract(runtime=service_runtime,profile=profile,python_executable=sys.executable)
            lease={'schema_id':'CURRENT_POLICY_SERVICE_LEASE_V1','runtime_file_sha256':plan['runtime_file_sha256'],
                   'served_model_name':runtime['served_model_name'],'policy_base_url':service_runtime['policy_base_url'],
                   'slurm_job_id':os.environ['SLURM_JOB_ID'],'hostname':socket.gethostname(),
                   'operational_attempt_id':run_root.name,
                   'launch_contract':launch,'routing_only':True}
            lease['lease_sha256']=sha(canonical(lease))
            put_json(run_root/'service/LEASE.json',lease)
            put_json(run_root/'service/LAUNCH_CONTRACT.json',launch)
            service_log=(run_root/'service/vllm.log')
            service_log.parent.mkdir(parents=True,exist_ok=True)
            service_log_handle=service_log.open('ab',buffering=0)
            proc=subprocess.Popen(launch['launch_command'],stdin=subprocess.DEVNULL,stdout=service_log_handle,
                                  stderr=subprocess.STDOUT,start_new_session=True)
            readiness=wait_for_policy_runtime_service(
                service_runtime,
                timeout_seconds=plan['operations']['service_ready_timeout_seconds'],
                poll_seconds=plan['operations']['service_poll_seconds'])
            if not readiness.get('ready'):
                if proc.poll() is not None:
                    raise ValueError('policy service terminated before readiness:'+str(proc.returncode))
                raise ValueError('policy service readiness failed:'+str(readiness.get('classification')))
            put_json(run_root/'service/READY.json',readiness_with_sha(readiness))
            for item in plan['branch_bindings']:
                binding=read_json(Path(item['path']))
                if digest_file(Path(item['path']))!=item['file_sha256']:raise ValueError('branch binding changed')
                try:
                    terminal=execute_native_branch(binding,run_root/'branches'/binding['branch_key_sha256'],service_lease=lease)
                    print('NATIVE_BRANCH',binding['arm'],binding['replicate_index'],terminal['status'],flush=True)
                except Exception as exc:
                    # Preserve missingness; never rerun an ambiguous branch or replace a state.
                    put_json(run_root/'branch_errors'/(binding['branch_key_sha256']+'.json'),
                             {'branch_key_sha256':binding['branch_key_sha256'],'type':type(exc).__name__,'message':str(exc),'retry':False})
            verification=verify_plan(plan_path,run_root)
            result.update(status=verification['status'],environment_result_package_sha256=verification['environment_result_package_sha256'])
    except Exception as exc:
        result.update(status='NATIVE_EXECUTION_INVALID',error_type=type(exc).__name__,error_message=str(exc))
    finally:
        if proc is not None:
            try:
                graceful=True
                if proc.poll() is None:
                    try: os.killpg(proc.pid,signal.SIGTERM)
                    except ProcessLookupError: pass
                    try: proc.wait(timeout=plan['operations']['termination_grace_seconds'])
                    except subprocess.TimeoutExpired:
                        graceful=False
                        try: os.killpg(proc.pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                        proc.wait()
                result['service_teardown']={'pid':proc.pid,'returncode':proc.returncode,'graceful':graceful,'owned_process_group_only':True}
            except Exception as exc:result['teardown_error']=str(exc);result['status']='NATIVE_EXECUTION_INVALID'
        if 'service_log_handle' in locals():
            service_log_handle.close()
    if not (run_root/'verifier/ENVIRONMENT_RESULT_PACKAGE.json').exists():
        verification=verify_plan(plan_path,run_root)
        result['environment_result_package_sha256']=verification['environment_result_package_sha256']
    put_json(run_root/'GPU_JOB_TERMINAL.json',result)
    return 0 if result['status'] in ('VERIFIED_COMPLETE','VERIFIED_WITH_MISSINGNESS') else 20

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True)
    raise SystemExit(run_allocation(ap.parse_args().plan))
