"""Typed whole-attempt rollout quarantine; never reuse invalid scientific data."""
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import subprocess
import time
import datetime

from rollout_adapter.materializer import (AuthorityError, canonical, checked, obj,
    put, ref, native_contracts, no_symlink_ancestors)
from rollout_adapter.lifecycle import verify_materialization


def classify_errors(*, fatal_errors, cell_errors, protocol_invalid_count):
    primary = [x for x in cell_errors if x != 'ABORTED_AFTER_PRIOR_INFRASTRUCTURE_OR_PROTOCOL_INVALID']
    if (protocol_invalid_count != 0 or not (fatal_errors or primary)
            or any(x != 'SHARD_PREEXISTING_ENDPOINT_OCCUPIED' for x in fatal_errors)
            or any(x != 'PolicyTransportError' for x in primary)):
        return 'UNSAFE_OR_UNKNOWN'
    return 'SAFE_LOCAL_RESOURCE_ISOLATION'


def accounting_inactive(job, shard_count, text):
    states = {}
    terminal = {'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY',
                'NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}
    for line in text.splitlines():
        parts = line.split('|')
        if len(parts) < 3 or '.' in parts[0]: continue
        if parts[0] in states: return False
        states[parts[0]] = parts[1].split()[0].rstrip('+')
    expected = {job+'_'+str(n) for n in range(shard_count)}
    return set(states) == expected and all(s in terminal for s in states.values())


def prove_inactive(manifest):
    root=Path(manifest['root'])
    submission=obj(ref(root/'SUBMISSION_RECEIPT.json'))
    if submission['manifest_sha256'] != ref(manifest['manifest_path'])['sha256']:
        raise AuthorityError('INVALID_ROLLOUT_SUBMISSION_IDENTITY')
    job=submission['array_job_id']
    if not str(job).isdigit(): raise AuthorityError('INVALID_ROLLOUT_JOB_ID')
    queue=subprocess.run(['squeue','--noheader','--array','--jobs',job,'--format','%i|%T'],
        capture_output=True,text=True,timeout=60)
    if queue.stdout.strip() or (queue.returncode and 'Invalid job id' not in queue.stderr):
        raise AuthorityError('INVALID_ROLLOUT_ARRAY_NOT_PROVEN_INACTIVE')
    watch=obj(ref(root/'RESIDENT_ROLLOUT_WATCH_START.json'))
    since=datetime.datetime.fromtimestamp(watch['start_epoch'],datetime.timezone.utc).strftime('%Y-%m-%d')
    accounting=subprocess.run(['sacct','--noheader','--parsable2','--jobs',job,'--starttime',since,
        '--format','JobID,State,ExitCode,ElapsedRaw,AllocTRES,Start,End'],
        capture_output=True,text=True,timeout=60)
    plan=obj({'path':manifest['shard_plan_path'],'sha256':manifest['shard_plan_sha256']})
    if accounting.returncode or not accounting_inactive(job,plan['shard_count'],accounting.stdout):
        raise AuthorityError('INVALID_ROLLOUT_ALL_SHARDS_TERMINAL_REQUIRED')
    return {'array_job_id':job,'sacct':accounting.stdout,
            'all_registered_shards_terminal':True,'slurm_submission_count':0}


def inspect_invalid(manifest_ref, start):
    m=obj(manifest_ref);root=verify_materialization(m)
    if obj({'path':m['request_path'],'sha256':m['request_file_sha256']}) != start:
        raise AuthorityError('INVALID_ROLLOUT_CURRENT_REQUEST')
    gp=root/'round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json'
    hp=root/'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json'
    terminal=obj(ref(gp));handoff=obj(ref(hp))
    if (terminal.get('scientific_rollout_valid') is not False
            or terminal.get('handoff_path')!=str(hp)
            or terminal.get('handoff_sha256')!=ref(hp)['sha256']
            or terminal.get('training_execution_count')!=0
            or terminal.get('memory_writeback_count')!=0
            or handoff.get('training_execution_performed') is not False
            or handoff.get('memory_writeback_performed') is not False
            or handoff.get('benchmark_feedback_used') is not False
            or handoff.get('rollout_request_sha256')!=m['request_file_sha256']):
        raise AuthorityError('INVALID_ROLLOUT_TERMINAL_BINDING')
    refs={}
    for role in ('attempt_bundle_index','rollout_universe','rollout_execution_binding'):
        value={'path':handoff[role+'_path'],'sha256':handoff[role+'_sha256']}
        if not no_symlink_ancestors(value['path']).resolve().is_relative_to(root):
            raise AuthorityError('INVALID_ROLLOUT_FOREIGN_REF')
        refs[role]=value;checked(value)
    if obj(refs['rollout_execution_binding']) != m['formal_execution_binding']:
        raise AuthorityError('INVALID_ROLLOUT_EXECUTION_BINDING_CHANGED')
    native=native_contracts(Path(m['implementation_worktree']))
    universe=obj(refs['rollout_universe'])
    rows=tuple(native.RoundEpisodeTerminalV1(**r) for r in universe['terminal_rows'])
    if native.seal_rollout_universe(request_sha256=start['request_sha256'],terminals=rows).to_dict()!=universe:
        raise AuthorityError('INVALID_ROLLOUT_UNIVERSE_REPLAY')
    for key in ('scheduled_count','success_count','failure_count','infrastructure_invalid_count',
                'protocol_invalid_count','scientific_rollout_valid'):
        if terminal[key]!=universe[key] or handoff[key]!=universe[key]:
            raise AuthorityError('INVALID_ROLLOUT_CENSUS:'+key)
    plan=obj({'path':m['shard_plan_path'],'sha256':m['shard_plan_sha256']})
    if len(rows)!=plan['total_schedule_count']:
        raise AuthorityError('INVALID_ROLLOUT_INCOMPLETE_SCHEDULE')
    index=obj(refs['attempt_bundle_index'])
    if (index['request_sha256']!=start['request_sha256'] or index['human_selection_performed'] is not False
            or index['row_count']!=len(index['rows'])):
        raise AuthorityError('INVALID_ROLLOUT_INDEX_IDENTITY')
    fatal={}
    for item in index['fatal_shards']:
        n=item['shard_id'];expected=root/'shards'/f'{n:04d}'/'PCHSI_V1232S_SHARD_FATAL_V1.json'
        if n in fatal or not 0<=n<plan['shard_count'] or item['fatal_path']!=str(expected):
            raise AuthorityError('INVALID_ROLLOUT_FATAL_INDEX')
        value=obj({'path':str(expected),'sha256':item['fatal_sha256']})
        if value['shard_id']!=n or value['error_message']!=item['fatal_error_message']:
            raise AuthorityError('INVALID_ROLLOUT_FATAL_IDENTITY')
        fatal[n]=value
    by_ordinal={r['global_ordinal']:r for r in index['rows']}
    expected_ordinals={n for n in range(len(rows)) if n%plan['shard_count'] not in fatal}
    if len(by_ordinal)!=len(index['rows']) or set(by_ordinal)!=expected_ordinals:
        raise AuthorityError('INVALID_ROLLOUT_INDEX_COVERAGE')
    errors=[]
    for n,row in enumerate(rows):
        shard=n%plan['shard_count']
        if shard in fatal: continue
        sidecar=obj({'path':root/'shards'/f'{shard:04d}'/'cell_terminals'/f'{n:05d}.json',
                     'sha256':row.terminal_receipt_sha256})
        if any(sidecar.get(k)!=getattr(row,k) for k in ('scientific_cell_id','execution_attempt_id','status','success')):
            raise AuthorityError('INVALID_ROLLOUT_CELL_IDENTITY')
        if row.status not in {'INFRASTRUCTURE_INVALID','PROTOCOL_INVALID'}: continue
        expected=root/'shards'/f'{shard:04d}'/'rollout_run/attempt_ledger'/(row.execution_attempt_id+'.terminal.json')
        indexed=by_ordinal[n]
        if indexed['attempt_terminal_path'] is None:
            errors.append(sidecar['termination_reason']);continue
        if indexed['attempt_terminal_path']!=str(expected):
            raise AuthorityError('INVALID_ROLLOUT_ATTEMPT_PATH')
        attempt=obj(ref(expected))
        if (attempt['execution_attempt_id']!=row.execution_attempt_id
                or attempt['scientific_outcome_status']!='SCIENTIFIC_OUTCOME_NOT_PRODUCED'):
            raise AuthorityError('INVALID_ROLLOUT_ATTEMPT_IDENTITY')
        errors.append(attempt.get('error_code','UNKNOWN'))
    retry=classify_errors(fatal_errors=[v['error_message'] for v in fatal.values()],
        cell_errors=errors,protocol_invalid_count=terminal['protocol_invalid_count'])
    return {'schema_id':'TYPED_INVALID_ROLLOUT_DISPOSITION_V1','start':start,
            'rollout_manifest_ref':manifest_ref,'global_terminal_ref':ref(gp),'handoff_ref':ref(hp),
            'index_ref':refs['attempt_bundle_index'],'retry_class':retry,
            'observed_rollout':terminal,'fatal_errors':[v['error_message'] for v in fatal.values()],
            'cell_errors':errors,'valid_round_contribution':0,
            'invalid_attempt_adaptive_evidence_reuse':False}


def wait_inactive(manifest, *, settings, output_root, clock=time.time, sleep=time.sleep, query=prove_inactive):
    start=Path(output_root)/'INVALID_ARRAY_WAIT_START.json'
    if not start.is_file():put(start,canonical({'start_epoch':clock(),'manifest_ref':ref(manifest['manifest_path'])}))
    observed=obj(ref(start))
    if observed['manifest_ref']!=ref(manifest['manifest_path']):raise AuthorityError('INVALID_ARRAY_WAIT_IDENTITY')
    while True:
        try:return query(manifest)
        except AuthorityError as exc:
            if str(exc) not in {'INVALID_ROLLOUT_ARRAY_NOT_PROVEN_INACTIVE','INVALID_ROLLOUT_ALL_SHARDS_TERMINAL_REQUIRED'}:raise
            if clock()-observed['start_epoch']>=settings['publication_grace_seconds']:
                raise AuthorityError('INVALID_ROLLOUT_ACCOUNTING_GRACE_EXPIRED') from exc
        sleep(settings['poll_seconds'])


def invalid_result(*, manifest_ref, start, attempt_root, current_parent_context, settings):
    disposition=inspect_invalid(manifest_ref,start)
    root=Path(attempt_root);accounting=root/'INVALID_ROLLOUT_ACCOUNTING.json'
    if not accounting.is_file():
        put(accounting,canonical(wait_inactive(obj(manifest_ref),settings=settings,output_root=root)))
    disposition['accounting_ref']=ref(accounting)
    path=root/'INVALID_ROLLOUT_DISPOSITION.json';put(path,canonical(disposition))
    keys=('round_id','execution_attempt_id','request_sha256','parent_policy_id',
          'parent_policy_artifact_sha256','round_start_memory_snapshot_sha256')
    return {**{k:start[k] for k in keys},'schema_id':'FORMAL_NATIVE_ROUND_RESULT_V1',
        'outcome':'PROTOCOL_INFRA_INVALID','retry_class':disposition['retry_class'],
        'next_parent_policy_id':start['parent_policy_id'],
        'next_parent_policy_artifact_sha256':start['parent_policy_artifact_sha256'],
        'terminal_ref':ref(path),'rollout_manifest_ref':manifest_ref,
        'attempt_root':str(root),'current_parent_context':current_parent_context,
        'human_scientific_decision_count':0,'benchmark_feedback_used':False,
        'invalid_attempt_adaptive_evidence_reuse':False,'stage_evidence_refs':{}}


def validate_invalid_result(start,result):
    expected=inspect_invalid(result['rollout_manifest_ref'],start)
    actual=obj(result['terminal_ref']);accounting=obj(actual['accounting_ref'])
    expected['accounting_ref']=actual['accounting_ref']
    m=obj(result['rollout_manifest_ref']);plan=obj({'path':m['shard_plan_path'],'sha256':m['shard_plan_sha256']})
    job=obj(ref(Path(m['root'])/'SUBMISSION_RECEIPT.json'))['array_job_id']
    if (actual!=expected or result['retry_class']!=expected['retry_class']
            or accounting['array_job_id']!=job
            or not accounting_inactive(job,plan['shard_count'],accounting['sacct'])):
        raise AuthorityError('INVALID_ROLLOUT_DISPOSITION_REPLAY')


def build_retry(driver,start,result):
    validate_invalid_result(start,result)
    from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
    from continuity_binding.next_request import rebind_execution
    current=driver._binding(start)
    identity=hashlib.sha256(canonical({'previous_request':start['request_sha256'],
        'invalid_terminal':result['terminal_ref']})).hexdigest()
    values={f.name:start[f.name] for f in fields(RoundRolloutCollectionRequestV1)}
    values.update(execution_attempt_id=start['round_id']+'-infra-'+identity[:20],request_sha256=None)
    nxt=RoundRolloutCollectionRequestV1(**values).to_dict()
    sink=Path(result['attempt_root'])/'infra_next';request=sink/'ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json'
    binding=sink/'ROUND_ROLLOUT_EXECUTION_BINDING_V1.json'
    put(request,canonical(nxt))
    put(binding,canonical(rebind_execution(obj(current['execution_binding']),start['request_sha256'],nxt['request_sha256']).to_dict()))
    next_current={**current,'request':ref(request),'execution_binding':ref(binding)}
    if current['input_refs'] is not None:
        inputs=obj(current['input_refs']);inputs['request_sha256']=nxt['request_sha256']
        path=sink/'ROUND_ROLLOUT_INPUT_REFERENCES_V1.json';put(path,canonical(inputs))
        next_current['input_refs']=ref(path)
    if current['current_index'] is not None:
        next_current['current_index']=rebind_retry_index(current['current_index'],start,nxt,sink)
    put(driver._binding_path(nxt),canonical(next_current))
    return nxt


def rebind_retry_index(index_ref,start,nxt,sink):
    from analyzer_binding.aggregate_context import validate_previous_select_context
    index=obj(index_ref)
    if (index['schema_id']!='CURRENT_FORMAL_RESIDENT_INPUT_INDEX_V1'
            or index['request_sha256']!=start['request_sha256'] or index['round_id']!=start['round_id']):
        raise AuthorityError('INFRA_RETRY_CURRENT_INDEX_IDENTITY')
    updated={**index,'request_sha256':nxt['request_sha256'],'refs':dict(index['refs'])}
    context_ref=index['refs'].get('previous_select_context')
    if context_ref:
        normalized={'path':context_ref['path'],'sha256':context_ref.get('sha256',context_ref.get('file_sha256'))}
        context=obj(normalized)
        validate_previous_select_context(context,current_request=start)
        rebound={**context,'consumer_request_sha256':nxt['request_sha256']}
        validate_previous_select_context(rebound,current_request=nxt)
        path=Path(sink)/'PREVIOUS_TRAIN_SELECT_RESEARCH_CONTEXT.json';put(path,canonical(rebound))
        updated['refs']['previous_select_context']={'path':str(path),'file_sha256':ref(path)['sha256']}
    path=Path(sink)/'CURRENT_INPUT_INDEX.json';put(path,canonical(updated))
    return ref(path)
