"""One entry point: native F0/F1 -> persisted verifier -> one Strong POST.

This canary intentionally does not manufacture a training plan or next-round
cursor. TRAIN and NO_TRAIN receipts expose that remaining integration boundary.
"""
from __future__ import annotations
import argparse
import fcntl
import os
import shlex
import subprocess
import sys
from pathlib import Path
from io_utils import read_json,put_json,sha,canonical,digest_file,write_new_or_equal
ROOT=Path(__file__).resolve().parent


def require_current_causal_release() -> dict:
    release=read_json(ROOT/'IMPLEMENTATION_RELEASE.json')
    required={
        'schema_id':'PAPER_CRITICAL_IMPLEMENTATION_RELEASE_V1',
        'implementation_candidate':False,
        'current_causal_round_live_execution_authorized':True,
        'training_execution_authorized':False,
        'next_round_launch_authorized':False,
        'max10_released':False,
    }
    for key,value in required.items():
        if release.get(key)!=value:
            raise RuntimeError('CURRENT_CAUSAL_RELEASE_GATE_FAILED:'+key)
    return release


def run_controller(run_root:Path):
    with (run_root/'CONTROLLER.lock').open('a+b') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('STATUS=CURRENT_ROUND_CONTROLLER_ALREADY_ACTIVE',flush=True);return 17
        terminal_path=run_root/'ROUND_EXECUTION_TERMINAL.json'
        if terminal_path.exists():
            print('STATUS='+read_json(terminal_path)['status'],flush=True);return 0
        plan_path=run_root/'EXECUTION_PLAN.json';plan=read_json(plan_path)
        if plan.get('plan_sha256')!=sha(canonical({k:v for k,v in plan.items() if k!='plan_sha256'})):
            raise ValueError('plan identity mismatch')
        summary={'schema_id':'CURRENT_CAUSAL_EXECUTION_CONTROLLER_TERMINAL_V1','plan_sha256':plan['plan_sha256'],
                 'full_round_closed':False,'next_round_launched':False,'max10_released':False,
                 'training_execution_count':0,'human_scientific_decision_count':0}
        try:
            if not (run_root/'GPU_JOB_TERMINAL.json').exists():
                if (run_root/'SBATCH_SUBMISSION_INTENT.json').exists():
                    raise ValueError('SUBMISSION_ALREADY_INTENDED_NO_BLIND_RESUBMIT')
                import native_branch
                sys.path.insert(0,str(ROOT/'vendor'))
                from policy_runtime_engine_profile import normalize_profile
                from policy_runtime_slurm_execution import load_cluster_policy
                runtime=read_json(Path(plan['runtime_path']))
                profile=normalize_profile(read_json(ROOT/'assets/ENGINE_PROFILE_FROM_LEDGER.json'),runtime=runtime)
                cluster=load_cluster_policy(ROOT/'vendor/POLICY_RUNTIME_SLURM_CLUSTER_EXECUTION_POLICY_V1.json')
                script=run_root/'RUN_GPU_JOB.sh'
                text='#!/usr/bin/env bash\nexport PYTHONDONTWRITEBYTECODE=1\nexec '+shlex.join([sys.executable,'-B',str(ROOT/'gpu_job.py'),'--plan',str(plan_path)])+'\n'
                write_new_or_equal(script,text.encode())
                argv=['sbatch','--parsable','--wait','--partition',cluster['inference_partition_default'],
                      '--nodes',str(cluster['nodes']),'--ntasks',str(cluster['ntasks']),
                      '--gpus',str(profile['tensor_parallel_size']),
                      '--time',plan['operations']['time_limit'],
                      '--job-name','pchsi-native-'+plan['plan_sha256'][:10],
                      '--output',str(run_root/'slurm-%j.out'),'--error',str(run_root/'slurm-%j.err'),str(script)]
                put_json(run_root/'SBATCH_SUBMISSION_INTENT.json',{'plan_sha256':plan['plan_sha256'],'argv':argv,'automatic_retry':False})
                print('STATUS=WAITING_FOR_CURRENT_NATIVE_SLURM_JOB',flush=True)
                with (run_root/'sbatch.stdout').open('xb') as stdout,(run_root/'sbatch.stderr').open('xb') as stderr:
                    result=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,check=False)
                put_json(run_root/'SBATCH_COMPLETION.json',{'returncode':result.returncode,'plan_sha256':plan['plan_sha256']})
                if not (run_root/'GPU_JOB_TERMINAL.json').exists():
                    raise ValueError('scheduler completed without matching native receipt')
            job=read_json(run_root/'GPU_JOB_TERMINAL.json')
            if job.get('plan_sha256')!=plan['plan_sha256']:
                raise ValueError('native job terminal belongs to another plan')
            # Re-run the independent verifier against persisted branches, never trust Slurm RC alone.
            from independent_verifier import verify_plan
            verification=verify_plan(plan_path,run_root)
            summary['environment_result_package_sha256']=verification['environment_result_package_sha256']
            summary['verifier_status']=verification['status']
            if verification['scientifically_complete_pair_count']==0:
                summary['status']='NATIVE_INFRA_OR_PROTOCOL_INVALID_NO_SCIENTIFIC_NO_TRAIN'
            else:
                from strong_post import execute_post
                post=execute_post(run_root,plan,verification)
                summary.update(status=post['status'],post_terminal=post)
            put_json(terminal_path,summary)
            print('STATUS='+summary['status'],flush=True)
            print('RESULT_ROOT='+str(run_root),flush=True)
            print('FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false',flush=True)
            return 0 if summary.get('post_terminal',{}).get('training_recommendation') in ('TRAIN','NO_TRAIN') else 20
        except Exception as exc:
            summary.update(status='CURRENT_EXECUTION_STOPPED_WITH_DIAGNOSTIC',error_type=type(exc).__name__,error_message=str(exc))
            put_json(terminal_path,summary)
            print('STATUS='+summary['status'],flush=True)
            print('DIAGNOSTIC='+str(exc),flush=True)
            return 20



def select_operational_attempt_root(base_root:Path)->Path:
    """Return the operational attempt root without changing scientific authority.

    A prior diagnostic may be retried automatically only when it provably stopped
    before scheduler submission or any scientific/model/environment/training effect.
    """
    terminal_path=base_root/'ROUND_EXECUTION_TERMINAL.json'
    if not terminal_path.exists():
        return base_root
    terminal=read_json(terminal_path)
    if terminal.get('status')!='CURRENT_EXECUTION_STOPPED_WITH_DIAGNOSTIC':
        return base_root
    unsafe=[]
    if (base_root/'SBATCH_SUBMISSION_INTENT.json').exists(): unsafe.append('SBATCH_SUBMISSION_INTENT')
    if (base_root/'GPU_JOB_TERMINAL.json').exists(): unsafe.append('GPU_JOB_TERMINAL')
    if terminal.get('training_execution_count') not in (None,0): unsafe.append('TRAINING_EXECUTION')
    if terminal.get('full_round_closed') is True: unsafe.append('FULL_ROUND_CLOSED')
    if terminal.get('next_round_launched') is True: unsafe.append('NEXT_ROUND_LAUNCHED')
    if terminal.get('environment_result_package_sha256') is not None: unsafe.append('ENVIRONMENT_RESULT')
    branches=base_root/'branches'
    if branches.exists() and any(p.is_file() for p in branches.rglob('*')): unsafe.append('BRANCH_EVIDENCE')
    if unsafe:
        raise RuntimeError('PRIOR_ATTEMPT_SIDE_EFFECTS_NO_AUTOMATIC_MECHANICAL_RETRY:'+','.join(sorted(unsafe)))
    identity=read_json(ROOT/'PACKAGE_IDENTITY.json')
    attempt_id=sha(canonical(identity))[:32]
    return base_root/'mechanical_recovery_attempts'/attempt_id

def launch(args):
    # The existing handoff identity, not this package version, determines the run root.
    import zipfile
    from io_utils import strict_loads
    archive=Path(args.capture_zip)
    if digest_file(archive)!=args.capture_sha256:raise ValueError('input capture SHA mismatch')
    with zipfile.ZipFile(archive) as z:
        handoff=strict_loads(z.read('pre_root/V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json'))
    locators=read_json(Path(args.deployment_authority) if args.deployment_authority else ROOT/'assets/deployment_authorities.json')
    operations=read_json(ROOT/'assets/operational_policy.json')
    base_run_root=Path(locators['output_parent'])/handoff['handoff_sha256']
    run_root=select_operational_attempt_root(base_run_root)
    run_root.mkdir(parents=True,exist_ok=True)
    if run_root != base_run_root:
        put_json(run_root/'MECHANICAL_RECOVERY_FROM.json',{'schema_id':'CURRENT_CAUSAL_MECHANICAL_RECOVERY_LINEAGE_V1','predecessor_run_root':str(base_run_root),'predecessor_terminal_sha256':digest_file(base_run_root/'ROUND_EXECUTION_TERMINAL.json'),'scientific_handoff_sha256':handoff['handoff_sha256'],'automatic_scientific_retry':False})
    with (run_root/'PREPARATION.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        if not (run_root/'EXECUTION_PLAN.json').exists():
            from round_plan import prepare_plan
            plan=prepare_plan(capture_zip=archive,expected_sha256=args.capture_sha256,
                              run_root=run_root,locators=locators,operations=operations)
        else:
            plan=read_json(run_root/'EXECUTION_PLAN.json')
            if plan['capture_zip_sha256']!=args.capture_sha256 or plan['handoff']!=handoff:
                raise ValueError('existing plan cannot be replaced by a new input')
    print('CURRENT_ROUND_RUN_ROOT='+str(run_root),flush=True)
    print('CURRENT_SELECTED_STATE_COUNT='+str(len(plan['states'])),flush=True)
    print('CURRENT_PLANNED_BRANCH_COUNT='+str(len(plan['handoff']['branch_plan'])),flush=True)
    print('CURRENT_EXECUTABLE_BRANCH_COUNT='+str(len(plan['branch_bindings'])),flush=True)
    if not args.execute_current_round:
        print('STATUS=PREPARED_NO_EXECUTION_AUTHORIZED',flush=True);return 0
    with (run_root/'controller.log').open('ab',buffering=0) as log:
        child=subprocess.Popen([sys.executable,'-B',str(ROOT/'controller.py'),'--resident-root',str(run_root)],
                                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    print('STATUS=CURRENT_CAUSAL_ROUND_CONTROLLER_DETACHED',flush=True)
    print('CONTROLLER_PID='+str(child.pid),flush=True)
    print('CONTROLLER_LOG='+str(run_root/'controller.log'),flush=True)
    print('MAX10_RELEASED=false',flush=True)
    return 0


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--resident-root',type=Path)
    ap.add_argument('--capture-zip',type=Path);ap.add_argument('--capture-sha256')
    ap.add_argument('--deployment-authority',type=Path)
    ap.add_argument('--execute-current-round',action='store_true')
    args=ap.parse_args()
    if args.resident_root or args.execute_current_round:
        require_current_causal_release()
    if args.resident_root:return run_controller(args.resident_root)
    if args.capture_zip is None or args.capture_sha256 is None:
        ap.error('--capture-zip and --capture-sha256 are required')
    return launch(args)
if __name__=='__main__':raise SystemExit(main())
