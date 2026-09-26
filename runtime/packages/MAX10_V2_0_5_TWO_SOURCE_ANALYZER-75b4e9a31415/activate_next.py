"""One pending handoff at a later round's completed Local call; current round untouched."""
from pathlib import Path
import json,os,signal,time,hashlib,datetime,subprocess,fcntl,stat
from parallel_entry import ROOT,verify

def eligible(policy,live,index,chain):
    return (index['round_index']>=policy['activation_round_index']
        and live['round_id']!=policy['current_round_preserved']['round_id']
        and chain.get('round_id')==live['round_id']
        and live.get('stage')=='ANALYZER_PLANNER_CAUSAL_VERIFICATION'
        and chain.get('stage_id') in ('L-A0','L-A1')
        and chain.get('state') in ('ACCEPTED','SEMANTIC_INVALID','AMBIGUOUS_POST_SEND'))

def no_unfinished_writes(proc,allowed):
    # Bounded inspection of the suspended registered process, not asset discovery.
    for fd in (proc/'fd').iterdir():
        if not stat.S_ISREG(fd.stat().st_mode):continue
        info=(proc/'fdinfo'/fd.name).read_text()
        flags=int(next(line.split()[1] for line in info.splitlines() if line.startswith('flags:')),8)
        if flags & os.O_ACCMODE and os.readlink(fd) not in allowed:return False
    return True

def main():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());owner=Path(a['owner_root']);old=a['prior_launch']
    helper_lock=(ROOT/'activation_helper.lock').open('ab');fcntl.flock(helper_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    from parallel_install import checked
    from parallel_launch import write_once
    status=ROOT/'ACTIVATION_STATUS.json';proc=Path('/proc')/str(old['pid']);stopped=False
    def read(path):return json.loads(path.read_bytes())
    def update(state,**fields):
        value={'state':state,'helper_pid':os.getpid(),'owner_pid':old['pid'],'activation_round_index':a['parallel_policy']['activation_round_index'],
            'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**fields}
        tmp=status.with_suffix('.tmp');tmp.write_text(json.dumps(value)+'\n');os.replace(tmp,status)
        cache=ROOT/'git_staging_runtime';cache.mkdir(exist_ok=True)
        with (cache/'ACTIVATION_EVENTS.jsonl').open('ab') as stream:
            stream.write((json.dumps(value,sort_keys=True)+'\n').encode());stream.flush();os.fsync(stream.fileno())
    def matches():return proc.exists() and [x.decode() for x in (proc/'cmdline').read_bytes().split(b'\0') if x]==old['argv']
    def ref(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    validation=read(ROOT/'SERVER_VALIDATION.json')
    if validation['manifest_sha256']!=identity or not validation['native_group_parity_verified']:raise ValueError('SERVER_VALIDATION_REQUIRED')
    update('WAITING_NEXT_ROUND_LOCAL_TERMINAL')
    try:
        while True:
            if (owner/'CAMPAIGN_TERMINAL.json').exists():update('CAMPAIGN_TERMINAL_NO_ACTIVATION');return
            if not matches():update('OWNER_CHANGED_OR_STOPPED_NO_MUTATION');return
            live=read(owner/'LIVE_STATUS.json')
            if live['round_id']==a['parallel_policy']['current_round_preserved']['round_id']:
                time.sleep(2);continue
            attempt=Path(live['attempt_root']);intent_path=attempt/'INTENT.json'
            intent=read(intent_path);request_sha=intent['start']['request_sha256']
            index_path=owner/'request_bindings'/(request_sha+'.json');index=read(index_path)
            request=checked(index['request'])
            if request['request_sha256']!=request_sha or request['round_id']!=live['round_id']:raise ValueError('NEXT_ROUND_REQUEST_INDEX_MISMATCH')
            chain_path=owner/'CHAIN_PROGRESS.json';chain=read(chain_path)
            if not eligible(a['parallel_policy'],live,index,chain):time.sleep(.01 if chain.get('round_id')==live['round_id'] else 1);continue
            if proc.stat().st_uid!=os.getuid():raise ValueError('OWNER_UID_CHANGED')
            os.kill(old['pid'],signal.SIGSTOP);stopped=True
            for _ in range(100):
                if (proc/'stat').read_text().split()[2] in ('T','t'):break
                time.sleep(.001)
            else:raise RuntimeError('OWNER_NOT_SUSPENDED')
            if read(chain_path)!=chain or read(owner/'LIVE_STATUS.json')!=live or (proc/'task'/str(old['pid'])/'children').read_text().strip():
                os.kill(old['pid'],signal.SIGCONT);stopped=False;continue
            binding_path=attempt/'CURRENT_ANALYZER_BINDING.json';binding=read(binding_path)
            allowed={old['log_path'],str(owner/'.campaign_writer.lock'),str(Path(old['extension_root'])/'.campaign_writer.lock'),
                str(Path(binding['output_root'])/'ANALYZER_ADAPTER.lock')}
            allowed.update(validation['handoff_lock_paths'])
            if not no_unfinished_writes(proc,allowed):
                os.kill(old['pid'],signal.SIGCONT);stopped=False;continue
            if checked(binding['refs']['request'])!=request:raise ValueError('NEXT_ROUND_BINDING_CHANGED')
            call=Path(binding['output_root'])/'local/strong_local_runtime'/chain['logical_call_id']/'logical_call.json';logical=read(call)
            if logical['logical_call_id']!=chain['logical_call_id'] or logical['terminal_method_status']!=chain['state'] or logical['round_id']!=live['round_id']:raise ValueError('NEXT_ROUND_TERMINAL_MISMATCH')
            proof={'schema_id':'NEXT_ROUND_TERMINAL_PARALLEL_HANDOFF_V1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'old_launch':old,'completed_call_ref':ref(call),'binding_ref':ref(binding_path),'intent_ref':ref(intent_path),
                'index_ref':ref(index_path),'round_id':live['round_id'],'round_index':index['round_index'],
                'current_round_preserved':a['parallel_policy']['current_round_preserved'],'provider_requests_interrupted':0,
                'scientific_jobs_cancelled':0,'entry_manifest_sha256':identity,'git_mutations':0,'no_unfinished_writable_files':True}
            write_once(ROOT/'SAFE_HANDOFF.json',proof)
            os.kill(old['pid'],signal.SIGTERM);os.kill(old['pid'],signal.SIGCONT);stopped=False
            for _ in range(100):
                if not matches():break
                time.sleep(.1)
            else:raise RuntimeError('PRIOR_OWNER_NOT_EXITED')
            run=subprocess.run([a['registered_python'],'-B',str(ROOT/'parallel_launch.py')],cwd=ROOT,capture_output=True,text=True,timeout=180)
            result={'safe_handoff':proof,'launch_returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr}
            if run.returncode==0:result['launch']=json.loads(run.stdout.splitlines()[-1])
            write_once(ROOT/'HANDOFF_RECEIPT.json',result)
            update('LAUNCHED_WAITING_RUNTIME_CONFIRMATION' if run.returncode==0 else 'LAUNCH_FAILED',handoff_ref=ref(ROOT/'HANDOFF_RECEIPT.json'))
            if run.returncode==0:
                launched=result['launch'];new_proc=Path('/proc')/str(launched['pid'])/'cmdline'
                while new_proc.exists() and [x.decode() for x in new_proc.read_bytes().split(b'\0') if x]==launched['argv']:
                    current=read(owner/'LIVE_STATUS.json');parallel=owner/'ANALYZER_PARALLEL_PROGRESS.json'
                    if current.get('pid')==launched['pid'] and current.get('parallel_manifest_sha256')==identity and parallel.is_file():
                        observed=read(parallel)
                        if observed.get('coordinator_pid')==launched['pid'] and observed.get('round_id')==current['round_id']:
                            update('ACTIVATED',handoff_ref=ref(ROOT/'HANDOFF_RECEIPT.json'),runtime_progress_ref=ref(parallel));return
                    time.sleep(1)
                update('LAUNCH_EXITED_BEFORE_PARALLEL_CONFIRMATION',handoff_ref=ref(ROOT/'HANDOFF_RECEIPT.json'))
            return
    except BaseException as exc:
        update('ACTIVATION_FAILED_OWNER_PRESERVED' if not (ROOT/'SAFE_HANDOFF.json').exists() else 'ACTIVATION_FAILED_AFTER_HANDOFF',error=type(exc).__name__+':'+str(exc))
        raise
    finally:
        if stopped and matches():os.kill(old['pid'],signal.SIGCONT)

if __name__=='__main__':main()
