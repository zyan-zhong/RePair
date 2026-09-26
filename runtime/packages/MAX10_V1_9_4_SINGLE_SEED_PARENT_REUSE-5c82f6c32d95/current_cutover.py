"""Explicit current-round coverage amendment; audit already published fixed-seed cells."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import copy,importlib.util

def materialize(a):
    from promotion_entry import ROOT
    from parent_cache import ref
    from continuity_binding.api import read_ref,write_once
    from offoff_binding.native import Native
    from offoff_binding.materialize import prepare,materialize as native_materialize
    plan=read_ref(a['current_select_parallel_ref']);old=read_ref(plan['binding_ref'])
    native=Native.load(old['native_repo_root'],old['source_refs']);context=prepare(native=native,**old['input_refs'])
    protocol=context['protocol'];oldrule=read_ref(protocol['promotion_rule_ref']);seeds=a['future_select_replicate_seeds']
    if len(seeds)!=1 or seeds!=protocol['replicate_seeds'][:1]:raise ValueError('CUTOVER_ONLY_REGISTERED_FIRST_SEED')
    excluded=a['promotion_excluded_request_ref'];excluded=read_ref({'path':excluded['path'],'sha256':excluded.get('sha256',excluded.get('file_sha256'))})
    if old['request_sha256']!=excluded['request_sha256']:raise ValueError('CUTOVER_CURRENT_REQUEST_CHANGED')
    sink=ROOT/'runtime/current_select_cutover';source=ref(ROOT/'current_cutover.py')
    oldsource=next(r for r in old['source_refs'] if r['sha256']==oldrule['decision_producer']['sha256'])
    rule={**oldrule,'schema_id':'REGISTERED_SELECT_COVERAGE_AMENDMENT_RULE_V1',
        'replicate_seeds':seeds,'decision_rule_id':oldrule['decision_rule_id']+'-FIXED-SEED-COVERAGE-AMENDMENT',
        'frozen_before_outcomes':False,'criterion_frozen_before_outcomes':True,'coverage_amended_after_episode_publication':True,
        'coverage_selection_reason':'User chose one fixed paired seed to reduce evaluation cost; first registered seed already complete; no outcome-based seed selection.',
        'original_rule_ref':protocol['promotion_rule_ref'],'original_decider_ref':oldsource,
        'decision_producer':{'source_ref':source,'entrypoint':'decide'}}
    rule_ref=write_once(sink/'COVERAGE_AMENDMENT_RULE.json',rule)
    protocol_ref=write_once(sink/'CURRENT_OFFOFF_PROTOCOL.json',{**protocol,'replicate_seeds':seeds,'promotion_rule_ref':rule_ref,
        'coverage_amendment_ref':a['current_select_parallel_ref'],'coverage_amended_after_episode_publication':True})
    sources=old['source_refs']+[source,ref(ROOT/'parent_cache.py')];native=Native.load(old['native_repo_root'],sources)
    binding_ref=native_materialize(native=native,**{**old['input_refs'],'protocol_ref':protocol_ref},sink=sink/'binding')
    amendment=write_once(sink/'REGISTERED_CURRENT_SELECT_CUTOVER.json',{'schema_id':'REGISTERED_CURRENT_SELECT_CUTOVER_V1',
        'source_parallel_ref':a['current_select_parallel_ref'],'source_binding_ref':plan['binding_ref'],'binding_ref':binding_ref,
        'request_sha256':old['request_sha256'],'selected_seeds':seeds,'all_selected_tasks_required':True,
        'original_episode_identities_preserved':True,'partial_other_seeds_excluded':True,'criterion_changed':False,
        'coverage_amended_after_episode_publication':True,'new_model_episodes_required':0,'human_scientific_verdict_count':0})
    return amendment

def decide(*,frozen_rule,aggregate):
    from continuity_binding.api import read_ref,read_bytes_ref
    rule=frozen_rule
    if rule['schema_id']!='REGISTERED_SELECT_COVERAGE_AMENDMENT_RULE_V1' or rule['frozen_before_outcomes'] is not False or rule['coverage_amended_after_episode_publication'] is not True or rule['criterion_frozen_before_outcomes'] is not True:raise ValueError('CUTOVER_RULE_DISCLOSURE_REQUIRED')
    old=read_ref(rule['original_rule_ref']);seeds=rule['replicate_seeds']
    if len(seeds)!=1 or seeds!=old['replicate_seeds'][:1]:raise ValueError('CUTOVER_SEED_SELECTION')
    source=rule['original_decider_ref'];read_bytes_ref(source)
    spec=importlib.util.spec_from_file_location('_cutover_original_strict_success',source['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Original strict criterion and all numerical/integrity checks; the persisted
    # amendment above explicitly discloses that coverage was changed after execution.
    numerical_rule={**old,'replicate_seeds':seeds,'decision_rule_id':rule['decision_rule_id']}
    return module.decide(frozen_rule=numerical_rule,aggregate=aggregate)

def finalize(amendment_ref):
    from continuity_binding.api import read_ref,write_once
    from offoff_binding.native import Native
    from offoff_binding.materialize import prepare
    from offoff_binding.execute import _audit_one,freeze_registered_promotion
    from pchsi.evaluation.select_result_audit import derive_expected_select_cells_from_master_schedules
    a=read_ref(amendment_ref);plan=read_ref(a['source_parallel_ref']);source_binding=read_ref(a['source_binding_ref']);binding=read_ref(a['binding_ref'])
    if plan['binding_ref']!=a['source_binding_ref']:raise ValueError('CUTOVER_PLAN_BINDING')
    native=Native.load(source_binding['native_repo_root'],source_binding['source_refs']);source=prepare(native=native,**source_binding['input_refs'])
    current_native=Native.load(binding['native_repo_root'],binding['source_refs']);current=prepare(native=current_native,**binding['input_refs'])
    from parent_cache import ref
    for name in ('current_cutover.py','parent_cache.py'):
        dependency=ref(Path(__file__).with_name(name))
        if current_native.sources.get(dependency['path'])!=dependency:raise ValueError('CUTOVER_IMPLEMENTATION_DEPENDENCY_CHANGED')
    from parent_cache import equivalent,contract
    for arm in ('parent','candidate'):equivalent(contract(source,arm),contract(current,arm))
    if source['start']!=current['start'] or current['start']['request_sha256']!=a['request_sha256']:raise ValueError('CUTOVER_ROUND_IDENTITY')
    live,audit,aggregate,_,_,loader=native.runners();audit_native=audit.load_native(native.root)
    expected=derive_expected_select_cells_from_master_schedules(schedules={k:b[2] for k,b in source['bundles'].items()},authorized_schedule_sha256={k:b[5] for k,b in source['bundles'].items()})
    expected={(e.schedule_name,e.condition_cell_id):e for e in expected}
    source_ordinals={c.condition_cell_id:n for arm,b in source['bundles'].items() for n,c in enumerate(b[2].cells)}
    roots={n:s['execution_root'] for s in plan['shards'] for n in s['ordinals']}
    if sorted(roots)!=list(range(source_binding['paired_cell_count'])):raise ValueError('CUTOVER_SOURCE_ORDINAL_GRID')
    receipts={};rows={arm:[] for arm in ('parent','candidate')};audits=[];current_roots=[]
    for ordinal in range(binding['paired_cell_count']):
        for arm,bundle in current['bundles'].items():
            cell=bundle[2].cells[ordinal];source_ordinal=source_ordinals[cell.condition_cell_id];root=Path(roots[source_ordinal])/arm;evaluator=root/'evaluator_run'
            if str(root) not in receipts:
                values=live.load_receipts(root/'cell_receipts.jsonl');ids=[r['condition_cell_id'] for r in values]
                if len(ids)!=len(set(ids)):raise ValueError('CUTOVER_DUPLICATE_SOURCE_CELL')
                receipts[str(root)]=dict(zip(ids,values))
            row=receipts[str(root)][cell.condition_cell_id];loaded=loader.load_attempt_directory_v1(evaluator/'attempts'/row['execution_attempt_id'])
            metadata=_audit_one(audit=audit,native_audit=audit_native,loaded=loaded,row=row,expected=expected[(arm,cell.condition_cell_id)],bundle=source['bundles'][arm],protocol=source['protocol'],infra=source['infra'],access=source['access'],root=evaluator)
            rows[arm].append(row);audits.append({'label':arm,'ordinal':ordinal,'source_ordinal':source_ordinal,
                'execution_attempt_id':row['execution_attempt_id'],'attempt_bundle_sha256':row['attempt_bundle_sha256'],**metadata})
            if arm=='parent':current_roots.append(roots[source_ordinal])
    for arm,b in current['bundles'].items():audit.check_receipt_grid(rows[arm],[c.to_dict() for c in b[2].cells],condition_id=b[0].policy_condition_id)
    paired=aggregate(parent_receipts=rows['parent'],candidate_receipts=rows['candidate'],expected_task_count=len(current['access'].records),expected_seeds=tuple(a['selected_seeds']))
    sink=Path(a['binding_ref']['path']).parent
    paired_ref=write_once(sink/'restricted/NATIVE_PAIRED_RESULTS.json',paired)
    audit_ref=write_once(sink/'restricted/NATIVE_IDENTITY_AUDIT.json',{'schema_id':'CURRENT_OFFOFF_COVERAGE_CUTOVER_AUDIT_V1','binding_ref':a['binding_ref'],
        'source_binding_ref':a['source_binding_ref'],'amendment_ref':amendment_ref,'execution_roots_by_ordinal':current_roots,'rows':audits})
    fields=('unique_task_count','replicate_seeds','paired_cell_count','total_condition_cell_count','parent_success_cells','candidate_success_cells','both_success_cells','both_failure_cells','parent_only_success_cells','candidate_only_success_cells','mean_task_success_rate_delta')
    summary={k:paired[k] for k in fields};summary.update(schema_id='CURRENT_TRAIN_SELECT_AGGREGATE_V1',round_id=current['start']['round_id'],request_sha256=current['start']['request_sha256'],
        parent_policy_id=current['parent']['policy_id'],candidate_policy_id=current['candidate']['policy_id'],memory_state='OFF',harness_state='OFF',
        primary_statistical_unit='unique_task',replicates_are_not_independent_tasks=True,evidence_access_class='TRAIN_SELECT',benchmark_feedback_used=False,
        frozen_protocol_ref=binding['input_refs']['protocol_ref'],identity_audit_ref=audit_ref,native_paired_results_ref=paired_ref,
        coverage_amended_after_episode_publication=True,coverage_amendment_ref=amendment_ref,new_model_episodes_for_cutover=0)
    summary_ref=write_once(sink/'TRAIN_SELECT_AGGREGATE.json',summary)
    decision=freeze_registered_promotion(native=current_native,protocol=current['protocol'],aggregate=summary,summary_ref=summary_ref,parent=current['parent'],candidate=current['candidate'])
    promotion_ref=write_once(sink/'PROMOTION_DECISION.json',decision.to_dict());chosen=current['candidate'] if decision.decision=='PROMOTE' else current['parent']
    return write_once(sink/'CURRENT_NATIVE_OFFOFF_TERMINAL.json',{'schema_id':'CURRENT_NATIVE_OFFOFF_TERMINAL_V1','round_id':current['start']['round_id'],
        'request_sha256':current['start']['request_sha256'],'binding_ref':a['binding_ref'],'summary_ref':summary_ref,'promotion_ref':promotion_ref,
        'outcome':'PROMOTED' if decision.decision=='PROMOTE' else 'ROLLED_BACK','next_parent_policy_id':chosen['policy_id'],'next_parent_policy_artifact_sha256':chosen['artifact_sha256'],
        'human_scientific_decision_count':0,'benchmark_feedback_used':False})

@contextmanager
def installed(a):
    import offoff_binding.execute as execution
    import entry.offoff_job as job
    from continuity_binding.api import read_ref
    original_validate=execution.validate_completed_offoff_terminal;original_jobs=job.execute_current_offoff_jobs
    def validate(ref):
        terminal=read_ref(ref);audit=read_ref(read_ref(terminal['summary_ref'])['identity_audit_ref'])
        if audit['schema_id']!='CURRENT_OFFOFF_COVERAGE_CUTOVER_AUDIT_V1':return original_validate(ref)
        if finalize(audit['amendment_ref'])!=ref:raise ValueError('CUTOVER_TERMINAL_REPLAY_MISMATCH')
        return True
    def jobs(**kwargs):
        if kwargs['parallel_ref']!=a['current_select_parallel_ref']:return original_jobs(**kwargs)
        from promotion_entry import ROOT
        from parent_cache import ref
        stop=read_ref(ref(ROOT/'runtime/CURRENT_CUTOVER_JOB_STOP.json'))
        if stop['schema_id']!='REGISTERED_CURRENT_SELECT_EXCLUDED_JOBS_STOPPED_V1' or stop['source_parallel_ref']!=a['current_select_parallel_ref'] or stop['all_registered_jobs_terminal'] is not True:raise ValueError('CUTOVER_OLD_JOBS_STOP_CONFIRMATION_REQUIRED')
        plan=read_ref(a['current_select_parallel_ref']);job_root=Path(a['current_select_parallel_ref']['path']).parent.parent/'jobs'
        expected=[ref(job_root/('shard_'+str(s['shard_id']))/'run_000/offoff.SUBMIT_RECEIPT.json') for s in plan['shards']]
        if len(stop['jobs'])!=len(expected) or {r['submission_ref']['sha256'] for r in stop['jobs']}!={r['sha256'] for r in expected}:raise ValueError('CUTOVER_COMPLETE_REGISTERED_JOB_STOP_GRID')
        for row in stop['jobs']:
            if read_ref(row['submission_ref'])['job_id']!=row['job_id'] or row['scheduler_state']['active'] is not False:raise ValueError('CUTOVER_STOP_RECEIPT_JOB_IDENTITY')
        return finalize(materialize(a))
    with patch.object(execution,'validate_completed_offoff_terminal',validate),patch.object(job,'execute_current_offoff_jobs',jobs):yield
