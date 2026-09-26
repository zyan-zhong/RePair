"""Reuse V197 terminal-receipt handoff, restricted to current L before G."""

from pathlib import Path
import sys,os,signal,time,json,hashlib,subprocess,datetime
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from closure_entry import verify
from launch import write_once
identity=verify();a=json.loads((root/'AUTHORITY.json').read_bytes())
validation=json.loads((root/'SERVER_VALIDATION.json').read_bytes())
assert validation['manifest_sha256']==identity and validation['group_interface_replay_verified']
assert validation['repair_feedback_verified']
assert os.uname().nodename==a['host']
def ref(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
owner=Path(a['owner_root']);previous=a['prior_launch'];pid=previous['pid'];proc=Path('/proc')/str(pid)
assert proc.stat().st_uid==os.getuid()
def argv():return [x.decode() for x in (proc/'cmdline').read_bytes().split(b'\0') if x]
assert argv()==previous['argv']
status_path=owner/'CHAIN_PROGRESS.json';deadline=time.monotonic()+600;stopped=False;proof=None
try:
 while time.monotonic()<deadline:
  status=json.loads(status_path.read_bytes())
  if status.get('round_id')!=a['repair_activation']['round_id']:raise RuntimeError('ROUND_ADVANCED_REBIND_REQUIRED')
  if status.get('stage_id') not in ('L-A0','L-A1'):raise RuntimeError('L_BOUNDARY_PASSED_NO_HANDOFF')
  # The parent writes this only after execute_one has published logical_call.json.
  if status.get('stage_id') not in ('L-A0','L-A1') or status.get('state') not in ('ACCEPTED','SEMANTIC_INVALID','AMBIGUOUS_POST_SEND'):
   time.sleep(.005);continue
  assert argv()==previous['argv'];os.kill(pid,signal.SIGSTOP);stopped=True
  for _ in range(100):
   if (proc/'stat').read_text().split()[2] in ('T','t'):break
   time.sleep(.001)
  else:raise RuntimeError('OWNER_DID_NOT_SUSPEND')
  stable=json.loads(status_path.read_bytes())
  children=(proc/'task'/str(pid)/'children').read_text().strip()
  if stable!=status or children:
   os.kill(pid,signal.SIGCONT);stopped=False;continue
  live=json.loads((owner/'LIVE_STATUS.json').read_bytes());attempt=Path(live['attempt_root'])
  if live['round_id']!=a['repair_activation']['round_id'] or live['stage']!='ANALYZER_PLANNER_CAUSAL_VERIFICATION':
   raise RuntimeError('OWNER_PHASE_CHANGED')
  binding_path=attempt/'CURRENT_ANALYZER_BINDING.json';binding=json.loads(binding_path.read_bytes())
  # Exact runtime roles are declared by the registered native adapter.
  role='local/strong_local_runtime' if status['stage_id'] in ('L-A0','L-A1') else 'group/strong_group_runtime'
  logical_path=Path(binding['output_root'])/role/status['logical_call_id']/'logical_call.json'
  logical=json.loads(logical_path.read_bytes())
  assert logical['logical_call_id']==status['logical_call_id'] and logical['terminal_method_status']==status['state']
  assert logical['round_id']==status['round_id']
  intent=json.loads((attempt/'INTENT.json').read_bytes());assert intent['start']['request_sha256']==a['repair_activation']['request_sha256']
  proof={'schema_id':'REGISTERED_REPAIR_L_BOUNDARY_HANDOFF_V1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'old_launch':previous,'completed_call_ref':ref(logical_path),'stable_terminal_progress':stable,
      'intent_ref':ref(attempt/'INTENT.json'),'binding_ref':ref(binding_path),'entry_manifest_sha256':identity,
      'new_authority_ref':ref(root/'AUTHORITY.json'),'interrupted_provider_requests':0,
      'scientific_jobs_cancelled':0,'old_scientific_results_rewritten':0,'git_operations':0}
  write_once(owner/'runtime_extensions'/identity/'SAFE_HANDOFF.json',proof)
  # SIGTERM is pending before resuming; no next scientific call can start.
  os.kill(pid,signal.SIGTERM);os.kill(pid,signal.SIGCONT);stopped=False
  for _ in range(100):
   if not proc.exists() or (proc/'stat').read_text().split()[2]=='Z':break
   time.sleep(.1)
  else:raise RuntimeError('PRIOR_OWNER_DID_NOT_EXIT')
  run=subprocess.run([a['registered_python'],'-B',str(root/'launch.py')],cwd=root,capture_output=True,text=True,timeout=180)
  result={'safe_handoff':proof,'old_resident_stopped':True,'launch_returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr}
  if run.returncode==0:result['launch']=json.loads(run.stdout.splitlines()[-1])
  write_once(root/'HANDOFF_RECEIPT.json',result);print(json.dumps(result));break
 else:raise RuntimeError('NO_SAFE_BOUNDARY_OBSERVED_OWNER_UNCHANGED')
finally:
 if stopped and proc.exists():os.kill(pid,signal.SIGCONT)
