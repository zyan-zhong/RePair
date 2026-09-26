from pathlib import Path
import json,subprocess,uuid
from signature_entry import ROOT,load
def main():
    a,base,identity=load();checked=base.preflight();authority,values,deployment,original,generation,link,target=base.prepare()
    from entry.campaign_owner import campaign_lock,_write_once
    owner=Path(authority['owner_root']);extension=owner/'runtime_extensions'/original
    with campaign_lock(Path(deployment['formal_state_root'])/'campaign_owner'):
        if (owner/'CAMPAIGN_TERMINAL.json').exists():raise ValueError('CAMPAIGN_ALREADY_TERMINAL')
        invocation=uuid.uuid4().hex;out=extension/'launch_receipts'/invocation;out.mkdir(parents=True)
        argv=[authority['registered_python'],'-B',str(ROOT/'signature_entry.py'),'--run','--invocation',invocation]
        _write_once(out/'LAUNCH_INTENT.json',{'argv':argv,'signature_overlay_manifest_sha256':identity,'original_manifest_sha256':original,'preflight':checked})
    with (out/'resident.log').open('ab',buffering=0) as stream:
        process=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    receipt={'schema_id':'REGISTERED_RUNTIME_EXTENSION_RESIDENT_LAUNCHED_V1','pid':process.pid,'argv':argv,'owner_root':str(owner),
        'log_path':str(out/'resident.log'),'runtime_root':str(generation),'extension_root':str(extension),'extension_sha256':original,
        'signature_overlay_manifest_sha256':identity,'invocation_id':invocation,'invocation_root':str(extension/'invocations'/invocation),
        'base_source_sha256':deployment['entry_source_sha256'],'new_provider_budget':0}
    _write_once(out/'LAUNCH_RECEIPT.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
