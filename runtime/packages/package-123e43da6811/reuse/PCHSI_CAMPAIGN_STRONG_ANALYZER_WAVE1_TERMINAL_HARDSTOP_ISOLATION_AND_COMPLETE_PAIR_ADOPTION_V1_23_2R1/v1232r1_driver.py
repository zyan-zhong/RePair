from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def load_json(path: Path) -> dict[str,Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('REQUIRED_REGULAR_JSON_MISSING:'+str(path))
    v=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(v,dict):
        raise RuntimeError('JSON_OBJECT_REQUIRED:'+str(path))
    return v


def write_new_json(path: Path, value: Mapping[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(dict(value),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()+b'\n'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        view=memoryview(raw)
        while view:
            n=os.write(fd,view)
            if n<=0: raise OSError('write made no progress')
            view=view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new_value(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()+b'\n'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        view=memoryview(raw)
        while view:
            n=os.write(fd,view)
            if n<=0: raise OSError('write made no progress')
            view=view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def find_badcase_root(qroot: Path) -> Path:
    for p in [qroot,*qroot.parents]:
        if p.name=='badcase': return p
    raise RuntimeError('BADCASE_ROOT_NOT_DERIVABLE_FROM_QROOT')


def discover_strong_repo(qroot: Path) -> tuple[Path,dict[str,Any]]:
    github=find_badcase_root(qroot)/'github_exports'
    rel=Path('docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json')
    found=[]
    for child in sorted(github.iterdir()):
        if not child.is_dir() or child.is_symlink(): continue
        auth=child/rel
        if not auth.is_file() or auth.is_symlink(): continue
        try: v=load_json(auth)
        except Exception: continue
        if v.get('schema_id')!='ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1': continue
        if v.get('strong_primary_fresh_round_execution_authorized') is not True: continue
        roles=set(v.get('strong_primary_roles') or [])
        if not {'ANALYZER','RESEARCH_PLANNER_PRE','RESEARCH_PLANNER_POST'}<=roles: continue
        req=[child/'src/pchsi/analyzer/grouping.py',child/'src/pchsi/analyzer/act3_registration.py',child/'scripts/memory/materialize_sequence_failure_experience_v1.py']
        if all(x.is_file() and not x.is_symlink() for x in req): found.append((child.resolve(),v))
    if len(found)!=1:
        raise RuntimeError('STRONG_REPO_DISCOVERY_NOT_UNIQUE:'+repr([str(x[0]) for x in found]))
    return found[0]


def import_repo(repo: Path) -> None:
    sys.path.insert(0,str(repo/'src'))


def load_historical_attempt_loader(repo: Path):
    path=repo/'scripts/memory/materialize_sequence_failure_experience_v1.py'
    spec=importlib.util.spec_from_file_location('pchsi_v1232r_attempt_loader',path)
    if spec is None or spec.loader is None: raise RuntimeError('ATTEMPT_LOADER_SPEC_INVALID')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    fn=getattr(mod,'load_attempt_directory_v1',None)
    if not callable(fn) or tuple(inspect.signature(fn).parameters)!=('attempt_dir',):
        raise RuntimeError('ATTEMPT_LOADER_SURFACE_DRIFT')
    return fn


def assert_api(repo: Path):
    from pchsi.analyzer import grouping as gm
    from pchsi.analyzer import act3_registration as a3
    from pchsi.reference_loop.bundle_reader import validate_attempt_bundle
    required={
      'build_group_manifests':(gm,'build_group_manifests',{'local_results','mechanical_signatures'}),
      'build_group_synthesis_inputs':(gm,'build_group_synthesis_inputs',{'group_manifests','source_bindings'}),
      'build_group_signature_binding':(a3,'build_group_signature_binding',{'local_result','error','evidence_pack','action_traces_by_call'}),
      'select_dev_source_call':(a3,'select_dev_source_call',{'local_result','error'}),
    }
    out={'validate_attempt_bundle':validate_attempt_bundle,'load_attempt_directory_v1':load_historical_attempt_loader(repo)}
    for key,(mod,name,params) in required.items():
        fn=getattr(mod,name,None)
        if not callable(fn): raise RuntimeError('FIXED_HEAD_REQUIRED_SYMBOL_MISSING:'+name)
        if not params<=set(inspect.signature(fn).parameters): raise RuntimeError('FIXED_HEAD_SIGNATURE_DRIFT:'+name)
        out[key]=fn
    return out


def classify_source_closed_groups(groups, bindings):
    source_closed=[]; partial=[]; no_source=[]
    for g in groups:
        members=g.get('membership_records')
        if not isinstance(members,list) or not members: raise RuntimeError('GROUP_MEMBERSHIP_RECORDS_INVALID')
        keys=[]
        for m in members:
            if not isinstance(m,dict): raise RuntimeError('GROUP_MEMBERSHIP_RECORD_INVALID')
            keys.append((str(m.get('local_result_sha256')),str(m.get('error_instance_id'))))
        n=sum(1 for k in keys if k in bindings)
        if n==len(keys): source_closed.append(g)
        elif n==0: no_source.append(g)
        else: partial.append(g)
    return source_closed,partial,no_source


def audit_terminal_hard_stop_isolation(*, wave, rows, units, complete_source_ids):
    """Accept prior complete pairs only when one terminal hard stop is provably final and isolated.

    The registry runner stops immediately after a hard_stop row. Therefore a full-registry
    execution manifest plus one hard stop mechanically proves that the hard stop occurred on
    the final frozen unit. The hard-stop unit itself remains censored/quarantined and is never
    retried or promoted into the complete-pair corpus.
    """
    hard=[(i,r) for i,r in enumerate(rows) if isinstance(r,dict) and r.get('hard_stop') is True]
    declared=wave.get('hard_stop_count')
    if declared!=len(hard):
        raise RuntimeError('Q_HARD_STOP_COUNT_DRIFT')
    if len(hard)!=1:
        raise RuntimeError('Q_HARD_STOP_RECOVERY_REQUIRES_EXACTLY_ONE_TERMINAL_HARD_STOP:'+str(len(hard)))
    idx,row=hard[0]
    if idx!=len(rows)-1:
        raise RuntimeError('Q_HARD_STOP_NOT_FINAL_EXECUTED_UNIT')
    if len(rows)!=len(units):
        raise RuntimeError('Q_HARD_STOP_ISOLATION_REQUIRES_FULL_REGISTRY_TERMINATION')
    unit=units[idx]
    for field in ('source_unit_id','stage_id','condition_id'):
        if row.get(field)!=unit.get(field):
            raise RuntimeError('Q_HARD_STOP_FINAL_UNIT_BINDING_MISMATCH:'+field)
    source=str(row.get('source_unit_id'))
    if source in set(complete_source_ids):
        raise RuntimeError('Q_HARD_STOP_SOURCE_CANNOT_BE_COMPLETE_PAIR')
    call_dir=Path(str(row.get('call_dir')))
    if call_dir.is_symlink() or not call_dir.is_dir():
        raise RuntimeError('Q_HARD_STOP_CALL_DIR_INVALID')
    logical=load_json(call_dir/'logical_call.json')
    attempt=load_json(call_dir/'attempt_000.json')
    method=load_json(call_dir/'method_result.json')
    if logical.get('logical_call_id')!=row.get('logical_call_id'):
        raise RuntimeError('Q_HARD_STOP_LOGICAL_CALL_ID_MISMATCH')
    if logical.get('stage_id')!=row.get('stage_id') or logical.get('condition_id')!=row.get('condition_id'):
        raise RuntimeError('Q_HARD_STOP_LOGICAL_STAGE_BINDING_MISMATCH')
    if logical.get('terminal_method_status')!=row.get('status'):
        raise RuntimeError('Q_HARD_STOP_LOGICAL_TERMINAL_STATUS_MISMATCH')
    if method.get('hard_stop') is not True:
        raise RuntimeError('Q_HARD_STOP_METHOD_RECEIPT_NOT_HARD_STOP')
    if method.get('status')!=row.get('status'):
        raise RuntimeError('Q_HARD_STOP_METHOD_STATUS_MISMATCH')
    if method.get('counts_as_method_failure') is not False:
        raise RuntimeError('Q_HARD_STOP_METHOD_FAILURE_AUTHORITY_DRIFT')
    if method.get('failure_class')!=row.get('method_failure_reason'):
        raise RuntimeError('Q_HARD_STOP_FAILURE_CLASS_MISMATCH')
    if attempt.get('retry_class')!='NO_RETRY' or attempt.get('retry_authority')!='FROZEN_RUNTIME_POLICY':
        raise RuntimeError('Q_HARD_STOP_RETRY_CONTRACT_DRIFT')
    if attempt.get('terminal_attempt_status') not in {'AMBIGUOUS_POST_SEND','INFRASTRUCTURE_ERROR','PROVIDER_REJECTED'}:
        raise RuntimeError('Q_HARD_STOP_TERMINAL_ATTEMPT_STATUS_UNEXPECTED:'+str(attempt.get('terminal_attempt_status')))
    if attempt.get('logical_call_id')!=row.get('logical_call_id'):
        raise RuntimeError('Q_HARD_STOP_ATTEMPT_LOGICAL_CALL_MISMATCH')
    # No complete pair may depend on the censored source. The full-registry + final-row proof
    # makes all earlier accepted pairs temporally prior to this stop and durable on disk.
    return {
        'schema_id':'V1232R1_Q_TERMINAL_HARD_STOP_ISOLATION_V1',
        'schema_version':1,
        'hard_stop_count':1,
        'hard_stop_row_index':idx,
        'registry_unit_count':len(units),
        'execution_row_count':len(rows),
        'hard_stop_is_final_frozen_unit':True,
        'hard_stop_source_unit_id':source,
        'hard_stop_stage_id':row.get('stage_id'),
        'hard_stop_condition_id':row.get('condition_id'),
        'logical_call_id':row.get('logical_call_id'),
        'logical_method_status':row.get('status'),
        'failure_class':row.get('method_failure_reason'),
        'bytes_transmission_state':attempt.get('bytes_transmission_state'),
        'retry_class':attempt.get('retry_class'),
        'retry_authority':attempt.get('retry_authority'),
        'terminal_attempt_status':attempt.get('terminal_attempt_status'),
        'counts_as_method_failure':method.get('counts_as_method_failure'),
        'automatic_retry_performed':False,
        'replacement_source_performed':False,
        'top_up_performed':False,
        'hard_stop_source_quarantined_from_complete_pair_corpus':True,
        'prior_complete_pairs_remain_adoptable':True,
        'human_disposition_required':False,
        'receipt_sha256':'0'*64,
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--v1232q-output-root',required=True)
    a=ap.parse_args()
    qroot=Path(a.v1232q_output_root).resolve()
    if qroot.is_symlink() or not qroot.is_dir(): raise RuntimeError('V1232Q_OUTPUT_ROOT_INVALID')

    wave=load_json(qroot/'V1232Q_STRONG_LOCAL_WAVE_TERMINAL_V1.json')
    selected=load_json(qroot/'V1232Q_SELECTED_SOURCE_UNIVERSE_V1.json')
    execm=load_json(qroot/'strong_local_runtime/execution_manifest.json')
    handoff=load_json(qroot/'V1232Q_SOURCE_ROLLOUT_HANDOFF_COPY.json')
    registry=load_json(qroot/'CLEAN_ANALYZER_LOCAL_RUNTIME_INPUT_REGISTRY_V1.json')

    if wave.get('schema_id')!='V1232Q_STRONG_LOCAL_WAVE_TERMINAL_V1': raise RuntimeError('Q_WAVE_SCHEMA_MISMATCH')
    if wave.get('human_disposition_required') is not False or wave.get('automatic_retry_performed') is not False: raise RuntimeError('Q_WAVE_GOVERNANCE_DRIFT')
    rows=execm.get('rows'); units=registry.get('units'); selrows=selected.get('rows')
    if not isinstance(rows,list) or not isinstance(units,list) or not isinstance(selrows,list): raise RuntimeError('Q_CORPUS_ROWS_INVALID')
    if len(rows)!=len(units): raise RuntimeError('Q_EXECUTION_NOT_FULL_REGISTRY')
    if selected.get('source_count')!=len(selrows): raise RuntimeError('Q_SELECTED_COUNT_MISMATCH')
    if len(units)!=2*len(selrows): raise RuntimeError('Q_REGISTRY_NOT_EXACT_A0_A1_PAIRS')
    if wave.get('selected_source_count')!=len(selrows): raise RuntimeError('Q_WAVE_SELECTED_COUNT_MISMATCH')

    by_source={}
    for r in rows:
        if not isinstance(r,dict): raise RuntimeError('Q_EXECUTION_ROW_NOT_OBJECT')
        sid=str(r.get('source_unit_id')); stage=str(r.get('stage_id'))
        if stage not in {'L-A0','L-A1'}: raise RuntimeError('Q_UNEXPECTED_LOCAL_STAGE:'+stage)
        by_source.setdefault(sid,{})[stage]=r

    complete=[]; incomplete=[]
    for meta in selrows:
        sid=str(meta['source_unit_id']); sr=by_source.get(sid,{})
        if set(sr)!={'L-A0','L-A1'}: raise RuntimeError('Q_SOURCE_MISSING_STAGE:'+sid)
        a0=sr['L-A0']; a1=sr['L-A1']
        if a0.get('status')=='ACCEPTED' and a1.get('status')=='ACCEPTED':
            complete.append(sid)
        else:
            incomplete.append({
              'source_unit_id':sid,
              'A0_status':a0.get('status'),'A0_reason':a0.get('method_failure_reason'),
              'A1_status':a1.get('status'),'A1_reason':a1.get('method_failure_reason'),
              'A0_logical_call_id':a0.get('logical_call_id'),'A1_logical_call_id':a1.get('logical_call_id'),
            })
    if complete!=wave.get('complete_source_unit_ids'): raise RuntimeError('Q_COMPLETE_PAIR_IDENTITY_DRIFT')
    if len(complete)!=wave.get('complete_pair_count') or len(incomplete)!=wave.get('censored_source_count'): raise RuntimeError('Q_PAIR_CENSUS_DRIFT')

    hard_stop_receipt=audit_terminal_hard_stop_isolation(
        wave=wave, rows=rows, units=units, complete_source_ids=complete
    )

    repo,role_auth=discover_strong_repo(qroot); import_repo(repo); api=assert_api(repo)
    from pchsi.reference_loop.canonical import domain_hash

    activation=domain_hash('V1232R1_WAVE1_ADOPTION_ACTIVATION_V1',{
      'q_wave_sha256':wave['wave_sha256'],
      'q_execution_manifest_file_sha256':sha256_file(qroot/'strong_local_runtime/execution_manifest.json'),
      'role_authority_file_sha256':sha256_file(repo/'docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json'),
    })
    out=find_badcase_root(qroot)/'new_human_pi1/control/v1232r_wave1_complete_pair_adoption_and_canonical_act3_group_prep'/activation
    out.mkdir(parents=True,exist_ok=False)
    hard_stop_receipt['receipt_sha256']=domain_hash(
        'V1232R1_Q_TERMINAL_HARD_STOP_ISOLATION_V1',
        hard_stop_receipt,
        excluded_field='receipt_sha256',
    )
    write_new_json(out/'V1232R1_Q_TERMINAL_HARD_STOP_ISOLATION_V1.json',hard_stop_receipt)

    adoption={
      'schema_id':'V1232R1_STRONG_WAVE1_COMPLETE_PAIR_ADOPTION_V1','schema_version':1,
      'round_id':wave['round_id'],'source_q_wave_sha256':wave['wave_sha256'],
      'selected_source_count':len(selrows),'complete_pair_count':len(complete),'incomplete_source_count':len(incomplete),
      'complete_source_unit_ids':complete,'incomplete_sources':incomplete,
      'logical_call_count_reused':len(rows),'logical_call_reexecution_count':0,
      'terminal_hard_stop_isolation_receipt_sha256':hard_stop_receipt['receipt_sha256'],
      'automatic_retry_count':0,'replacement_source_count':0,'top_up_source_count':0,'resource_budget_expansion':False,
      'outcome_adaptive_selection_used':False,'human_disposition_required':False,'human_scientific_decision_count':0,
      'adoption_policy':'ONLY_EXISTING_A0_ACCEPTED_PLUS_A1_ACCEPTED_COMPLETE_PAIRS_ENTER_WAVE2',
      'adoption_sha256':'0'*64,
    }
    adoption['adoption_sha256']=domain_hash('V1232R1_STRONG_WAVE1_COMPLETE_PAIR_ADOPTION_V1',adoption,excluded_field='adoption_sha256')
    write_new_json(out/'V1232R1_STRONG_WAVE1_COMPLETE_PAIR_ADOPTION_V1.json',adoption)

    sel_by={str(x['source_unit_id']):x for x in selrows}
    local_results=[]; a1_data={}
    for sid in complete:
        meta=sel_by[sid]
        sm=load_json(qroot/'units'/sid/'source_unit_manifest.json')
        if sm.get('source_unit_id')!=sid: raise RuntimeError('SOURCE_UNIT_MANIFEST_IDENTITY_MISMATCH:'+sid)
        bundle_path=Path(str(sm.get('attempt_bundle_path')))
        b=api['validate_attempt_bundle'](bundle_path)
        if b.attempt_bundle_sha256!=sm.get('attempt_bundle_sha256') or b.task_id!=sm.get('task_id'): raise RuntimeError('SOURCE_BUNDLE_MANIFEST_MISMATCH:'+sid)
        a1row=by_source[sid]['L-A1']; art=load_json(Path(str(a1row['call_dir']))/'validated_artifact.json')
        if art.get('local_result_sha256')!=a1row.get('validated_artifact_sha256'): raise RuntimeError('A1_VALIDATED_IDENTITY_MISMATCH:'+sid)
        local_results.append(art); a1_data[sid]=(art,meta,b,bundle_path)

    req_path=Path(str(handoff.get('rollout_request_path')))
    if req_path.is_symlink() or not req_path.is_file() or sha256_file(req_path)!=handoff.get('rollout_request_sha256'): raise RuntimeError('ROLLOUT_REQUEST_AUTHORITY_INVALID')
    req=load_json(req_path); memory_sha=req.get('round_start_memory_snapshot_sha256')
    if not isinstance(memory_sha,str) or len(memory_sha)!=64: raise RuntimeError('ROUND_START_MEMORY_SHA_MISSING')

    signatures=[]; source_contexts={}; source_binding_censored=[]; signature_failures=[]
    for sid,(a1,meta,b,bundle_path) in a1_data.items():
        pack=load_json(qroot/'units'/sid/'analyzer_evidence_pack.json')
        raw=api['load_attempt_directory_v1'](bundle_path)
        traces={x.model_call_index:x for x in raw.traces}; calls={x.model_call_index:x for x in raw.policy_calls}
        for err in a1.get('error_instances',[]):
            try:
                sig=api['build_group_signature_binding'](local_result=a1,error=err,evidence_pack=pack,action_traces_by_call=traces)
            except Exception as e:
                signature_failures.append({'source_unit_id':sid,'error_instance_id':err.get('error_instance_id'),'reason':type(e).__name__+':'+str(e)})
                continue
            signatures.append(sig)
            try: sel=api['select_dev_source_call'](local_result=a1,error=err)
            except Exception as e:
                source_binding_censored.append({'source_unit_id':sid,'error_instance_id':err.get('error_instance_id'),'reason':type(e).__name__+':'+str(e)}); continue
            if sel.get('formal_eligible') is not True:
                source_binding_censored.append({'source_unit_id':sid,'error_instance_id':err.get('error_instance_id'),'reason':'NO_UNIQUE_LINKED_REPAIR_SOURCE_CALL'}); continue
            ci=int(sel['source_call_index']); call=calls.get(ci)
            if call is None:
                source_binding_censored.append({'source_unit_id':sid,'error_instance_id':err.get('error_instance_id'),'reason':'SOURCE_CALL_NOT_PRESENT'}); continue
            state_sha=domain_hash('V1232Q_CURRENT_ROUND_ANALYZER_GROUP_SOURCE_CONTEXT_V1',{
              'round_id':wave['round_id'],'parent_policy_id':registry['policy_version'],'source_unit_id':sid,
              'source_bundle_sha256':b.attempt_bundle_sha256,'model_call_index':ci,'observation_sha256':call.observation_sha256,
              'menu_sha256':call.admissible_commands_sequence_sha256,'executed_history_sha256':call.executed_history_sha256,
              'prompt_sha256':call.prompt_sha256,'round_start_memory_snapshot_sha256':memory_sha,
            })
            ctx={'source_unit_id':sid,'local_result_sha256':a1['local_result_sha256'],'error_instance_id':err['error_instance_id'],
              'source_state_sha256':state_sha,'menu_sha256':call.admissible_commands_sequence_sha256,'source_call_index':ci,
              'public_task_goal':call.public_task_goal,'observation':call.observation,'admissible_commands':list(call.admissible_commands),
              'executed_history':[{'action':x,'resulting_observation':y} for x,y in call.executed_history],
              'interface_feedback_before':call.interface_feedback_before,'budget_before':dict(call.budget_before),
              'source_context_identity_role':'ANALYZER_GROUP_BINDING_ONLY_F0F1_REPLAY_REBIND_REQUIRED'}
            key=(a1['local_result_sha256'],err['error_instance_id'])
            if key in source_contexts: raise RuntimeError('DUPLICATE_GROUP_SOURCE_CONTEXT:'+repr(key))
            source_contexts[key]=ctx

    if signature_failures:
        fail={'schema_id':'V1232R1_ACT3_SIGNATURE_FAILURE_V1','schema_version':1,'round_id':wave['round_id'],'failure_count':len(signature_failures),'rows':signature_failures,'human_disposition_required':False}
        write_new_json(out/'V1232R1_ACT3_SIGNATURE_FAILURE_V1.json',fail)
        print('STATUS=V1232R1_ACT3_SIGNATURE_COMPILATION_FAIL_CLOSED'); print('V1232R1_OUTPUT_ROOT='+str(out)); print('V1232R1_SIGNATURE_FAILURE_COUNT='+str(len(signature_failures))); print('HUMAN_DISPOSITION_REQUIRED=false'); return 21
    if not signatures: raise RuntimeError('NO_A1_ERROR_INSTANCE_SIGNATURES')

    mechanical={(x['local_result_sha256'],x['error_instance_id']):x for x in signatures}
    groups=api['build_group_manifests'](local_results=local_results,mechanical_signatures=mechanical)
    closed,partial,no_source=classify_source_closed_groups(groups,source_contexts)
    if not closed: raise RuntimeError('NO_SOURCE_CLOSED_GROUPS')
    synths=api['build_group_synthesis_inputs'](closed,source_bindings=source_contexts)
    if len(synths)!=len(closed): raise RuntimeError('GROUP_SYNTHESIS_CARDINALITY_MISMATCH')

    group_rows=[]
    for g,synth in zip(closed,synths,strict=True):
        members=[]
        for m in synth['member_rows']:
            key=(m['local_result_sha256'],m['error_instance_id']); c=source_contexts.get(key)
            if c is None: raise RuntimeError('GROUP_MEMBER_CONTEXT_MISSING:'+repr(key))
            members.append(c)
        gr=out/'groups'/g['group_id']; gr.mkdir(parents=True,exist_ok=False)
        write_new_json(gr/'group_manifest.json',g); write_new_json(gr/'group_synthesis_input.json',synth); write_new_value(gr/'source_contexts.json',members)
        group_rows.append({'group_id':g['group_id'],'group_manifest_sha256':g['group_manifest_sha256'],'group_manifest_path':str(gr/'group_manifest.json'),'group_synthesis_input_sha256':synth['group_synthesis_input_sha256'],'group_synthesis_input_path':str(gr/'group_synthesis_input.json'),'source_contexts_path':str(gr/'source_contexts.json'),'member_count':len(members)})

    universe={'schema_id':'V1232R1_COMPLETE_GROUP_UNIVERSE_V1','schema_version':1,'round_id':wave['round_id'],'group_count':len(groups),'source_closed_group_count':len(closed),'partial_group_count':len(partial),'no_source_group_count':len(no_source),'source_binding_censored_count':len(source_binding_censored),'human_group_selection_performed':False,'group_top_up_performed':False,'complete_pair_adoption_sha256':adoption['adoption_sha256'],'universe_sha256':'0'*64}
    universe['universe_sha256']=domain_hash('V1232R1_COMPLETE_GROUP_UNIVERSE_V1',universe,excluded_field='universe_sha256'); write_new_json(out/'V1232R1_COMPLETE_GROUP_UNIVERSE_V1.json',universe)
    prep={'schema_id':'V1232R1_DETERMINISTIC_GROUP_PREPARATION_V1','schema_version':1,'round_id':wave['round_id'],'source_wave_sha256':wave['wave_sha256'],'complete_pair_adoption_sha256':adoption['adoption_sha256'],'formal_signature_count':len(signatures),'complete_group_count':len(groups),'source_closed_group_count':len(group_rows),'partial_group_count':len(partial),'no_source_group_count':len(no_source),'source_binding_censored_count':len(source_binding_censored),'groups':group_rows,'source_binding_censored':source_binding_censored,'source_contexts_are_analyzer_group_bindings_not_f0f1_replay_authority':True,'historical_act3_attempt_loader_reused':True,'human_group_selection_performed':False,'analyzer_self_denominator_selection_performed':False,'group_top_up_performed':False,'strong_local_logical_call_reexecution_count':0,'next':'EXISTING_STAGE6I_STAGE6J_STYLE_GROUP_RUNTIME_MATERIALIZATION_G_A2_A3_THEN_C_P_X_THEN_DYNAMIC_PRE_V2','prep_sha256':'0'*64}
    prep['prep_sha256']=domain_hash('V1232R1_DETERMINISTIC_GROUP_PREPARATION_V1',prep,excluded_field='prep_sha256'); write_new_json(out/'V1232R1_DETERMINISTIC_GROUP_PREPARATION_V1.json',prep)
    term={'schema_id':'PCHSI_V1232R1_TERMINAL_V1','schema_version':1,'status':'Q_WAVE1_COMPLETE_PAIRS_ADOPTED_CANONICAL_ACT3_GROUP_PREP_COMPLETE','round_id':wave['round_id'],'parent_policy_id':registry['policy_version'],'source_q_wave_sha256':wave['wave_sha256'],'selected_source_count':len(selrows),'complete_local_pair_count':len(complete),'incomplete_source_count':len(incomplete),'q_terminal_hard_stop_count':hard_stop_receipt['hard_stop_count'],'q_terminal_hard_stop_failure_class':hard_stop_receipt['failure_class'],'formal_signature_count':len(signatures),'complete_group_count':len(groups),'source_closed_group_count':len(group_rows),'provider_call_count':0,'strong_local_logical_call_reexecution_count':0,'environment_execution_count':0,'training_execution_count':0,'human_scientific_decision_count':0,'automatic_retry_count':0,'replacement_source_count':0,'top_up_source_count':0,'next':prep['next'],'terminal_sha256':'0'*64}
    term['terminal_sha256']=domain_hash('PCHSI_V1232R1_TERMINAL_V1',term,excluded_field='terminal_sha256'); write_new_json(out/'PCHSI_V1232R1_TERMINAL_V1.json',term)
    print('STATUS=V1232R1_Q_WAVE1_COMPLETE_PAIRS_ADOPTED_CANONICAL_ACT3_GROUP_PREP_COMPLETE')
    print('V1232R1_OUTPUT_ROOT='+str(out)); print('V1232R1_Q_TERMINAL_HARD_STOP_FAILURE_CLASS='+str(hard_stop_receipt['failure_class'])); print('V1232R1_COMPLETE_LOCAL_PAIR_COUNT='+str(len(complete))); print('V1232R1_INCOMPLETE_SOURCE_COUNT='+str(len(incomplete))); print('V1232R1_COMPLETE_GROUP_COUNT='+str(len(groups))); print('V1232R1_SOURCE_CLOSED_GROUP_COUNT='+str(len(group_rows))); print('V1232R1_STRONG_LOCAL_LOGICAL_CALL_REEXECUTION_COUNT=0'); print('HUMAN_DISPOSITION_REQUIRED=false'); print('V1232R1_NEXT='+term['next']); return 0

if __name__=='__main__': raise SystemExit(main())
