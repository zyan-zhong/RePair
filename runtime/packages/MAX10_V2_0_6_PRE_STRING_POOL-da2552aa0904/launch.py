from pathlib import Path
from contextlib import contextmanager
import os,json,hashlib,subprocess,uuid,signal,time,fcntl,datetime
from context_entry import ROOT,verify,checked

def write_once(path,value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode();path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('LAUNCH_RECEIPT_CONFLICT')
        return
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())

@contextmanager
def lock(root):
    fd=os.open(root/'.campaign_writer.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
    finally:os.close(fd)

def main():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    validation=json.loads((ROOT/'SERVER_VALIDATION.json').read_bytes())
    if validation['manifest_sha256']!=identity or not validation['registered_completed_analyzer_assets_verified'] or not validation['native_sender_identity_verified']:raise ValueError('SERVER_VALIDATION_REQUIRED')
    if os.uname().nodename!=a['host']:raise ValueError('REGISTERED_HOST_REQUIRED')
    owner=Path(a['owner_root']);old=a['prior_launch'];extension=Path(old['extension_root'])
    proc=Path('/proc')/str(old['pid'])/'cmdline'
    def matches():return proc.exists() and [x.decode() for x in proc.read_bytes().split(b'\0') if x]==old['argv']
    before=json.loads((owner/'LIVE_STATUS.json').read_bytes());interrupted=False
    if matches():raise ValueError('STOPPED_OWNER_REQUIRED')
    checked(a['context_recovery_binding_ref']);stop=checked(a['context_recovery_stop_ref'])
    if stop['message']!='PRE_REGISTERED_CONTEXT_BUDGET_EXCEEDED_NO_SEND' or before['pid']!=old['pid']:raise ValueError('RECOVERY_STOP_MISMATCH')
    with lock(extension),lock(owner):
        if (owner/'CAMPAIGN_TERMINAL.json').exists():raise ValueError('CAMPAIGN_ALREADY_TERMINAL')
        claim=owner/'runtime_extensions'/identity/'LAUNCH_CLAIM.json'
        if claim.exists():
            receipt=json.loads(Path(json.loads(claim.read_bytes())['receipt_path']).read_bytes())
            p=Path('/proc')/str(receipt['pid'])/'cmdline'
            if p.exists() and [x.decode() for x in p.read_bytes().split(b'\0') if x]==receipt['argv']:print(json.dumps(receipt));return
            raise ValueError('LAUNCH_ALREADY_CONSUMED_READ_STOP_RECEIPT')
        invocation=uuid.uuid4().hex;out=extension/'launch_receipts'/invocation
        argv=[a['registered_python'],'-B',str(ROOT/'context_entry.py'),'--invocation',invocation]
        write_once(out/'LAUNCH_INTENT.json',{'argv':argv,'closed_history_manifest_sha256':identity,
            'previous_pid':old['pid'],'previous_startup_interrupted':interrupted,'previous_live':before,
            'provider_requests_interrupted':0,'scientific_jobs_cancelled':0})
        write_once(claim,{'receipt_path':str(out/'LAUNCH_RECEIPT.json'),'argv':argv})
        with (out/'resident.log').open('ab',buffering=0) as stream:
            child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
        receipt={**old,'pid':child.pid,'argv':argv,'log_path':str(out/'resident.log'),'invocation_id':invocation,
            'invocation_root':str(extension/'invocations'/invocation),'closed_history_manifest_sha256':old['closed_history_manifest_sha256'],
            'closed_history_entry_root':old['closed_history_entry_root'],'pre_pool_entry_root':str(ROOT),'pre_pool_manifest_sha256':identity,'launched_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scientific_progress_claimed':False}
        write_once(out/'LAUNCH_RECEIPT.json',receipt)
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
