from pathlib import Path
from unittest.mock import patch
import json,sys,uuid,argparse
from seed_recovery import verify_root,read,ref,materialize,audit_and_capture,installed
ROOT=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');args=p.parse_args()
 identity=ref(ROOT/'PACKAGE_FILES.sha256')['sha256'];verify_root(ROOT,identity)
 a=json.loads((ROOT/'RECOVERY_AUTHORITY.json').read_bytes());original=a['validation_package']
 verify_root(original['root'],original['manifest_sha256'])
 verify_root(a['promotion_package']['root'],a['promotion_package']['manifest_sha256'])
 sys.path.insert(0,original['root']);import entry_v208
 authority=read(ref(Path(original['root'])/'AUTHORITY.json'));pre=authority['predecessor']
 if not args.preflight:entry_v208.progress(authority['experiment_root'],'BOOTSTRAPPING_SEED_RECOVERY',new_model_episodes=0)
 verify_root(pre['root'],pre['manifest_sha256']);sys.path.insert(0,pre['root'])
 prior=entry_v208.load_module('_seed_recovery_registered_context',Path(pre['root'])/'context_entry.py');prepared=prior.load()
 import entry.main as native_main
 def current(argv=None):
  import entry.registration as registration
  if args.preflight:
   deployment=registration.build_deployment(Path(authority['native_entry_root']),entry_source_sha256=authority['native_entry_manifest_sha256'])
   amendment=materialize(a,deployment);audit=audit_and_capture(a,amendment,capture=False)
   print(json.dumps({'status':'FULL_SINGLE_SEED_AUDIT_PASS','audit_ref':audit,'amendment_ref':amendment,'new_model_episodes':0}),flush=True);return 0
  with installed(a):return entry_v208.execute(authority,original['manifest_sha256'],preflight=False)
 try:
  with patch.object(prior,'load',lambda:prepared),patch.object(native_main,'main',current):return prior.run(uuid.uuid4().hex)
 except Exception as exc:
  if not args.preflight:entry_v208.progress(authority['experiment_root'],'STOPPED',error_type=type(exc).__name__,error=str(exc))
  raise
if __name__=='__main__':raise SystemExit(main())
