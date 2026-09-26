"""Reuse V194 full-cell cutover and V211 lifecycle; no model or GPU rerun."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import hashlib,importlib.util,json,sys,inspect
ROOT=Path(__file__).resolve().parent
def ref(p):return {'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def read(r):
 b=Path(r['path']).read_bytes()
 if hashlib.sha256(b).hexdigest()!=r.get('sha256',r.get('file_sha256')):raise ValueError('REGISTERED_SOURCE_CHANGED')
 return json.loads(b)
def verify_root(root,expected):
 p=Path(root);raw=(p/'PACKAGE_FILES.sha256').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('REGISTERED_MANIFEST_CHANGED')
 for line in raw.decode().splitlines():
  h,n=line.split(maxsplit=1);q=p/n
  if not q.resolve().is_relative_to(p.resolve()) or ref(q)['sha256']!=h:raise ValueError('REGISTERED_MEMBER_CHANGED:'+n)

def materialize(a,deployment):
 from continuity_binding.api import read_ref,write_once
 from offoff_binding.native import Native
 from offoff_binding.materialize import materialize as native_materialize,prepare
 import promotion_entry
 plan=read(a['source_parallel_ref']);old=read(plan['binding_ref']);protocol=read(old['input_refs']['protocol_ref'])
 v194=read(a['promotion_authority_ref']);seeds=v194['future_select_replicate_seeds']
 if len(seeds)!=1 or seeds!=protocol['replicate_seeds'][:1]:raise ValueError('ONLY_PREVIOUSLY_REGISTERED_SINGLE_SEED')
 effective=promotion_entry.future_deployment(deployment,v194);rule_ref=effective['promotion_rule_ref'];rule=read(rule_ref)
 if rule['replicate_seeds']!=seeds:raise ValueError('EFFECTIVE_SEED_DRIFT')
 sink=Path(a['recovery_root'])
 disclosure=write_once(sink/'COVERAGE_CORRECTION.json',{'schema_id':'REGISTERED_SELECT_WIRING_CORRECTION_V1',
  'original_protocol_ref':old['input_refs']['protocol_ref'],'effective_rule_ref':rule_ref,
  'prior_user_authority_ref':a['promotion_authority_ref'],'stop_receipt_ref':a['stop_receipt_ref'],
  'selected_seeds':seeds,'coverage_corrected_after_episode_publication':True,
  'selection_reason':'Restore prior registered seed; no outcome-based seed selection.',
  'goal_tie_rule_previously_registered':True,'original_episode_identities_preserved':True,'new_model_episodes':0})
 protocol_ref=write_once(sink/'CURRENT_OFFOFF_PROTOCOL.json',{**protocol,'replicate_seeds':seeds,
  'promotion_rule_ref':rule_ref,'coverage_correction_ref':disclosure})
 sources={r['path']:r for r in old['source_refs']}
 for r in effective['offoff_source_registration']['source_refs']:sources[r['path']]=r
 for name in ('current_cutover.py','parent_cache.py'):
  r=ref(promotion_entry.ROOT/name);sources[r['path']]=r
 native=Native.load(old['native_repo_root'],list(sources.values()))
 binding_ref=native_materialize(native=native,**{**old['input_refs'],'protocol_ref':protocol_ref},sink=sink/'binding')
 amendment={'schema_id':'REGISTERED_CURRENT_SELECT_CUTOVER_V1','source_parallel_ref':a['source_parallel_ref'],
  'source_binding_ref':plan['binding_ref'],'binding_ref':binding_ref,'request_sha256':old['request_sha256'],
  'selected_seeds':seeds,'all_selected_tasks_required':True,'original_episode_identities_preserved':True,
  'partial_other_seeds_excluded':True,'criterion_changed_from_prior_user_authority':False,
  'coverage_amended_after_episode_publication':True,'new_model_episodes_required':0,'human_scientific_verdict_count':0,
  'coverage_correction_ref':disclosure}
 return write_once(sink/'REGISTERED_CURRENT_SELECT_CUTOVER.json',amendment)

def native_finalize(amendment_ref):
 """Original physical-cell audits and arithmetic; existing goal writer adds tie metric."""
 import current_cutover,offoff_binding.execute as execution
 source=inspect.getsource(current_cutover.finalize)
 old='from continuity_binding.api import read_ref,write_once'
 if source.count(old)!=1:raise ValueError('CUTOVER_IMPORT_ANCHOR_CHANGED')
 # V194's goal writer verifies the private terminal captures and adds the
 # complete metric grid before its unchanged promotion producer is invoked.
 source=source.replace(old,'from continuity_binding.api import read_ref\n    from offoff_binding.execute import write_once')
 namespace=dict(vars(current_cutover));exec(compile(source,current_cutover.__file__,'exec'),namespace)
 return namespace['finalize'](amendment_ref)

def audit_and_capture(a,amendment_ref,*,capture):
 from continuity_binding.api import read_ref,write_once
 from offoff_binding.native import Native
 from offoff_binding.materialize import prepare
 from offoff_binding.execute import _audit_one
 from pchsi.evaluation.select_result_audit import derive_expected_select_cells_from_master_schedules
 from parent_replay import replay
 from goal_capture import validate_capture
 from parent_cache import equivalent,contract
 amendment=read(amendment_ref);plan=read(amendment['source_parallel_ref']);old=read(amendment['source_binding_ref']);new=read(amendment['binding_ref'])
 native=Native.load(old['native_repo_root'],old['source_refs']);source=prepare(native=native,**old['input_refs'])
 current=prepare(native=Native.load(new['native_repo_root'],new['source_refs']),**new['input_refs'])
 rule=read(current['protocol']['promotion_rule_ref']);refs=rule['goal_source_refs']
 for arm in ('parent','candidate'):equivalent(contract(source,arm),contract(current,arm))
 live,audit,_,_,_,loader=native.runners();an=audit.load_native(native.root)
 expected=derive_expected_select_cells_from_master_schedules(schedules={k:b[2] for k,b in source['bundles'].items()},authorized_schedule_sha256={k:b[5] for k,b in source['bundles'].items()})
 expected={(e.schedule_name,e.condition_cell_id):e for e in expected}
 roots={n:s['execution_root'] for s in plan['shards'] for n in s['ordinals']};rows=[];receipt_cache={}
 for arm,bundle in current['bundles'].items():
  ordinals={c.condition_cell_id:n for n,c in enumerate(source['bundles'][arm][2].cells)}
  for n,cell in enumerate(bundle[2].cells):
   oldn=ordinals[cell.condition_cell_id];root=Path(roots[oldn])/arm
   if str(root) not in receipt_cache:
    rr=live.load_receipts(root/'cell_receipts.jsonl');ids=[r['condition_cell_id'] for r in rr]
    if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_PUBLISHED_CELL')
    receipt_cache[str(root)]=dict(zip(ids,rr))
   row=receipt_cache[str(root)][cell.condition_cell_id];eroot=root/'evaluator_run'
   loaded=loader.load_attempt_directory_v1(eroot/'attempts'/row['execution_attempt_id'])
   _audit_one(audit=audit,native_audit=an,loaded=loaded,row=row,expected=expected[(arm,cell.condition_cell_id)],
    bundle=source['bundles'][arm],protocol=source['protocol'],infra=source['infra'],access=source['access'],root=eroot)
   rows.append({'arm':arm,'ordinal':n,'source_ordinal':oldn,'root':str(root),'receipt':row})
   if capture:
    dest=root/'restricted_goal_progress'/cell.condition_cell_id;cp=dest/'TERMINAL_CAPTURE.json'
    if not cp.exists():replay(loaded,source['access'].records[loaded.episode_artifact.task_index],cp,refs)
    validate_capture(cp,loaded.episode_artifact,row,refs)
    write_once(dest/'BOUND_GOAL_METRIC.json',{'schema_id':'RESTRICTED_BOUND_GOAL_METRIC_V1','condition_cell_id':cell.condition_cell_id,
     'execution_attempt_id':row['execution_attempt_id'],'attempt_bundle_sha256':row['attempt_bundle_sha256'],'capture_ref':ref(cp)})
    progress=Path(a['recovery_root'])/'GOAL_RECOVERY_PROGRESS.json'
    value={'stage':'GOAL_METRIC_RECOVERY','completed':len(rows),'total':2*new['paired_cell_count'],'policy_calls':0,'new_model_episodes':0}
    tmp=progress.with_suffix('.tmp');tmp.write_text(json.dumps(value)+'\n');tmp.replace(progress)
 result={'schema_id':'REGISTERED_COMPLETE_FIXED_SEED_AUDIT_V1','amendment_ref':amendment_ref,
  'audited_cells':len(rows),'selected_seeds':amendment['selected_seeds'],'rows':rows,'new_model_episodes':0,'goal_metrics_complete':capture}
 return write_once(Path(a['recovery_root'])/('FULL_METRIC_AUDIT.json' if capture else 'FULL_CELL_AUDIT.json'),result)

@contextmanager
def installed(a):
 import one_validation,entry.offoff_job as job,offoff_binding.execute as execution,entry_v208
 original=one_validation.run_validation;original_validate=execution.validate_completed_offoff_terminal
 def finalize(ref_):return native_finalize(ref_)
 def validate(terminal_ref):
  terminal=read(terminal_ref);summary=read(terminal['summary_ref']);audit=read(summary['identity_audit_ref'])
  if audit.get('amendment_ref',{}).get('path')!=str(Path(a['recovery_root'])/'REGISTERED_CURRENT_SELECT_CUTOVER.json'):
   return original_validate(terminal_ref)
  if finalize(audit['amendment_ref'])!=terminal_ref:raise ValueError('RECOVERED_TERMINAL_REPLAY_MISMATCH')
  return True
 def run(**kwargs):
  root=Path(kwargs['experiment_root']);authority=kwargs['authority'];native=kwargs['native']
  def recover(*,stage,inputs,stage_intent_ref,experiment_root):
   if stage!='OFFOFF':raise ValueError('ONLY_EXACT_OFFOFF_RECOVERY_AUTHORIZED:'+stage)
   if read(stage_intent_ref)['inputs']!=inputs:raise ValueError('RECOVERY_INPUTS_CHANGED')
   amendment=materialize(a,authority['deployment'])
   entry_v208.progress(root,'GOAL_METRIC_RECOVERY',selected_seed=read(amendment)['selected_seeds'],new_model_episodes=0)
   audit=audit_and_capture(a,amendment,capture=True)
   terminal=finalize(amendment)
   def jobs(**kw):
    if kw['parallel_ref']!=a['source_parallel_ref']:raise ValueError('RECOVERY_PARALLEL_MISMATCH')
    return terminal
   with patch.object(job,'execute_current_offoff_jobs',jobs):
    output=native.offoff(start=read(authority['source_request_ref']),current_inputs_ref=authority['current_inputs_ref'],
     trained=inputs['trained'],output_root=root/'offoff',deployment=authority['deployment'])
   proof=one_validation.write_once(Path(a['recovery_root'])/'OFFOFF_RECOVERY_PROOF.json',
    {'status':'VERIFIED_NATIVE_STAGE_RECOVERY','stage':stage,'intent_ref':stage_intent_ref,'audit_ref':audit,
     'terminal_ref':terminal,'amendment_ref':amendment,'new_model_episodes':0,'provider_calls':0})
   return {'output':output,'native_recovery_ref':proof}
  return original(**kwargs,recover_callable=recover)
 with patch.object(one_validation,'run_validation',run),patch.object(execution,'validate_completed_offoff_terminal',validate):yield
