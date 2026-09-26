from pathlib import Path
import json,subprocess,uuid,os
from resume_entry import ROOT,load

def main():
    a,base,prior,identity,prepared,scope=load()
    if os.uname().nodename!=a['host']:raise ValueError('REGISTERED_RESIDENT_HOST_REQUIRED')
    old=a['prior_launch'];proc=Path('/proc')/str(old['pid'])/'cmdline'
    if proc.exists() and all(x.encode() in proc.read_bytes() for x in old['argv'][2:3]):raise ValueError('PRIOR_RESIDENT_STILL_ACTIVE')
    checked=base.preflight();authority,values,deployment,original,generation,link,target=prepared
    from entry.campaign_owner import campaign_lock,_write_once
    owner=Path(a['owner_root']);extension=owner/'runtime_extensions'/original
    with campaign_lock(Path(deployment['formal_state_root'])/'campaign_owner'):
        if (owner/'CAMPAIGN_TERMINAL.json').exists():raise ValueError('CAMPAIGN_ALREADY_TERMINAL')
        invocation=uuid.uuid4().hex;out=extension/'launch_receipts'/invocation;out.mkdir(parents=True)
        argv=[a['registered_python'],'-B',str(ROOT/'resume_entry.py'),'--run','--invocation',invocation]
        _write_once(out/'LAUNCH_INTENT.json',{'argv':argv,'transport_entry_manifest_sha256':identity,'preflight':checked})
    with (out/'resident.log').open('ab',buffering=0) as stream:
        process=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    receipt={'schema_id':'REGISTERED_TRANSPORT_RESIDENT_LAUNCHED_V1','pid':process.pid,'argv':argv,'owner_root':str(owner),
        'log_path':str(out/'resident.log'),'runtime_root':str(generation),'extension_root':str(extension),'extension_sha256':original,
        'transport_entry_manifest_sha256':identity,'invocation_id':invocation,'invocation_root':str(extension/'invocations'/invocation),
        'base_source_sha256':deployment['entry_source_sha256'],'host':a['host'],'provider_success_claimed':False}
    _write_once(out/'LAUNCH_RECEIPT.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
