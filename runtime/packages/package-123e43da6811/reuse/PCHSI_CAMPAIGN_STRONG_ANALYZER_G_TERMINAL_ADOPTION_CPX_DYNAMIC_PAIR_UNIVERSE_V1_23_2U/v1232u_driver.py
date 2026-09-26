from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from source_context_equivalence import (
    index_source_contexts,
    source_context_audit_summary,
    source_context_for_candidate_projection,
)


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def canonical_bytes(value:Any)->bytes:
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode('utf-8')


def load_json(path:Path)->dict[str,Any]:
    if path.is_symlink() or not path.is_file(): raise RuntimeError('REQUIRED_REGULAR_JSON_MISSING:'+str(path))
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict): raise RuntimeError('JSON_OBJECT_REQUIRED:'+str(path))
    return value


def load_json_value(path:Path)->Any:
    if path.is_symlink() or not path.is_file(): raise RuntimeError('REQUIRED_REGULAR_JSON_MISSING:'+str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def write_or_verify_json(path:Path,value:Any)->None:
    raw=canonical_bytes(value)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.read_bytes()!=raw:
            raise RuntimeError('EXISTING_ARTIFACT_IDENTITY_MISMATCH:'+str(path))
        return
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        view=memoryview(raw)
        while view:
            n=os.write(fd,view)
            if n<=0: raise OSError('write made no progress')
            view=view[n:]
        os.fsync(fd)
    finally: os.close(fd)


def sha64(value:object,label:str)->str:
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise RuntimeError(label+'_INVALID_SHA256')
    return value


def find_badcase_root(path:Path)->Path:
    for p in [path,*path.parents]:
        if p.name=='badcase': return p
    raise RuntimeError('BADCASE_ROOT_NOT_DERIVABLE')


def discover_qroot(rroot:Path,source_q_wave_sha256:str)->Path:
    base=find_badcase_root(rroot)/'new_human_pi1/control/v1232q_strong_analyzer_wave1_and_canonical_act3_reuse'
    found=[]
    if base.is_dir() and not base.is_symlink():
        for child in sorted(base.iterdir()):
            term=child/'V1232Q_STRONG_LOCAL_WAVE_TERMINAL_V1.json'
            if child.is_dir() and not child.is_symlink() and term.is_file() and not term.is_symlink():
                try: obj=load_json(term)
                except Exception: continue
                if obj.get('wave_sha256')==source_q_wave_sha256: found.append(child.resolve())
    if len(found)!=1: raise RuntimeError('QROOT_DISCOVERY_NOT_UNIQUE:'+repr([str(x) for x in found]))
    return found[0]


def discover_strong_repo(rroot:Path)->tuple[Path,dict[str,Any]]:
    github=find_badcase_root(rroot)/'github_exports'
    rel=Path('docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json')
    found=[]
    for child in sorted(github.iterdir()):
        if not child.is_dir() or child.is_symlink(): continue
        auth=child/rel
        if not auth.is_file() or auth.is_symlink(): continue
        try: obj=load_json(auth)
        except Exception: continue
        if obj.get('schema_id')!='ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1': continue
        if obj.get('strong_primary_fresh_round_execution_authorized') is not True: continue
        roles=set(obj.get('strong_primary_roles') or [])
        if not {'ANALYZER','RESEARCH_PLANNER_PRE','RESEARCH_PLANNER_POST'}<=roles: continue
        req=[
            child/'src/pchsi/cognitive_runtime/orchestrator.py',
            child/'src/pchsi/cognitive_runtime/projections.py',
            child/'src/pchsi/memory/dev_snapshot_loader.py',
            child/'src/pchsi/memory/consumer_views.py',
            child/'src/pchsi/analyzer/state_candidate_budget.py',
        ]
        if all(x.is_file() and not x.is_symlink() for x in req): found.append((child.resolve(),obj))
    if len(found)!=1: raise RuntimeError('STRONG_REPO_DISCOVERY_NOT_UNIQUE:'+repr([str(x[0]) for x in found]))
    return found[0]


def git_object_id(value:object,object_format:str,label:str)->str:
    if not isinstance(object_format,str) or not object_format:
        raise RuntimeError(label+'_OBJECT_FORMAT_INVALID')
    fmt=object_format.strip().lower()
    try:
        expected_hex_len=hashlib.new(fmt).digest_size*2
    except Exception as error:
        raise RuntimeError(label+'_OBJECT_FORMAT_UNSUPPORTED:'+fmt) from error
    if (
        not isinstance(value,str)
        or len(value)!=expected_hex_len
        or any(c not in '0123456789abcdef' for c in value)
    ):
        raise RuntimeError(
            label+'_INVALID_GIT_OBJECT_ID:format='+fmt
            +':expected_hex_len='+str(expected_hex_len)
            +':observed='+repr(value)
        )
    return value


def tracked_repo_identity(repo:Path)->dict[str,str]:
    fmt_cp=subprocess.run(
        ['git','-C',str(repo),'rev-parse','--show-object-format=storage'],
        capture_output=True,text=True,
    )
    if fmt_cp.returncode!=0:
        raise RuntimeError('REPO_OBJECT_FORMAT_READ_FAILED:'+fmt_cp.stderr.strip())
    object_format=fmt_cp.stdout.strip().lower()
    head_cp=subprocess.run(
        ['git','-C',str(repo),'rev-parse','--verify','HEAD^{commit}'],
        capture_output=True,text=True,
    )
    if head_cp.returncode!=0:
        raise RuntimeError('REPO_HEAD_COMMIT_READ_FAILED:'+head_cp.stderr.strip())
    head_oid=git_object_id(head_cp.stdout.strip(),object_format,'REPO_HEAD')
    type_cp=subprocess.run(
        ['git','-C',str(repo),'cat-file','-t',head_oid],
        capture_output=True,text=True,
    )
    if type_cp.returncode!=0 or type_cp.stdout.strip()!='commit':
        raise RuntimeError(
            'REPO_HEAD_OBJECT_TYPE_INVALID:'
            +type_cp.stdout.strip()+':'+type_cp.stderr.strip()
        )
    st=subprocess.run(
        ['git','-C',str(repo),'status','--porcelain=v1','-z','--untracked-files=no'],
        capture_output=True,
    )
    if st.returncode!=0: raise RuntimeError('REPO_STATUS_READ_FAILED')
    if st.stdout: raise RuntimeError('REPO_TRACKED_WORKTREE_NOT_CLEAN')
    return {'head_oid':head_oid,'object_format':object_format}


def import_repo(repo:Path)->None:
    sys.path.insert(0,str(repo/'src'))


def preflight_api()->dict[str,Any]:
    from pchsi.cognitive_runtime.orchestrator import execute_one
    from pchsi.cognitive_runtime.request_renderer import render_stage_request
    from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
    from pchsi.cognitive_runtime.output_validation import validated_artifact_identity
    from pchsi.cognitive_runtime.manifest import load_runtime_manifest
    from pchsi.cognitive_runtime.projections import group_projection_v3,component_projection,crosscheck_projection_v2
    from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
    from pchsi.memory.consumer_views import MemoryConsumerQueryV1,build_analyzer_memory_view_v1
    from pchsi.evaluation.raw_policy_prompt import ExecutedTransition,InterfaceFeedbackCode
    from pchsi.round_control.clean_group_analyzer_binding import build_clean_group_task_access_record,build_group_universe,build_round_group_analyzer_resource_authority,validate_round_group_analyzer_resource_authority
    from pchsi.analyzer.component_attribution import aggregate_capability_profile,build_policy_behavior_profile
    from pchsi.analyzer.candidate_projector import project_candidate
    from pchsi.analyzer.state_candidate_budget import materialize_state_condition_k1
    required={
      'execute_one':(execute_one,{'output_root','unit_identity','stage_id','condition_id','round_id','policy_version','projection','task_access'}),
      'group_projection_v3':(group_projection_v3,{'group_manifest_path','group_synthesis_input_path','a1_local_result_paths','source_contexts_path','memory_pack_path'}),
      'crosscheck_projection_v2':(crosscheck_projection_v2,{'target_path','target_stage_id','group_manifest_path','common_group_projection_path','memory_pack_path'}),
      'load_calibrated_dev_snapshot_v2':(load_calibrated_dev_snapshot_v2,{'snapshot_directory','expected_snapshot_sha256','token_budget_contract_path','expected_token_budget_contract_sha256'}),
      'build_analyzer_memory_view_v1':(build_analyzer_memory_view_v1,{'query','snapshot','top_k'}),
      'build_clean_group_task_access_record':(build_clean_group_task_access_record,{'round_id','group_id','group_manifest_sha256','member_contexts','task_access_by_source_unit'}),
      'build_round_group_analyzer_resource_authority':(build_round_group_analyzer_resource_authority,{'round_id','policy_version','producer_role','source_authority_sha256','group_universe','group_stage_rows'}),
      'project_candidate':(project_candidate,{'proposal','source_state','candidate_kind','crosscheck_disposition'}),
      'materialize_state_condition_k1':(materialize_state_condition_k1,{'condition_id','source_state_sha256','candidates'}),
    }
    for name,(fn,params) in required.items():
        if not params<=set(inspect.signature(fn).parameters): raise RuntimeError('FIXED_HEAD_CALLABLE_SIGNATURE_DRIFT:'+name)
    return locals()


def strip_memory_projection(value:Mapping[str,Any])->dict[str,Any]:
    out=dict(value); out['memory_pack_sha256']=None; out.pop('memory_pack',None); return out


def build_group_memory_pack(*,contexts:list[dict[str,Any]],snapshot:Any,api:dict[str,Any],domain_hash:Any)->dict[str,Any]:
    MemoryConsumerQueryV1=api['MemoryConsumerQueryV1']; build_view=api['build_analyzer_memory_view_v1']; ExecutedTransition=api['ExecutedTransition']; InterfaceFeedbackCode=api['InterfaceFeedbackCode']
    top_k=int(snapshot.token_budget_contract.max_record_count)
    if top_k<1: raise RuntimeError('ANALYZER_MEMORY_TOP_K_AUTHORITY_INVALID')
    members=[]
    for ctx in contexts:
        hist=tuple(ExecutedTransition(str(x['action']),str(x['resulting_observation'])) for x in ctx.get('executed_history',[]))
        raw_feedback=ctx.get('interface_feedback_before')
        feedback=None if raw_feedback is None else InterfaceFeedbackCode(str(raw_feedback))
        query=MemoryConsumerQueryV1(observation=str(ctx.get('observation','')),executed_transitions=hist,admissible_commands=tuple(ctx.get('admissible_commands') or []),interface_feedback=feedback,public_task_goal=str(ctx.get('public_task_goal','')))
        qdict=query.to_dict(); qsha=domain_hash('V1232T_ANALYZER_MEMORY_QUERY_V1',qdict)
        view=build_view(query=query,snapshot=snapshot,top_k=top_k)
        members.append({'local_result_sha256':ctx['local_result_sha256'],'error_instance_id':ctx['error_instance_id'],'source_state_sha256':ctx['source_state_sha256'],'query_sha256':qsha,'analyzer_memory_view_sha256':view.view_sha256,'analyzer_memory_view':view.to_dict()})
    members.sort(key=lambda x:(x['local_result_sha256'],x['error_instance_id']))
    pack={'schema_id':'ACT3_GROUP_ANALYZER_MEMORY_BUNDLE_V1','schema_version':1,'active_snapshot_sha256':snapshot.snapshot.snapshot_sha256,'contract_sha256':snapshot.token_budget_contract.contract_sha256,'member_count':len(members),'members':members,'cross_member_retrieval_fusion':False,'memory_pack_sha256':'0'*64}
    pack['memory_pack_sha256']=domain_hash('ACT3_GROUP_ANALYZER_MEMORY_BUNDLE_V1',pack,excluded_field='memory_pack_sha256')
    return pack


def expected_logical_call_id(*,unit_identity:Mapping[str,Any],stage_id:str,condition_id:str|None,round_id:str,policy_version:str,request_body_sha256:str,domain_hash:Any)->str:
    return domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1',{'scientific_unit_identity_sha256':unit_identity['identity_sha256'],'stage_id':stage_id,'condition_id':condition_id,'round_id':round_id,'policy_version':policy_version,'request_body_sha256':request_body_sha256})


def execute_or_reuse(*,runtime_root:Path,unit_identity:Mapping[str,Any],stage_id:str,condition_id:str|None,round_id:str,policy_version:str,projection:Mapping[str,Any],task_access:Mapping[str,Any],api:dict[str,Any],domain_hash:Any)->dict[str,Any]:
    bundle=api['render_stage_request'](stage_id=stage_id,projection=projection)
    logical_id=expected_logical_call_id(unit_identity=unit_identity,stage_id=stage_id,condition_id=condition_id,round_id=round_id,policy_version=policy_version,request_body_sha256=bundle['request_body_sha256'],domain_hash=domain_hash)
    call_dir=runtime_root/logical_id
    reused=False
    if call_dir.exists() or call_dir.is_symlink():
        if call_dir.is_symlink() or not call_dir.is_dir(): raise RuntimeError('CALL_DIR_INVALID:'+str(call_dir))
        logical_path=call_dir/'logical_call.json'
        if not logical_path.is_file() or logical_path.is_symlink(): raise RuntimeError('UNSAFE_PARTIAL_LOGICAL_CALL_NO_RESEND:'+logical_id)
        logical=load_json(logical_path)
        checks={'logical_call_id':logical_id,'scientific_unit_identity_sha256':unit_identity['identity_sha256'],'stage_id':stage_id,'condition_id':condition_id,'round_id':round_id,'policy_version':policy_version,'request_body_sha256':bundle['request_body_sha256']}
        for key,val in checks.items():
            if logical.get(key)!=val: raise RuntimeError('TERMINAL_LOGICAL_CALL_IDENTITY_MISMATCH:'+key+':'+logical_id)
        status=str(logical.get('terminal_method_status')); result={'logical_call_id':logical_id,'call_dir':str(call_dir),'status':status,'hard_stop':False,'method_failure_reason':None,'reused_terminal_call':True}
        if status=='ACCEPTED':
            artifact=load_json(call_dir/'validated_artifact.json'); result['validated_artifact_sha256']=api['validated_artifact_identity'](stage_id=stage_id,artifact=artifact)
        else:
            m=call_dir/'method_result.json'; v=call_dir/'validation_error.json'
            detail=load_json(m) if m.is_file() and not m.is_symlink() else (load_json(v) if v.is_file() and not v.is_symlink() else {})
            result['method_failure_reason']=detail.get('failure_class') or detail.get('message')
            result['hard_stop']=bool(detail.get('hard_stop',False))
        reused=True
    else:
        result=api['execute_one'](output_root=runtime_root,unit_identity=unit_identity,stage_id=stage_id,condition_id=condition_id,round_id=round_id,policy_version=policy_version,projection=projection,task_access=task_access)
        result=dict(result); result['reused_terminal_call']=False
    print('V1232U_CALL stage='+stage_id+' condition='+str(condition_id)+' status='+str(result.get('status'))+' reused='+str(reused).lower()+' logical_call_id='+logical_id,flush=True)
    return result



def adopt_terminal_call_only(*,runtime_root:Path,unit_identity:Mapping[str,Any],stage_id:str,condition_id:str|None,round_id:str,policy_version:str,projection:Mapping[str,Any],api:dict[str,Any],domain_hash:Any)->dict[str,Any]:
    """Adopt one already-terminal T G-stage call. Never executes provider transport."""
    bundle=api['render_stage_request'](stage_id=stage_id,projection=projection)
    logical_id=expected_logical_call_id(unit_identity=unit_identity,stage_id=stage_id,condition_id=condition_id,round_id=round_id,policy_version=policy_version,request_body_sha256=bundle['request_body_sha256'],domain_hash=domain_hash)
    call_dir=runtime_root/logical_id
    if call_dir.is_symlink() or not call_dir.is_dir():
        raise RuntimeError('T_G_TERMINAL_CALL_MISSING_NO_REEXECUTION:'+logical_id)
    logical_path=call_dir/'logical_call.json'
    if logical_path.is_symlink() or not logical_path.is_file():
        raise RuntimeError('T_G_UNSAFE_PARTIAL_LOGICAL_CALL_NO_REEXECUTION:'+logical_id)
    logical=load_json(logical_path)
    checks={'logical_call_id':logical_id,'scientific_unit_identity_sha256':unit_identity['identity_sha256'],'stage_id':stage_id,'condition_id':condition_id,'round_id':round_id,'policy_version':policy_version,'request_body_sha256':bundle['request_body_sha256']}
    for key,val in checks.items():
        if logical.get(key)!=val: raise RuntimeError('T_G_TERMINAL_LOGICAL_CALL_IDENTITY_MISMATCH:'+key+':'+logical_id)
    status=str(logical.get('terminal_method_status'))
    result={'logical_call_id':logical_id,'call_dir':str(call_dir),'status':status,'hard_stop':False,'method_failure_reason':None,'reused_terminal_call':True,'adopted_from_v1232t':True}
    if status=='ACCEPTED':
        artifact=load_json(call_dir/'validated_artifact.json')
        result['validated_artifact_sha256']=api['validated_artifact_identity'](stage_id=stage_id,artifact=artifact)
    else:
        m=call_dir/'method_result.json'; v=call_dir/'validation_error.json'
        detail=load_json(m) if m.is_file() and not m.is_symlink() else (load_json(v) if v.is_file() and not v.is_symlink() else {})
        result['method_failure_reason']=detail.get('failure_class') or detail.get('message')
        result['hard_stop']=bool(detail.get('hard_stop',False))
    print('V1232U_ADOPT_G_CALL stage='+stage_id+' condition='+str(condition_id)+' status='+status+' logical_call_id='+logical_id,flush=True)
    return result


def formal_group_stage_result(record:Mapping[str,Any],stage_id:str)->dict[str,Any]:
    """Bridge canonical stored pair keys A2/A3 to runtime stage IDs G-A2/G-A3."""
    mapping={'G-A2':'A2','G-A3':'A3'}
    key=mapping.get(stage_id)
    if key is None: raise RuntimeError('UNSUPPORTED_GROUP_STAGE:'+stage_id)
    value=record.get(key)
    if not isinstance(value,dict): raise RuntimeError('COMPLETE_GROUP_STAGE_RESULT_MISSING:'+stage_id)
    return value

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--v1232r1-output-root',required=True); args=ap.parse_args()
    rroot=Path(args.v1232r1_output_root).resolve()
    term=load_json(rroot/'PCHSI_V1232R1_TERMINAL_V1.json'); prep=load_json(rroot/'V1232R1_DETERMINISTIC_GROUP_PREPARATION_V1.json'); adoption=load_json(rroot/'V1232R1_STRONG_WAVE1_COMPLETE_PAIR_ADOPTION_V1.json')
    if term.get('status')!='Q_WAVE1_COMPLETE_PAIRS_ADOPTED_CANONICAL_ACT3_GROUP_PREP_COMPLETE': raise RuntimeError('R1_NOT_SUCCESS_TERMINAL')
    if prep.get('prep_sha256')!=term.get('terminal_sha256') and prep.get('round_id')!=term.get('round_id'): raise RuntimeError('R1_PREP_TERMINAL_BINDING_INVALID')
    if prep.get('source_closed_group_count')!=term.get('source_closed_group_count') or len(prep.get('groups') or [])!=term.get('source_closed_group_count'): raise RuntimeError('R1_SOURCE_CLOSED_GROUP_CENSUS_DRIFT')
    if term.get('strong_local_logical_call_reexecution_count')!=0 or adoption.get('logical_call_reexecution_count')!=0: raise RuntimeError('R1_WAVE1_REEXECUTION_DRIFT')
    round_id=str(term['round_id']); policy_version=str(term['parent_policy_id']); source_q_wave_sha=sha64(term['source_q_wave_sha256'],'SOURCE_Q_WAVE')
    qroot=discover_qroot(rroot,source_q_wave_sha); qwave=load_json(qroot/'V1232Q_STRONG_LOCAL_WAVE_TERMINAL_V1.json')
    if qwave.get('wave_sha256')!=source_q_wave_sha: raise RuntimeError('Q_WAVE_IDENTITY_MISMATCH')
    qexec=load_json(qroot/'strong_local_runtime/execution_manifest.json'); qrows=qexec.get('rows')
    if not isinstance(qrows,list): raise RuntimeError('Q_EXECUTION_ROWS_INVALID')
    if len(qrows)!=qwave.get('selected_source_count')*2: raise RuntimeError('Q_EXECUTION_CARDINALITY_NOT_FULL_FROZEN_WAVE')
    repo,role_auth=discover_strong_repo(rroot); repo_identity=tracked_repo_identity(repo); head=repo_identity['head_oid']; object_format=repo_identity['object_format']; import_repo(repo); api=preflight_api()
    from pchsi.reference_loop.canonical import domain_hash
    # Exact historical Analyzer Memory dependency; paths/SHA come from repository authority.
    dep_path=repo/'configs/memory/package_b_failure_memory_dependency_v1.json'; contract_path=repo/'configs/memory/failure_memory_token_budget_contract_v1.json'
    dep=load_json(dep_path); contract=load_json(contract_path)
    snapshot_dir=Path(str(dep.get('active_snapshot_external_directory')))
    snapshot_sha=sha64(dep.get('active_snapshot_sha256'),'ANALYZER_MEMORY_SNAPSHOT')
    contract_sha=sha64(dep.get('token_budget_contract_sha256'),'ANALYZER_MEMORY_CONTRACT')
    if contract.get('contract_sha256')!=contract_sha: raise RuntimeError('ANALYZER_MEMORY_DEPENDENCY_CONTRACT_MISMATCH')
    snapshot=api['load_calibrated_dev_snapshot_v2'](snapshot_directory=snapshot_dir,expected_snapshot_sha256=snapshot_sha,token_budget_contract_path=contract_path,expected_token_budget_contract_sha256=contract_sha)
    role_path=repo/'docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json'
    activation=domain_hash('V1232T_ANALYZER_TAIL_ACTIVATION_V1',{'r1_terminal_sha256':term['terminal_sha256'],'r1_prep_sha256':prep['prep_sha256'],'fixed_repo_head_oid':head,'fixed_repo_object_format':object_format,'role_authority_file_sha256':sha256_file(role_path),'analyzer_memory_snapshot_sha256':snapshot_sha,'analyzer_memory_contract_sha256':contract_sha})
    out=find_badcase_root(rroot)/'new_human_pi1/control/v1232t_strong_analyzer_group_tail_dynamic_pair_universe'/activation
    if out.is_symlink() or not out.is_dir(): raise RuntimeError('V1232T_RECOVERY_OUTPUT_ROOT_NOT_FOUND:'+str(out))
    runtime_root=out/'strong_group_runtime'; runtime_root.mkdir(parents=True,exist_ok=True)
    # Map accepted A1 bytes + task-access authority from the immutable Q wave.
    a1_by_sha={}; access_by_source={}; source_unit_by_local={}
    complete=set(adoption.get('complete_source_unit_ids') or [])
    for row in qrows:
        if not isinstance(row,dict) or row.get('stage_id')!='L-A1' or row.get('source_unit_id') not in complete or row.get('status')!='ACCEPTED': continue
        art=load_json(Path(str(row['call_dir']))/'validated_artifact.json'); lsha=sha64(art.get('local_result_sha256'),'A1_LOCAL_RESULT')
        if lsha in a1_by_sha: raise RuntimeError('DUPLICATE_A1_LOCAL_RESULT_SHA')
        a1_by_sha[lsha]=Path(str(row['call_dir']))/'validated_artifact.json'; source_unit_by_local[lsha]=str(row['source_unit_id'])
    for sid in complete:
        access=load_json(qroot/'units'/sid/'task_access_record.json'); access_by_source[str(sid)]=access
    group_rows=list(prep.get('groups') or [])
    group_manifest_shas=[sha64(x.get('group_manifest_sha256'),'GROUP_MANIFEST') for x in group_rows]
    group_universe=api['build_group_universe'](round_id=round_id,group_manifest_sha256s=group_manifest_shas); write_or_verify_json(out/'CLEAN_ANALYZER_GROUP_UNIVERSE_V1.json',group_universe)
    runtime_manifest=api['load_runtime_manifest'](); stage_rows=[dict(x) for x in runtime_manifest['stage_rows'] if x.get('stage_id') in {'G-A2','G-A3'}]
    group_budget=api['build_round_group_analyzer_resource_authority'](round_id=round_id,policy_version=policy_version,producer_role='REFERENCE_EXPERIMENT_CONTRACT',source_authority_sha256=prep['prep_sha256'],group_universe=group_universe,group_stage_rows=stage_rows); api['validate_round_group_analyzer_resource_authority'](group_budget); write_or_verify_json(out/'ROUND_GROUP_ANALYZER_RESOURCE_AUTHORITY_V1.json',group_budget)
    # Preserve the original rollout handoff as the round-evidence identity in G/C/X identities.
    sample_sid=next(iter(sorted(complete))); sample_sm=load_json(qroot/'units'/sample_sid/'source_unit_manifest.json'); round_evidence_sha=sha64(sample_sm.get('rollout_handoff_sha256'),'ROLLOUT_HANDOFF')
    g_records=[]; group_runtime_index=[]; group_context_rows_all=[]; group_memory_paths={}; common_projection_paths={}; group_accesses={}; group_manifests_by_id={}
    counters={'provider_calls':0,'terminal_reuse':0,'g_terminal_adoption':0,'g_provider_call_reexecution':0,'same_logical_call_resend':0,'automatic_retry':0,'replacement_group':0,'top_up_group':0,'human_scientific_decision':0,'g_quarantined':0,'g_incomplete':0,'g_complete_pair':0,'c_requested':0,'x_requested':0}
    global_hard_stop=None
    for ordinal,grow in enumerate(sorted(group_rows,key=lambda x:str(x['group_id']))):
        gid=str(grow['group_id']); gdir=out/'groups'/gid; gdir.mkdir(parents=True,exist_ok=True)
        manifest_path=Path(str(grow['group_manifest_path'])); synth_path=Path(str(grow['group_synthesis_input_path'])); contexts_path=Path(str(grow['source_contexts_path']))
        manifest=load_json(manifest_path); synthesis=load_json(synth_path); contexts=load_json_value(contexts_path)
        if not isinstance(contexts,list) or not contexts: raise RuntimeError('GROUP_SOURCE_CONTEXTS_INVALID:'+gid)
        if manifest.get('group_id')!=gid or manifest.get('group_manifest_sha256')!=grow.get('group_manifest_sha256'): raise RuntimeError('R1_GROUP_MANIFEST_IDENTITY_DRIFT:'+gid)
        for ctx in contexts:
            if not isinstance(ctx,dict): raise RuntimeError('GROUP_SOURCE_CONTEXT_ROW_INVALID:'+gid)
            group_context_rows_all.append(dict(ctx))
        local_paths=[]
        for m in synthesis.get('member_rows') or []:
            p=a1_by_sha.get(str(m.get('local_result_sha256')))
            if p is None: raise RuntimeError('GROUP_MEMBER_A1_BYTES_MISSING:'+gid)
            local_paths.append(p)
        memory_pack=build_group_memory_pack(contexts=contexts,snapshot=snapshot,api=api,domain_hash=domain_hash); memory_path=gdir/'analyzer_memory_pack.json'; write_or_verify_json(memory_path,memory_pack); group_memory_paths[gid]=memory_path
        group_access=api['build_clean_group_task_access_record'](round_id=round_id,group_id=gid,group_manifest_sha256=manifest['group_manifest_sha256'],member_contexts=contexts,task_access_by_source_unit=access_by_source); write_or_verify_json(gdir/'group_task_access_record.json',group_access); group_accesses[gid]=group_access
        p_a2=api['group_projection_v3'](group_manifest_path=manifest_path,group_synthesis_input_path=synth_path,a1_local_result_paths=local_paths,source_contexts_path=contexts_path,memory_pack_path=None)
        p_a3=api['group_projection_v3'](group_manifest_path=manifest_path,group_synthesis_input_path=synth_path,a1_local_result_paths=local_paths,source_contexts_path=contexts_path,memory_pack_path=memory_path)
        if strip_memory_projection(p_a2)!=strip_memory_projection(p_a3): raise RuntimeError('G_A2_A3_COMMON_EVIDENCE_MISMATCH:'+gid)
        pa2_path=gdir/'projection_G_A2.json'; pa3_path=gdir/'projection_G_A3.json'; write_or_verify_json(pa2_path,p_a2); write_or_verify_json(pa3_path,p_a3); common_projection_paths[gid]=pa2_path
        group_manifests_by_id[gid]=manifest_path
        identity=api['build_scientific_unit_identity'](scientific_unit_type='GROUP',scientific_unit_id=gid,source_unit_manifest_sha256=synthesis['group_synthesis_input_sha256'],task_set_manifest_sha256=group_universe['group_universe_sha256'],task_id=None,gamefile_sha256=None,group_manifest_sha256=manifest['group_manifest_sha256'],round_evidence_package_sha256=round_evidence_sha)
        write_or_verify_json(gdir/'scientific_unit_identity.json',identity)
        results={}; unsafe=False
        for stage,cond,proj in (('G-A2','A2',p_a2),('G-A3','A3',p_a3)):
            if unsafe: break
            result=adopt_terminal_call_only(runtime_root=runtime_root,unit_identity=identity,stage_id=stage,condition_id=cond,round_id=round_id,policy_version=policy_version,projection=proj,api=api,domain_hash=domain_hash); results[stage]=result
            counters['g_terminal_adoption']+=1
            if result.get('hard_stop') is True:
                if result.get('status')=='AMBIGUOUS_POST_SEND': unsafe=True; counters['g_quarantined']+=1
                else: global_hard_stop={'stage':stage,'group_id':gid,'result':result}; break
        if global_hard_stop: break
        complete=results.get('G-A2',{}).get('status')=='ACCEPTED' and results.get('G-A3',{}).get('status')=='ACCEPTED'
        if complete: counters['g_complete_pair']+=1
        elif not unsafe: counters['g_incomplete']+=1
        rec={'group_id':gid,'group_ordinal':ordinal,'A2':results.get('G-A2'),'A3':results.get('G-A3'),'complete_pair':complete,'quarantined_ambiguous':unsafe,'memory_pack_sha256':memory_pack['memory_pack_sha256'],'group_task_access_sha256':group_access['group_task_access_sha256']}
        g_records.append(rec); group_runtime_index.append({'group_id':gid,'group_dir':str(gdir),'complete_pair':complete})
    if global_hard_stop:
        fail={'schema_id':'V1232U_ANALYZER_TAIL_HARD_STOP_V1','schema_version':1,'round_id':round_id,'hard_stop':global_hard_stop,'automatic_retry_count':0,'same_logical_call_resend_count':0,'human_disposition_required':False}
        write_or_verify_json(out/'V1232U_ANALYZER_TAIL_HARD_STOP_V1.json',fail); print('STATUS=V1232U_ANALYZER_TAIL_FAIL_CLOSED_HARD_STOP'); print('V1232U_OUTPUT_ROOT='+str(out)); print('HUMAN_DISPOSITION_REQUIRED=false'); return 20
    g_adoption={'schema_id':'V1232U_T_G_TERMINAL_ADOPTION_V1','schema_version':1,'round_id':round_id,'source_v1232t_output_root':str(out),'source_r1_terminal_sha256':term['terminal_sha256'],'source_closed_group_count':len(group_rows),'adopted_terminal_g_call_count':counters['g_terminal_adoption'],'g_complete_pair_group_count':counters['g_complete_pair'],'g_quarantined_group_count':counters['g_quarantined'],'g_incomplete_group_count':counters['g_incomplete'],'g_provider_call_reexecution_count':0,'automatic_retry_count':0,'replacement_group_count':0,'top_up_group_count':0,'human_disposition_required':False,'adoption_sha256':'0'*64}
    g_adoption['adoption_sha256']=domain_hash('V1232U_T_G_TERMINAL_ADOPTION_V1',g_adoption,excluded_field='adoption_sha256'); write_or_verify_json(out/'V1232U_T_G_TERMINAL_ADOPTION_V1.json',g_adoption)
    complete_g=[x for x in g_records if x['complete_pair']]
    if not complete_g: raise RuntimeError('NO_COMPLETE_G_PAIRS')
    # C stage: one C call for every accepted G result in complete pairs.
    accepted_g=[]; c_records=[]
    for grec in complete_g:
        gid=grec['group_id']; gdir=out/'groups'/gid
        for stage in ('G-A2','G-A3'):
            res=formal_group_stage_result(grec,stage); call_dir=Path(str(res['call_dir'])); artifact_path=call_dir/'validated_artifact.json'; gart=load_json(artifact_path); gsha=sha64(gart.get('group_result_sha256'),'GROUP_RESULT')
            accepted_g.append({'group_id':gid,'stage_id':stage,'artifact_path':str(artifact_path),'group_result_sha256':gsha,'artifact':gart})
            cproj=api['component_projection'](artifact_path)
            cid=api['build_scientific_unit_identity'](scientific_unit_type='GROUP',scientific_unit_id=gid+'::'+stage,source_unit_manifest_sha256=gsha,task_set_manifest_sha256=group_universe['group_universe_sha256'],task_id=None,gamefile_sha256=None,group_manifest_sha256=sha64(gart.get('group_manifest_sha256'),'GROUP_MANIFEST'),round_evidence_package_sha256=round_evidence_sha)
            result=execute_or_reuse(runtime_root=runtime_root,unit_identity=cid,stage_id='C',condition_id=None,round_id=round_id,policy_version=policy_version,projection=cproj,task_access=group_accesses[gid],api=api,domain_hash=domain_hash); counters['c_requested']+=1
            if result.get('reused_terminal_call'): counters['terminal_reuse']+=1
            else: counters['provider_calls']+=1
            if result.get('hard_stop') is True and result.get('status')!='AMBIGUOUS_POST_SEND':
                fail={'schema_id':'V1232U_ANALYZER_TAIL_HARD_STOP_V1','schema_version':1,'round_id':round_id,'hard_stop':{'stage':'C','group_id':gid,'result':result},'automatic_retry_count':0,'same_logical_call_resend_count':0,'human_disposition_required':False}; write_or_verify_json(out/'V1232U_ANALYZER_TAIL_HARD_STOP_V1.json',fail); print('STATUS=V1232U_ANALYZER_TAIL_FAIL_CLOSED_HARD_STOP'); print('V1232U_OUTPUT_ROOT='+str(out)); return 20
            c_records.append({'group_id':gid,'target_stage_id':stage,'group_result_sha256':gsha,'result':result})
    registered={x['group_result_sha256']:x['artifact'] for x in accepted_g}; attributions=[]
    for row in c_records:
        if row['result'].get('status')=='ACCEPTED': attributions.append(load_json(Path(str(row['result']['call_dir']))/'validated_artifact.json'))
    profile=api['aggregate_capability_profile'](attributions,registered_group_results=registered); behavior=api['build_policy_behavior_profile'](profile); write_or_verify_json(out/'ANALYZER_CAPABILITY_PROFILE_V1.json',profile); write_or_verify_json(out/'ANALYZER_POLICY_BEHAVIOR_PROFILE_V1.json',behavior)
    # X stage only for proposal-bearing accepted G results from complete G pairs.
    x_records=[]; x_by_gsha={}
    for item in accepted_g:
        gart=item['artifact']; proposals=gart.get('source_conditioned_proposals')
        if not isinstance(proposals,list): raise RuntimeError('GROUP_PROPOSALS_NOT_ARRAY')
        if not proposals: continue
        gid=item['group_id']; stage=item['stage_id']; memory_path=None if stage=='G-A2' else group_memory_paths[gid]
        xproj=api['crosscheck_projection_v2'](target_path=Path(item['artifact_path']),target_stage_id=stage,group_manifest_path=group_manifests_by_id[gid],common_group_projection_path=common_projection_paths[gid],memory_pack_path=memory_path)
        xdir=out/'groups'/gid; xp=xdir/('projection_X_'+stage.replace('-','_')+'.json'); write_or_verify_json(xp,xproj)
        xid=api['build_scientific_unit_identity'](scientific_unit_type='CROSSCHECK_TARGET',scientific_unit_id=item['group_result_sha256'],source_unit_manifest_sha256=item['group_result_sha256'],task_set_manifest_sha256=group_universe['group_universe_sha256'],task_id=None,gamefile_sha256=None,group_manifest_sha256=sha64(gart.get('group_manifest_sha256'),'GROUP_MANIFEST'),round_evidence_package_sha256=round_evidence_sha)
        result=execute_or_reuse(runtime_root=runtime_root,unit_identity=xid,stage_id='X',condition_id=None,round_id=round_id,policy_version=policy_version,projection=xproj,task_access=group_accesses[gid],api=api,domain_hash=domain_hash); counters['x_requested']+=1
        if result.get('reused_terminal_call'): counters['terminal_reuse']+=1
        else: counters['provider_calls']+=1
        if result.get('hard_stop') is True and result.get('status')!='AMBIGUOUS_POST_SEND':
            fail={'schema_id':'V1232U_ANALYZER_TAIL_HARD_STOP_V1','schema_version':1,'round_id':round_id,'hard_stop':{'stage':'X','group_id':gid,'target_stage_id':stage,'result':result},'automatic_retry_count':0,'same_logical_call_resend_count':0,'human_disposition_required':False}; write_or_verify_json(out/'V1232U_ANALYZER_TAIL_HARD_STOP_V1.json',fail); print('STATUS=V1232U_ANALYZER_TAIL_FAIL_CLOSED_HARD_STOP'); print('V1232U_OUTPUT_ROOT='+str(out)); return 20
        xrow={'group_id':gid,'target_stage_id':stage,'group_result_sha256':item['group_result_sha256'],'result':result}; x_records.append(xrow)
        if result.get('status')=='ACCEPTED': xart=load_json(Path(str(result['call_dir']))/'validated_artifact.json'); x_by_gsha[item['group_result_sha256']]=xart
    tail={'schema_id':'V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1','schema_version':1,'status':'STRONG_ANALYZER_G_A2_A3_C_P_X_CLOSED','round_id':round_id,'parent_policy_id':policy_version,'fixed_repo_head_oid':head,'fixed_repo_object_format':object_format,'source_r1_terminal_sha256':term['terminal_sha256'],'source_closed_group_count':len(group_rows),'source_v1232t_g_adoption_sha256':g_adoption['adoption_sha256'],'adopted_terminal_g_call_count':counters['g_terminal_adoption'],'g_provider_call_reexecution_count':0,'g_complete_pair_group_count':counters['g_complete_pair'],'g_quarantined_group_count':counters['g_quarantined'],'g_incomplete_group_count':counters['g_incomplete'],'c_request_count':counters['c_requested'],'c_accepted_count':len(attributions),'deterministic_p_materialized':True,'x_request_count':counters['x_requested'],'x_accepted_count':len(x_by_gsha),'provider_call_count':counters['provider_calls'],'terminal_call_reuse_count':counters['terminal_reuse'],'automatic_retry_count':0,'same_logical_call_resend_count':0,'replacement_group_count':0,'top_up_group_count':0,'outcome_adaptive_selection_used':False,'environment_call_count':0,'training_execution_count':0,'human_scientific_decision_count':0,'profile_sha256':profile['profile_sha256'],'policy_profile_sha256':behavior['policy_profile_sha256'],'terminal_sha256':'0'*64}
    tail['terminal_sha256']=domain_hash('V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1',tail,excluded_field='terminal_sha256'); write_or_verify_json(out/'V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1.json',tail)
    # Dynamic Planner pair-universe resolution: exact execution context + validated X + existing candidate/K<=1 APIs.
    context_index=index_source_contexts(group_context_rows_all)
    candidates_by={(state,cond):[] for state in context_index for cond in ('A2','A3')}; x_missing=[]; projection_fail=[]; candidate_rows=[]
    for item in accepted_g:
        cond='A2' if item['stage_id']=='G-A2' else 'A3'; gart=item['artifact']; gsha=item['group_result_sha256']; proposals=gart.get('source_conditioned_proposals') or []
        if not proposals: continue
        xart=x_by_gsha.get(gsha)
        if xart is None:
            for p in proposals: x_missing.append({'group_result_sha256':gsha,'condition_id':cond,'source_state_sha256':p.get('source_state_sha256'),'local_result_sha256':p.get('local_result_sha256'),'error_instance_id':p.get('error_instance_id'),'reason':'PROPOSAL_BEARING_G_RESULT_LACKS_ACCEPTED_X'})
            continue
        disposition=str(xart.get('disposition'))
        for proposal in proposals:
            state=str(proposal.get('source_state_sha256')); entry=context_index.get(state)
            if entry is None: projection_fail.append({'group_result_sha256':gsha,'condition_id':cond,'reason':'SOURCE_CONTEXT_STATE_MISSING','source_state_sha256':state}); continue
            try:
                exec_ctx=source_context_for_candidate_projection(entry); candidate=api['project_candidate'](proposal=proposal,source_state=exec_ctx,candidate_kind='FAILURE_REPAIR',crosscheck_disposition=disposition)
            except Exception as e:
                projection_fail.append({'group_result_sha256':gsha,'condition_id':cond,'source_state_sha256':state,'reason':type(e).__name__+':'+str(e)}); continue
            candidates_by.setdefault((state,cond),[]).append(candidate); candidate_rows.append({'group_result_sha256':gsha,'condition_id':cond,'formal_x_disposition':disposition,'source_context_audit':source_context_audit_summary(entry),'candidate':candidate})
    if projection_fail:
        write_or_verify_json(out/'V1232U_CANDIDATE_PROJECTION_FAILURE_V1.json',{'schema_id':'V1232U_CANDIDATE_PROJECTION_FAILURE_V1','schema_version':1,'count':len(projection_fail),'rows':projection_fail,'human_disposition_required':False})
        print('STATUS=V1232U_DYNAMIC_PAIR_UNIVERSE_FAIL_CLOSED_CANDIDATE_PROJECTION'); print('V1232U_OUTPUT_ROOT='+str(out)); return 21
    candidate_by_sha={}; candidate_meta_by_sha={}
    for row in candidate_rows:
        csha=sha64(row['candidate'].get('candidate_sha256'),'CANDIDATE')
        prior=candidate_by_sha.get(csha)
        if prior is not None and canonical_bytes(prior)!=canonical_bytes(row['candidate']):
            raise RuntimeError('CANDIDATE_SHA_BYTES_CONFLICT:'+csha)
        candidate_by_sha[csha]=row['candidate']
        candidate_meta_by_sha.setdefault(csha,[]).append(row)
    materializations=[]; k1_collisions=0; condition_registered={'A2':0,'A3':0}; complete_pairs=[]
    for state in sorted(context_index):
        mats={}
        for cond in ('A2','A3'):
            raw=candidates_by.get((state,cond),[]); zero='METHOD_X_UNAVAILABLE' if any(x.get('condition_id')==cond and x.get('source_state_sha256')==state for x in x_missing) else 'NO_FORMAL_PROPOSAL'
            mat=api['materialize_state_condition_k1'](condition_id=cond,source_state_sha256=state,candidates=raw,zero_candidate_disposition=zero); mats[cond]=mat
            if mat.get('formal_disposition')=='FORMAL_CANDIDATE_REGISTERED': condition_registered[cond]+=1
            if mat.get('formal_disposition')=='METHOD_INVALID_K1_STATE_BUDGET_COLLISION': k1_collisions+=1
            materializations.append(mat)
        if all(mats[c].get('formal_disposition')=='FORMAL_CANDIDATE_REGISTERED' for c in ('A2','A3')):
            entry=context_index[state]
            pair={'state_index':len(complete_pairs),'source_state_sha256':state,'source_context':source_context_for_candidate_projection(entry),'source_context_audit':source_context_audit_summary(entry),'A2':{'candidate_sha256':mats['A2']['selected_candidate_sha256'],'selected_execution_identity_sha256':mats['A2']['selected_execution_identity_sha256']},'A3':{'candidate_sha256':mats['A3']['selected_candidate_sha256'],'selected_execution_identity_sha256':mats['A3']['selected_execution_identity_sha256']}}
            # Include exact candidate bytes and X disposition for downstream Dynamic PRE/F0F1 binders.
            for cond in ('A2','A3'):
                csha=pair[cond]['candidate_sha256']; candidate=candidate_by_sha.get(csha); matches=candidate_meta_by_sha.get(csha,[])
                if candidate is None or not matches: raise RuntimeError('SELECTED_CANDIDATE_BYTES_MISSING:'+state+':'+cond)
                condition_matches=[r for r in matches if r['condition_id']==cond]
                if not condition_matches: raise RuntimeError('SELECTED_CANDIDATE_CONDITION_PROVENANCE_MISSING:'+state+':'+cond)
                pair[cond]['candidate']=candidate; pair[cond]['candidate_provenance']=[{'group_result_sha256':r['group_result_sha256'],'formal_x_disposition':r['formal_x_disposition']} for r in condition_matches]
                pair[cond]['group_result_sha256s']=sorted({r['group_result_sha256'] for r in condition_matches}); pair[cond]['formal_x_dispositions']=sorted({r['formal_x_disposition'] for r in condition_matches})
            complete_pairs.append(pair)
    pair_universe={'schema_id':'V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1','schema_version':1,'round_id':round_id,'parent_policy_id':policy_version,'analyzer_tail_terminal_sha256':tail['terminal_sha256'],'source_state_count':len(context_index),'condition_registered_count':condition_registered,'complete_pair_count':len(complete_pairs),'k1_collision_count':k1_collisions,'candidate_count':len(candidate_rows),'x_missing_candidate_source_count':len(x_missing),'source_context_execution_state_count':len(context_index),'source_context_provenance_variant_count':sum(x['provenance_variant_count'] for x in [source_context_audit_summary(v) for v in context_index.values()]),'pair_table':complete_pairs,'legacy_fixed_cardinality_assumed':False,'dynamic_pre_v2_required':True,'provider_call_count':0,'environment_call_count':0,'training_execution_count':0,'human_pair_selection_count':0,'pair_universe_sha256':'0'*64}
    pair_universe['pair_universe_sha256']=domain_hash('V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1',pair_universe,excluded_field='pair_universe_sha256'); write_or_verify_json(out/'V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json',pair_universe)
    write_or_verify_json(out/'V1232U_GROUP_STAGE_EXECUTION_CENSUS_V1.json',{'schema_id':'V1232U_GROUP_STAGE_EXECUTION_CENSUS_V1','schema_version':1,'round_id':round_id,'groups':g_records,'c_records':c_records,'x_records':x_records,'counters':counters})
    final={'schema_id':'PCHSI_V1232U_TERMINAL_V1','schema_version':1,'status':'STRONG_ANALYZER_TAIL_CLOSED_DYNAMIC_PLANNER_PAIR_UNIVERSE_READY','round_id':round_id,'parent_policy_id':policy_version,'source_r1_terminal_sha256':term['terminal_sha256'],'analyzer_tail_terminal_sha256':tail['terminal_sha256'],'dynamic_pair_universe_sha256':pair_universe['pair_universe_sha256'],'source_closed_group_count':len(group_rows),'source_v1232t_g_adoption_sha256':g_adoption['adoption_sha256'],'adopted_terminal_g_call_count':counters['g_terminal_adoption'],'g_provider_call_reexecution_count':0,'g_complete_pair_group_count':counters['g_complete_pair'],'g_quarantined_group_count':counters['g_quarantined'],'g_incomplete_group_count':counters['g_incomplete'],'c_request_count':counters['c_requested'],'x_request_count':counters['x_requested'],'dynamic_planner_pair_count':len(complete_pairs),'k1_collision_count':k1_collisions,'provider_call_count':counters['provider_calls'],'terminal_call_reuse_count':counters['terminal_reuse'],'automatic_retry_count':0,'same_logical_call_resend_count':0,'replacement_group_count':0,'top_up_group_count':0,'environment_call_count':0,'training_execution_count':0,'human_scientific_decision_count':0,'next':'EXISTING_DYNAMIC_STRONG_PLANNER_PRE_V2_THEN_CURRENT_SAME_STATE_F0F1_VERIFIER_POST_TRAIN_NO_TRAIN','terminal_sha256':'0'*64}
    final['terminal_sha256']=domain_hash('PCHSI_V1232U_TERMINAL_V1',final,excluded_field='terminal_sha256'); write_or_verify_json(out/'PCHSI_V1232U_TERMINAL_V1.json',final)
    print('STATUS=V1232U_T_G_TERMINALS_ADOPTED_ANALYZER_TAIL_CLOSED_DYNAMIC_PLANNER_PAIR_UNIVERSE_READY')
    print('V1232U_OUTPUT_ROOT='+str(out)); print('V1232U_T_G_TERMINAL_ADOPTED_CALL_COUNT='+str(counters['g_terminal_adoption'])); print('V1232U_G_PROVIDER_CALL_REEXECUTION_COUNT=0'); print('V1232U_SOURCE_CLOSED_GROUP_COUNT='+str(len(group_rows))); print('V1232U_G_COMPLETE_PAIR_GROUP_COUNT='+str(counters['g_complete_pair'])); print('V1232U_G_QUARANTINED_GROUP_COUNT='+str(counters['g_quarantined'])); print('V1232U_G_INCOMPLETE_GROUP_COUNT='+str(counters['g_incomplete'])); print('V1232U_C_REQUEST_COUNT='+str(counters['c_requested'])); print('V1232U_X_REQUEST_COUNT='+str(counters['x_requested'])); print('V1232U_DYNAMIC_PLANNER_PAIR_COUNT='+str(len(complete_pairs))); print('V1232U_K1_COLLISION_COUNT='+str(k1_collisions)); print('V1232U_PROVIDER_CALL_COUNT='+str(counters['provider_calls'])); print('V1232U_SAME_LOGICAL_CALL_RESEND_COUNT=0'); print('HUMAN_SCIENTIFIC_DECISION_COUNT=0'); print('V1232U_NEXT='+final['next']); return 0

if __name__=='__main__': raise SystemExit(main())
