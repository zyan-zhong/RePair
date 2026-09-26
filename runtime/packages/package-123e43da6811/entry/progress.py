"""Small observational status view; never an authority for scientific decisions."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def update(root, **fields):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    target=root/'LIVE_STATUS.json'
    value=json.loads(target.read_bytes()) if target.is_file() else {}
    value.update(fields, schema_id='FORMAL_OBSERVATIONAL_PROGRESS_V1',
        updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        host=socket.gethostname(),pid=os.getpid(),scientific_authority=False)
    fd,name=tempfile.mkstemp(prefix='.progress.',dir=root)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as stream:
            json.dump(value,stream,ensure_ascii=False,sort_keys=True);stream.write('\n')
        os.replace(name,target)
    finally:
        if os.path.exists(name):os.unlink(name)


def read_status(root):
    root=Path(root);path=root/'LIVE_STATUS.json'
    if not path.is_file():return {'stage':'NOT_STARTED','owner_root':str(root)}
    value=json.loads(path.read_bytes());value['owner_root']=str(root)
    manifest=value.get('rollout_manifest_ref')
    if manifest:
        path=Path(manifest['path']);raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=manifest['sha256']:
            raise ValueError('STATUS_MANIFEST_CHANGED')
        m=json.loads(raw);plan_path=Path(m['shard_plan_path']);raw=plan_path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=m['shard_plan_sha256']:
            raise ValueError('STATUS_PLAN_CHANGED')
        plan=json.loads(raw);counts={'completed':0,'success':0,'failure':0,'invalid':0}
        for n in range(plan['shard_count']):
            p=Path(m['root'])/'shards'/f'{n:04d}'/'LIVE_STATUS.json'
            if p.is_file():
                progress=json.loads(p.read_bytes())
                for key in counts:counts[key]+=progress.get(key,0)
        value['rollout']={**counts,'scheduled':plan['total_schedule_count']}
        sub=Path(m['root'])/'SUBMISSION_RECEIPT.json'
        if sub.is_file():
            value['rollout_job_id']=json.loads(sub.read_bytes())['array_job_id']
    return value


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--interval',type=float,default=5)
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    if args.interval<=0:parser.error('interval must be positive')
    package=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(package))
    from entry.preflight import verify_package
    identity,_=verify_package(package)
    proof=json.loads((package/'authority/POST_SUBMIT_SOURCE_RECOVERY_V1.json').read_bytes())
    root=Path(proof['predecessor_owner_root'])/'source_recoveries'/identity
    while True:
        value=read_status(root)
        job=value.get('rollout_job_id')
        if job and str(job).isdigit():
            try:
                cp=subprocess.run(['squeue','--noheader','--array','--jobs',job,'--format','%i|%T|%R'],
                    capture_output=True,text=True,timeout=10)
                value['queue']=cp.stdout.strip() or 'No active rollout job'
            except (OSError,subprocess.TimeoutExpired):value['queue']='Query temporarily unavailable'
        if args.json:print(json.dumps(value,ensure_ascii=False),flush=True)
        else:
            if args.watch and sys.stdout.isatty():print('\033[2J\033[H',end='')
            print('Formal Max-10 | stage:',value['stage'])
            print('Valid rounds:',value.get('valid_rounds',0),'/',value.get('max_rounds','?'),
                  '| invalid attempts:',value.get('invalid_attempts',0))
            print('Round:',value.get('round_id','pending'),'| outcome:',value.get('last_outcome','pending'))
            if value.get('rollout'):
                r=value['rollout'];print('Rollout:',r['completed'],'/',r['scheduled'],
                    '| success:',r['success'],'failure:',r['failure'],'invalid:',r['invalid'])
            print(value.get('queue',''))
            print('Updated:',value.get('updated_utc'),'| resident:',value.get('host'),value.get('pid'))
            if value.get('error'):print('Stop:',value['error'])
            print('Evidence:',root,flush=True)
        if not args.watch:break
        time.sleep(args.interval)


if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:pass
