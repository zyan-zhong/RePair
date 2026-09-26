from pathlib import Path
import os,json,subprocess,uuid
from profile_entry import ROOT,load

def main():
    a,prior,identity,prepared=load()
    from profile_entry import ROOT
    sys_path_base=Path(a['base_source_root'])
    budget_a,budget_prior,budget_id,prepared=prepared
    prior_a,prior_module,prior_id,prepared=prepared
    old_a,old_prior,old_id,prior_prepared=prepared
    old_transport,base,signature,transport_id,base_prepared,scope=prior_prepared
    if os.uname().nodename!=a['host']:raise ValueError('REGISTERED_HOST_REQUIRED')
    previous=a['prior_launch'];proc=Path('/proc')/str(previous['pid'])/'cmdline'
    if proc.exists() and previous['argv'][2].encode() in proc.read_bytes():raise ValueError('PRIOR_RESIDENT_STILL_ACTIVE')
    from entry.campaign_owner import campaign_lock,_write_once
    owner=Path(a['owner_root']);extension=Path(previous['extension_root'])
    with campaign_lock(extension),campaign_lock(owner):
        if (owner/'CAMPAIGN_TERMINAL.json').exists():raise ValueError('CAMPAIGN_ALREADY_TERMINAL')
        claim=owner/'runtime_extensions'/identity/'LAUNCH_CLAIM.json'
        if claim.exists():
            existing=json.loads(claim.read_bytes());receipt=json.loads(Path(existing['receipt_path']).read_bytes())
            p=Path('/proc')/str(receipt['pid'])/'cmdline'
            if p.exists() and receipt['argv'][2].encode() in p.read_bytes():print(json.dumps(receipt));return
            raise ValueError('REGISTERED_LAUNCH_ALREADY_CONSUMED_READ_RECEIPT')
        checked=base.preflight();invocation=uuid.uuid4().hex;out=extension/'launch_receipts'/invocation;out.mkdir(parents=True)
        argv=[a['registered_python'],'-B',str(ROOT/'profile_entry.py'),'--run','--invocation',invocation]
        _write_once(out/'LAUNCH_INTENT.json',{'argv':argv,'trained_parent_manifest_sha256':identity,'preflight':checked})
        _write_once(claim,{'receipt_path':str(out/'LAUNCH_RECEIPT.json'),'argv':argv})
        with (out/'resident.log').open('ab',buffering=0) as stream:
            process=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
        receipt={**previous,'schema_id':'REGISTERED_PLANNER_CONTEXT_RESIDENT_LAUNCHED_V1','pid':process.pid,'argv':argv,
            'log_path':str(out/'resident.log'),'invocation_id':invocation,'invocation_root':str(extension/'invocations'/invocation),
            'trained_parent_manifest_sha256':identity,'provider_success_claimed':False}
        _write_once(out/'LAUNCH_RECEIPT.json',receipt)
    print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
