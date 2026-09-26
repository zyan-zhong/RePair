from pathlib import Path
import json,os,subprocess,fcntl,datetime
from parallel_entry import ROOT,verify

def main():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    if os.uname().nodename!=a['host']:raise ValueError('REGISTERED_HOST_REQUIRED')
    validation=json.loads((ROOT/'SERVER_VALIDATION.json').read_bytes())
    if validation['manifest_sha256']!=identity or not validation['native_local_parity_verified'] or not validation['native_group_parity_verified']:raise ValueError('SERVER_VALIDATION_REQUIRED')
    from parallel_launch import write_once
    with (ROOT/'activation.lock').open('ab') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        receipt=ROOT/'ACTIVATION_REGISTRATION.json'
        if receipt.exists():print(receipt.read_text());return
        args=[a['registered_python'],'-u','-B',str(ROOT/'activate_next.py')]
        intent=ROOT/'ACTIVATION_LAUNCH_INTENT.json'
        if intent.exists():raise ValueError('ACTIVATION_INTENT_WITHOUT_RECEIPT_NO_DUPLICATE_LAUNCH')
        write_once(intent,{'argv':args,'manifest_sha256':identity})
        with (ROOT/'activation.log').open('ab',buffering=0) as log:
            child=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
        value={'schema_id':'REGISTERED_PENDING_ANALYZER_CONCURRENCY_V1','registered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'helper_pid':child.pid,'host':a['host'],'argv':args,'manifest_sha256':identity,'entry_root':str(ROOT),
            'current_round_unchanged':True,'activation_round_index':a['parallel_policy']['activation_round_index'],
            'policy':a['parallel_policy'],'active_parallelism_claimed':False,'git_mutation_count':0}
        write_once(receipt,value);print(json.dumps(value))
if __name__=='__main__':main()
