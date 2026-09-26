from __future__ import annotations
import argparse,fcntl,json,os,time
from pathlib import Path

from safe_io import load_obj,write_once
from autonomy_binding import assert_fixed_head
from current_round_driver import advance_current_round,BLOCKED,ADOPT,ROUTE,NO_TRAIN
from runtime_inheritance import snapshot_v110_runtime

FIXED='61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a'
RUNTIME='V110_RUNTIME_INHERITANCE_V1.json'
STATUS='AUTONOMOUS_CAMPAIGN_STATUS_V1.json'


def _lock(root:Path):
    root.mkdir(parents=True,exist_ok=True)
    p=root/'.campaign_writer.lock';fd=os.open(p,os.O_RDWR|os.O_CREAT,0o600)
    try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: os.close(fd);raise ValueError('CAMPAIGN_WRITER_ALREADY_ACTIVE')
    return fd


def _validate_runtime(value:dict[str,object],v110_pid:int|None=None)->dict[str,object]:
    if value.get('schema_id')!='V110_RUNTIME_INHERITANCE_V1' or value.get('schema_version')!=1:
        raise ValueError('V110_RUNTIME_INHERITANCE_SCHEMA_MISMATCH')
    if value.get('fixed_head')!=FIXED: raise ValueError('V110_RUNTIME_FIXED_HEAD_MISMATCH')
    if v110_pid is not None and value.get('pid')!=v110_pid: raise ValueError('V110_RUNTIME_PID_MISMATCH')
    for key in ('v110_package_root','upstream_root','closure_root','prepared_root','repo'):
        x=value.get(key)
        if not isinstance(x,str) or not x: raise ValueError('V110_RUNTIME_BINDING_MISSING:'+key)
    return value


def load_or_snapshot_runtime(*,state_root:Path,v110_pid:int)->dict[str,object]:
    state_root=Path(state_root);p=state_root/RUNTIME
    if p.is_file(): return _validate_runtime(load_obj(p),v110_pid)
    value=snapshot_v110_runtime(pid=v110_pid,expected_fixed_head=FIXED)
    _validate_runtime(value,v110_pid);write_once(p,value);return value


def supervisor_iteration(*,runtime:dict[str,object],state_root:Path)->dict[str,object]:
    runtime=_validate_runtime(runtime)
    repo=Path(str(runtime['repo']));assert_fixed_head(repo,FIXED)
    return advance_current_round(
        repo=repo,state_root=Path(state_root),
        closure_root=Path(str(runtime['closure_root'])),
        prepared_root=Path(str(runtime['prepared_root'])),
        upstream_root=Path(str(runtime['upstream_root'])),
        v110_package_root=Path(str(runtime['v110_package_root'])),
    )


def status(state_root:Path)->dict[str,object]:
    root=Path(state_root); runtime=root/RUNTIME; release=root/BLOCKED
    phase='NOT_STARTED'
    if runtime.is_file(): phase='RUNTIME_INHERITED'
    if (root/ADOPT).is_file(): phase='PLANNER_POST_ADOPTED'
    if (root/ROUTE).is_file(): phase='CURRENT_ROUND_ROUTE_BOUND'
    if (root/NO_TRAIN).is_file(): phase='NO_TRAINING_UPDATE_APPLIED'
    if release.is_file():
        r=load_obj(release)
        phase='MAX10_RELEASED' if r.get('full_max10_autonomous_campaign_released') is True else 'AUTONOMY_RELEASE_BLOCKED'
    return {'schema_id':'AUTONOMOUS_CAMPAIGN_STATUS_V1','schema_version':1,'phase':phase,
        'state_root':str(root),'runtime_inherited':runtime.is_file(),'release_gate_present':release.is_file(),
        'routine_human_scientific_decision_count_target':0,'full_max10_autonomous_campaign_released':
        bool(load_obj(release).get('full_max10_autonomous_campaign_released')) if release.is_file() else False}


def run(*,state_root:Path,v110_pid:int,poll:float)->int:
    state_root=Path(state_root);fd=_lock(state_root)
    try:
        runtime=load_or_snapshot_runtime(state_root=state_root,v110_pid=v110_pid)
        last=None
        while True:
            out=supervisor_iteration(runtime=runtime,state_root=state_root)
            phase=str(out.get('phase'))
            if phase!=last:
                print('CAMPAIGN_PHASE='+phase,flush=True);last=phase
            if out.get('fail_closed') is True:
                print('STATUS=FAIL_CLOSED_NO_BLIND_RESEND',flush=True);return 31
            gate=state_root/BLOCKED
            if gate.is_file():
                g=load_obj(gate)
                if g.get('full_max10_autonomous_campaign_released') is True:
                    print('STATUS=FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED',flush=True);return 0
                print('STATUS=AUTONOMY_RELEASE_GATE_BLOCKED',flush=True)
                print('BLOCKERS='+json.dumps(g.get('blockers',[]),sort_keys=True),flush=True)
                print('HUMAN_SCIENTIFIC_DECISION_REQUIRED=false',flush=True)
                return 20
            time.sleep(max(2.0,float(poll)))
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)


def main(argv=None):
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    r=sub.add_parser('run');r.add_argument('--state-root',type=Path,required=True);r.add_argument('--v110-pid',type=int,required=True);r.add_argument('--poll-seconds',type=float,default=10.0)
    s=sub.add_parser('status');s.add_argument('--state-root',type=Path,required=True)
    a=p.parse_args(argv)
    if a.mode=='status':
        for k,v in status(a.state_root).items(): print(f'{k.upper()}={json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else str(v).lower() if isinstance(v,bool) else v}')
        return 0
    return run(state_root=a.state_root,v110_pid=a.v110_pid,poll=a.poll_seconds)

if __name__=='__main__': raise SystemExit(main())
