from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f'REQUIRED_REGULAR_JSON_MISSING:{path}')
    v = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(v, dict):
        raise RuntimeError(f'JSON_OBJECT_REQUIRED:{path}')
    return v


def write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new_value(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new_bytes(path: Path, payload: bytes) -> None:
    if not isinstance(payload, bytes):
        raise TypeError('payload must be bytes')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view=memoryview(payload)
        while view:
            written=os.write(fd,view)
            if written<=0:
                raise OSError('write made no progress')
            view=view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def canonical_jsonl_bytes(rows: list[Mapping[str, Any]]) -> bytes:
    return b''.join(
        json.dumps(dict(row), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8') + b'\n'
        for row in rows
    )


def _require_abs_regular_file(path_text: object, label: str) -> Path:
    if not isinstance(path_text, str) or not path_text:
        raise RuntimeError(label+'_PATH_MISSING')
    p=Path(path_text)
    if not p.is_absolute():
        raise RuntimeError(label+'_PATH_NOT_ABSOLUTE:'+path_text)
    if p.is_symlink() or not p.is_file():
        raise RuntimeError(label+'_PATH_NOT_REGULAR:'+path_text)
    if p.resolve()!=p:
        raise RuntimeError(label+'_PATH_HAS_SYMLINK_COMPONENT:'+path_text)
    return p


def _require_abs_regular_dir(path_text: object, label: str) -> Path:
    if not isinstance(path_text, str) or not path_text:
        raise RuntimeError(label+'_PATH_MISSING')
    p=Path(path_text)
    if not p.is_absolute():
        raise RuntimeError(label+'_PATH_NOT_ABSOLUTE:'+path_text)
    if p.is_symlink() or not p.is_dir():
        raise RuntimeError(label+'_PATH_NOT_REGULAR_DIR:'+path_text)
    if p.resolve()!=p:
        raise RuntimeError(label+'_PATH_HAS_SYMLINK_COMPONENT:'+path_text)
    return p


def recover_bundle_authorities(
    *,
    state_root: Path,
    handoff: Mapping[str, Any],
    index: Mapping[str, Any],
    failure_ids: list[object],
    attempt_receipt_type,
    episode_artifact_type,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Recover exact attempt directories from bounded shard-terminal authority.

    V1232K cell rows persist attempt_bundle_root + execution_attempt_id. The
    global bundle index accidentally projected a nonexistent attempt_bundle_path
    field as null. This resolver never scans the filesystem broadly and never
    invents a path from a task ID.
    """
    if index.get('schema_id')!='ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1':
        raise RuntimeError('ATTEMPT_BUNDLE_INDEX_SCHEMA_MISMATCH')
    idx_rows=index.get('rows')
    if not isinstance(idx_rows,list) or index.get('row_count')!=len(idx_rows):
        raise RuntimeError('ATTEMPT_BUNDLE_INDEX_ROWS_INVALID')
    shard_count=handoff.get('shard_count')
    if type(shard_count) is not int or shard_count<=0:
        raise RuntimeError('HANDOFF_SHARD_COUNT_INVALID')

    # Load only the finite shard set declared by the handoff.
    shard_rows: dict[tuple[int,int], dict[str,Any]]={}
    for shard_id in range(shard_count):
        shard_root=state_root/'shards'/f'{shard_id:04d}'
        terminal_path=shard_root/'PCHSI_V1232S_SHARD_TERMINALS_V1.json'
        terminal=load_json(terminal_path)
        if terminal.get('schema_id')!='PCHSI_V1232S_SHARD_TERMINALS_V1' or terminal.get('shard_id')!=shard_id:
            raise RuntimeError('SHARD_TERMINAL_AUTHORITY_MISMATCH:'+str(shard_id))
        rows=terminal.get('rows')
        if not isinstance(rows,list):
            raise RuntimeError('SHARD_TERMINAL_ROWS_INVALID:'+str(shard_id))
        for row in rows:
            if not isinstance(row,dict):
                raise RuntimeError('SHARD_TERMINAL_ROW_NOT_OBJECT:'+str(shard_id))
            ordinal=row.get('global_ordinal')
            if type(ordinal) is not int:
                raise RuntimeError('SHARD_TERMINAL_GLOBAL_ORDINAL_INVALID:'+str(shard_id))
            key=(shard_id,ordinal)
            if key in shard_rows:
                raise RuntimeError('SHARD_TERMINAL_DUPLICATE_ORDINAL:'+repr(key))
            shard_rows[key]=row

    index_by_cell: dict[str, dict[str,Any]]={}
    index_ordinals=set()
    null_index_paths=0
    for row in idx_rows:
        if not isinstance(row,dict):
            raise RuntimeError('ATTEMPT_BUNDLE_INDEX_ROW_NOT_OBJECT')
        cid=row.get('scientific_cell_id'); ordinal=row.get('global_ordinal'); shard_id=row.get('shard_id')
        if not isinstance(cid,str) or not cid or type(ordinal) is not int or type(shard_id) is not int:
            raise RuntimeError('ATTEMPT_BUNDLE_INDEX_IDENTITY_INVALID')
        if cid in index_by_cell or ordinal in index_ordinals:
            raise RuntimeError('ATTEMPT_BUNDLE_INDEX_DUPLICATE_IDENTITY')
        if not 0<=shard_id<shard_count:
            raise RuntimeError('ATTEMPT_BUNDLE_INDEX_SHARD_OUT_OF_RANGE:'+str(shard_id))
        sr=shard_rows.get((shard_id,ordinal))
        if sr is None:
            raise RuntimeError('INDEX_ROW_MISSING_SHARD_TERMINAL:'+cid)
        for field in ('scientific_cell_id','global_ordinal','shard_id'):
            if sr.get(field)!=row.get(field):
                raise RuntimeError('INDEX_SHARD_TERMINAL_IDENTITY_MISMATCH:'+field+':'+cid)
        idx_terminal=row.get('attempt_terminal_path')
        if idx_terminal is not None and idx_terminal!=sr.get('attempt_terminal_path'):
            raise RuntimeError('INDEX_ATTEMPT_TERMINAL_PATH_MISMATCH:'+cid)
        if row.get('attempt_bundle_path') is None:
            null_index_paths+=1
        index_by_cell[cid]=row
        index_ordinals.add(ordinal)

    resolved: dict[str, dict[str,Any]]={}
    recovery_rows=[]
    for raw_cid in failure_ids:
        cid=str(raw_cid)
        idx=index_by_cell.get(cid)
        if idx is None:
            raise RuntimeError('FAILURE_CELL_MISSING_FROM_BUNDLE_INDEX:'+cid)
        shard_id=int(idx['shard_id']); ordinal=int(idx['global_ordinal'])
        sr=shard_rows[(shard_id,ordinal)]
        if sr.get('status')!='SCIENTIFIC_FAILURE' or sr.get('success') is not False:
            raise RuntimeError('FAILURE_COHORT_TERMINAL_NOT_SCIENTIFIC_FAILURE:'+cid)
        attempt_id=sr.get('execution_attempt_id')
        if not isinstance(attempt_id,str) or not attempt_id:
            raise RuntimeError('SHARD_TERMINAL_EXECUTION_ATTEMPT_ID_INVALID:'+cid)

        # Verify the per-cell sidecar whose SHA is frozen into the shard terminal.
        sidecar=state_root/'shards'/f'{shard_id:04d}'/'cell_terminals'/f'{ordinal:05d}.json'
        if sidecar.is_symlink() or not sidecar.is_file():
            raise RuntimeError('CELL_TERMINAL_SIDECAR_MISSING:'+cid)
        expected_sidecar_sha=sr.get('terminal_receipt_sha256')
        if not isinstance(expected_sidecar_sha,str) or sha256_file(sidecar)!=expected_sidecar_sha:
            raise RuntimeError('CELL_TERMINAL_SIDECAR_SHA_MISMATCH:'+cid)
        sidecar_obj=load_json(sidecar)
        for field in ('global_ordinal','shard_id','scientific_cell_id','execution_attempt_id','task_id','task_index','status','success','attempt_terminal_path','attempt_bundle_root'):
            if sidecar_obj.get(field)!=sr.get(field):
                raise RuntimeError('CELL_SIDECAR_SHARD_ROW_MISMATCH:'+field+':'+cid)

        terminal_path=_require_abs_regular_file(sr.get('attempt_terminal_path'),'ATTEMPT_TERMINAL')
        expected_terminal_path=(state_root/'shards'/f'{shard_id:04d}'/'rollout_run'/'attempt_ledger'/f'{attempt_id}.terminal.json')
        if terminal_path!=expected_terminal_path:
            raise RuntimeError('ATTEMPT_TERMINAL_PATH_AUTHORITY_MISMATCH:'+cid)
        receipt=attempt_receipt_type.from_json(terminal_path.read_bytes())
        if receipt.receipt_kind!='TERMINAL' or receipt.execution_attempt_id!=attempt_id:
            raise RuntimeError('ATTEMPT_TERMINAL_RECEIPT_IDENTITY_MISMATCH:'+cid)
        if receipt.attempt_bundle_sha256 is None or receipt.episode_semantic_sha256 is None:
            raise RuntimeError('ATTEMPT_TERMINAL_RECEIPT_BUNDLE_IDENTITY_MISSING:'+cid)

        root=_require_abs_regular_dir(sr.get('attempt_bundle_root'),'ATTEMPT_BUNDLE_ROOT')
        expected_root=(state_root/'shards'/f'{shard_id:04d}'/'rollout_run'/'attempts')
        if root!=expected_root:
            raise RuntimeError('ATTEMPT_BUNDLE_ROOT_AUTHORITY_MISMATCH:'+cid)
        bundle_path=root/attempt_id
        if (
            bundle_path.is_symlink()
            or not bundle_path.is_dir()
            or bundle_path.parent!=root
            or bundle_path.resolve()!=bundle_path
        ):
            raise RuntimeError('RESOLVED_ATTEMPT_BUNDLE_PATH_INVALID:'+cid)
        episode_path=bundle_path/'attempt.json'
        if episode_path.is_symlink() or not episode_path.is_file():
            raise RuntimeError('RESOLVED_ATTEMPT_EPISODE_MISSING:'+cid)
        episode=episode_artifact_type.from_json(episode_path.read_bytes())
        if episode.execution_attempt_id!=attempt_id or episode.task_id!=sr.get('task_id') or episode.task_index!=sr.get('task_index'):
            raise RuntimeError('ATTEMPT_EPISODE_SHARD_IDENTITY_MISMATCH:'+cid)
        if episode.episode_semantic_sha256!=receipt.episode_semantic_sha256:
            raise RuntimeError('ATTEMPT_EPISODE_TERMINAL_SEMANTIC_SHA_MISMATCH:'+cid)
        if episode.success is not False:
            raise RuntimeError('FAILURE_COHORT_EPISODE_SUCCESS_MISMATCH:'+cid)

        index_path=idx.get('attempt_bundle_path')
        if index_path is not None:
            if not isinstance(index_path,str) or Path(index_path)!=bundle_path:
                raise RuntimeError('NONNULL_INDEX_BUNDLE_PATH_DISAGREES_WITH_SHARD_AUTHORITY:'+cid)
        resolved[cid]={
            'bundle_path':bundle_path,
            'attempt_bundle_sha256':receipt.attempt_bundle_sha256,
            'episode_semantic_sha256':receipt.episode_semantic_sha256,
            'execution_attempt_id':attempt_id,
            'task_id':episode.task_id,
            'task_index':episode.task_index,
            'task_type':episode.task_type,
            'gamefile_sha256':episode.gamefile_sha256,
            'shard_id':shard_id,
            'global_ordinal':ordinal,
        }
        recovery_rows.append({
            'scientific_cell_id':cid,
            'global_ordinal':ordinal,
            'shard_id':shard_id,
            'execution_attempt_id':attempt_id,
            'resolved_attempt_bundle_path':str(bundle_path),
            'attempt_terminal_path':str(terminal_path),
            'attempt_bundle_sha256':receipt.attempt_bundle_sha256,
            'episode_semantic_sha256':receipt.episode_semantic_sha256,
            'index_attempt_bundle_path_was_null':idx.get('attempt_bundle_path') is None,
        })

    receipt={
        'schema_id':'V1232Q_ATTEMPT_BUNDLE_PATH_AUTHORITY_RECONCILIATION_V1',
        'schema_version':1,
        'handoff_shard_count':shard_count,
        'index_row_count':len(idx_rows),
        'failure_cohort_count':len(failure_ids),
        'resolved_failure_bundle_count':len(resolved),
        'null_index_attempt_bundle_path_count':null_index_paths,
        'resolution_authority':'BOUNDED_SHARD_TERMINAL_ATTEMPT_BUNDLE_ROOT_PLUS_EXECUTION_ATTEMPT_ID',
        'filesystem_wide_discovery_used':False,
        'filename_task_id_inference_used':False,
        'human_path_selection_performed':False,
        'rows':recovery_rows,
        'receipt_sha256':'0'*64,
    }
    return resolved,receipt


def find_badcase_root(state_root: Path) -> Path:
    for p in [state_root, *state_root.parents]:
        if p.name == 'badcase':
            return p
    raise RuntimeError('BADCASE_ROOT_NOT_DERIVABLE_FROM_STATE_ROOT')


def discover_strong_repo(state_root: Path) -> tuple[Path, dict[str, Any]]:
    github_root = find_badcase_root(state_root) / 'github_exports'
    if not github_root.is_dir():
        raise RuntimeError('GITHUB_EXPORTS_ROOT_MISSING')
    candidates = []
    rel = Path('docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json')
    for child in sorted(github_root.iterdir()):
        if not child.is_dir() or child.is_symlink():
            continue
        auth = child / rel
        if not auth.is_file() or auth.is_symlink():
            continue
        try:
            value = load_json(auth)
        except Exception:
            continue
        if value.get('schema_id') != 'ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1':
            continue
        if value.get('strong_primary_fresh_round_execution_authorized') is not True:
            continue
        roles = set(value.get('strong_primary_roles') or [])
        if not {'ANALYZER','RESEARCH_PLANNER_PRE','RESEARCH_PLANNER_POST'} <= roles:
            continue
        required = [
            child/'scripts/cognitive_runtime/run_registry_v1.py',
            child/'configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json',
            child/'src/pchsi/cognitive_runtime/orchestrator.py',
            child/'src/pchsi/round_control/clean_analyzer_input_materialization.py',
        ]
        if all(x.is_file() and not x.is_symlink() for x in required):
            candidates.append((child.resolve(), value))
    if len(candidates) != 1:
        raise RuntimeError('STRONG_REPO_DISCOVERY_NOT_UNIQUE:'+str([str(x[0]) for x in candidates]))
    return candidates[0]


def terminal_paths(state_root: Path) -> tuple[Path, Path, Path, Path, Path]:
    ev = state_root/'round_evidence'
    return (
        ev/'PCHSI_V1232K_GLOBAL_TERMINAL_V1.json',
        ev/'ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json',
        ev/'ROUND_ROLLOUT_UNIVERSE_SEAL_V1.json',
        ev/'ROUND_FAILURE_COHORT_SELECTION_MANIFEST_V1.json',
        ev/'ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1.json',
    )


def validate_handoff(state_root: Path) -> tuple[dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any]]:
    tp,hp,up,fp,ip = terminal_paths(state_root)
    t,h,u,f,i = map(load_json,(tp,hp,up,fp,ip))
    if h.get('schema_id') != 'ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1':
        raise RuntimeError('ROLLOUT_HANDOFF_SCHEMA_MISMATCH')
    if h.get('scientific_rollout_valid') is not True:
        raise RuntimeError('ROLLOUT_HANDOFF_NOT_SCIENTIFICALLY_VALID')
    if int(h.get('infrastructure_invalid_count',-1)) != 0 or int(h.get('protocol_invalid_count',-1)) != 0:
        raise RuntimeError('ROLLOUT_HANDOFF_HAS_INVALID_CELLS')
    if h.get('human_selection_performed') is not False or h.get('benchmark_feedback_used') is not False:
        raise RuntimeError('ROLLOUT_HANDOFF_HUMAN_OR_BENCHMARK_LEAK')
    if h.get('memory_writeback_performed') is not False or h.get('training_execution_performed') is not False:
        raise RuntimeError('ROLLOUT_HANDOFF_HAS_FORBIDDEN_DOWNSTREAM_MUTATION')
    if t.get('scientific_rollout_valid') is not True:
        raise RuntimeError('GLOBAL_TERMINAL_NOT_VALID')
    if f.get('human_selection_performed') is not False:
        raise RuntimeError('FAILURE_COHORT_HUMAN_SELECTED')
    return t,h,u,f,i


def import_repo(repo: Path) -> None:
    sys.path.insert(0, str(repo/'src'))


def load_historical_attempt_loader(repo: Path):
    path=repo/'scripts/memory/materialize_sequence_failure_experience_v1.py'
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('HISTORICAL_ATTEMPT_LOADER_SOURCE_MISSING')
    spec=importlib.util.spec_from_file_location('pchsi_v1232q_historical_attempt_loader',path)
    if spec is None or spec.loader is None:
        raise RuntimeError('HISTORICAL_ATTEMPT_LOADER_SPEC_INVALID')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn=getattr(module,'load_attempt_directory_v1',None)
    if not callable(fn):
        raise RuntimeError('HISTORICAL_ATTEMPT_LOADER_SYMBOL_MISSING')
    params=inspect.signature(fn).parameters
    if tuple(params) != ('attempt_dir',):
        raise RuntimeError('HISTORICAL_ATTEMPT_LOADER_SIGNATURE_DRIFT:'+str(tuple(params)))
    return fn


def assert_fixed_head_api_contract(repo: Path) -> dict[str, Any]:
    # Release-preflight against the actual discovered fixed-head repo.
    # This runs before output-root creation and before any provider call.
    from pchsi.analyzer import grouping as grouping_mod
    from pchsi.analyzer import act3_registration as act3_mod
    from pchsi.round_control import clean_analyzer_input_materialization as clean_analyzer_mod
    from pchsi.evaluation.schema_models import AttemptReceiptV1, EpisodeArtifactV1

    required={
        'build_group_manifests': (grouping_mod,'build_group_manifests',('local_results','mechanical_signatures')),
        'build_group_synthesis_inputs': (grouping_mod,'build_group_synthesis_inputs',('group_manifests','source_bindings')),
        'build_group_signature_binding': (act3_mod,'build_group_signature_binding',('local_result','error','evidence_pack','action_traces_by_call')),
        'select_dev_source_call': (act3_mod,'select_dev_source_call',('local_result','error')),
        'build_round_analyzer_resource_budget': (clean_analyzer_mod,'build_round_analyzer_resource_budget',('round_id','policy_version','producer_role','source_authority_sha256','local_stage_rows','local_logical_call_cap')),
        'validate_round_analyzer_resource_budget': (clean_analyzer_mod,'validate_round_analyzer_resource_budget',('value',)),
        'select_failure_only_u_reg': (clean_analyzer_mod,'select_failure_only_u_reg',('failure_rows','resource_budget','source_campaign_sha256')),
        'build_clean_analyzer_task_access_record': (clean_analyzer_mod,'build_clean_analyzer_task_access_record',('round_id','source_unit_id','task_id','gamefile_sha256','source_campaign_sha256','evidence_cutoff_sha256')),
        'build_local_u_reg_manifest': (clean_analyzer_mod,'build_local_u_reg_manifest',('round_id','policy_version','evidence_cutoff_sha256','failure_universe_file_sha256','source_campaign_sha256','resource_budget','selected_units')),
    }
    out={}
    for key,(module,name,expected) in required.items():
        fn=getattr(module,name,None)
        if not callable(fn):
            raise RuntimeError('FIXED_HEAD_REQUIRED_SYMBOL_MISSING:'+module.__name__+':'+name)
        params=inspect.signature(fn).parameters
        if not set(expected) <= set(params):
            raise RuntimeError('FIXED_HEAD_CALLABLE_SIGNATURE_DRIFT:'+name+':'+str(tuple(params)))
        out[key]=fn
    out['load_attempt_directory_v1']=load_historical_attempt_loader(repo)
    if not callable(getattr(AttemptReceiptV1,'from_json',None)):
        raise RuntimeError('ATTEMPT_RECEIPT_FROM_JSON_SURFACE_MISSING')
    if not callable(getattr(EpisodeArtifactV1,'from_json',None)):
        raise RuntimeError('EPISODE_ARTIFACT_FROM_JSON_SURFACE_MISSING')
    out['AttemptReceiptV1']=AttemptReceiptV1
    out['EpisodeArtifactV1']=EpisodeArtifactV1
    return out


def classify_source_closed_groups(group_manifests, source_bindings):
    source_closed=[]; partial=[]; no_source=[]
    for group in group_manifests:
        members=group.get('membership_records')
        if not isinstance(members,list) or not members:
            raise RuntimeError('GROUP_MEMBERSHIP_RECORDS_INVALID')
        keys=[]
        for m in members:
            if not isinstance(m,dict):
                raise RuntimeError('GROUP_MEMBERSHIP_RECORD_INVALID')
            keys.append((str(m.get('local_result_sha256')),str(m.get('error_instance_id'))))
        present=sum(1 for key in keys if key in source_bindings)
        if present == len(keys): source_closed.append(group)
        elif present == 0: no_source.append(group)
        else: partial.append(group)
    return source_closed,partial,no_source


def runtime_local_stage_rows(repo: Path) -> list[dict[str,Any]]:
    manifest = load_json(repo/'configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json')
    rows = [dict(x) for x in manifest.get('stage_rows',[]) if isinstance(x,dict) and x.get('stage_id') in {'L-A0','L-A1'}]
    if {x.get('stage_id') for x in rows} != {'L-A0','L-A1'}:
        raise RuntimeError('LOCAL_STAGE_RUNTIME_CONTRACT_MISSING')
    return rows


def derive_local_cap(repo: Path, stage_rows: list[dict[str,Any]]) -> tuple[int,dict[str,Any]]:
    contract = load_json(repo/'configs/analyzer/analyzer_a0_a3_experiment_contract_v1.json')
    target = contract.get('main_unique_states_target')
    if type(target) is not int or target <= 0:
        raise RuntimeError('REFERENCE_EXPERIMENT_STATE_TARGET_INVALID')
    per_state = sum(int(x['logical_call_budget_per_unit']) for x in stage_rows)
    if per_state <= 0:
        raise RuntimeError('LOCAL_STAGE_PER_STATE_COST_INVALID')
    return target * per_state, contract


def evidence_pack(bundle, *, round_id: str, parent_policy_id: str, handoff_sha: str, memory_snapshot_sha: str|None, mechanical: Mapping[str,Any], domain_hash) -> dict[str,Any]:
    transitions = {x.model_call_index:x for x in bundle.transitions}
    rows=[]
    observed_memory=set()
    for call, trace in zip(bundle.policy_calls,bundle.traces):
        trans=transitions.get(call.model_call_index)
        prov = trace.provenance
        if not isinstance(prov, Mapping):
            raise RuntimeError('TRACE_PROVENANCE_MAPPING_REQUIRED')
        mv = prov.get('memory_version')
        ms = prov.get('memory_state_sha256')
        if mv is not None or ms is not None:
            observed_memory.add((mv,ms))
        rows.append({
            'model_call_index':call.model_call_index,
            'environment_step_count_before':call.environment_step_count_before,
            'public_task_goal':call.public_task_goal,
            'observation_before':call.observation,
            'admissible_commands':list(call.admissible_commands),
            'executed_history':[{'action':a,'resulting_observation':o} for a,o in call.executed_history],
            'policy_prompt_text':call.prompt_text,
            'raw_model_response':call.raw_response_text,
            'literal_action':trace.literal_action,
            'normalized_action':trace.normalized_action,
            'parser_status':trace.parser_status,
            'parser_error':trace.parser_error,
            'attempt_outcome':trace.attempt_outcome,
            'execution_status':trace.execution_status,
            'submitted_environment_action':trace.submitted_environment_action,
            'final_executed_action':trace.final_executed_action,
            'resulting_observation':None if trans is None else trans.resulting_observation,
            'resulting_admissible_commands':None if trans is None else list(trans.resulting_menu),
            'environment_done':None if trans is None else trans.done,
            'environment_won':None if trans is None else trans.won,
            'environment_score':None if trans is None else trans.score,
            'budget_before':call.budget_before.to_dict(),
            'budget_after':trace.budget_after.to_dict(),
        })
    if memory_snapshot_sha is None:
        raise RuntimeError('SOURCE_TRAJECTORY_MEMORY_AUTHORITY_MISSING')
    persistent={x for x in observed_memory if x[0]=='PERSISTENT_FAILURE_EXPERIENCE_V1'}
    if persistent!={('PERSISTENT_FAILURE_EXPERIENCE_V1',memory_snapshot_sha)}:
        raise RuntimeError('SOURCE_TRAJECTORY_MEMORY_AUTHORITY_DRIFT:'+repr(sorted(persistent)))
    task_goal = bundle.policy_calls[0].public_task_goal if bundle.policy_calls else ''
    pack={
      'schema_id':'ANALYZER_EVIDENCE_PACK_V1','schema_version':1,
      'pack_role':'COMMON_EVIDENCE_IDENTICAL_ACROSS_A0_A1_A2_A3',
      'task_identity':{'task_id':bundle.task_id,'task_type':bundle.episode.get('task_type'),'gamefile_sha256':bundle.gamefile_sha256,'seed':bundle.episode.get('seed'),'public_task_goal':task_goal},
      'policy_identity':{'logical_policy_id':parent_policy_id,'checkpoint_instance_id':parent_policy_id,'identity_sha256':domain_hash('CURRENT_ROUND_ANALYZER_POLICY_IDENTITY_V1',{'round_id':round_id,'parent_policy_id':parent_policy_id,'rollout_handoff_sha256':handoff_sha,'round_start_memory_snapshot_sha256':memory_snapshot_sha})},
      'trajectory_identity':{'source_attempt_bundle_sha256':bundle.attempt_bundle_sha256,'source_episode_semantic_sha256':bundle.episode_semantic_sha256,'round_rollout_evidence_handoff_sha256':handoff_sha,'execution_attempt_id':bundle.episode.get('execution_attempt_id'),'round_id':round_id},
      'trajectory':rows,'mechanical_evidence':dict(mechanical),
      'memory_support_port':{'schema_id':'ANALYZER_MEMORY_SUPPORT_PORT_V1','base_pack_exposes_memory':False,'memory_packet':None,'a3_extension_rule':'A3_MAY_ATTACH_ONE_FROZEN_ANALYZER_MEMORY_PACKET_WITHOUT_CHANGING_COMMON_TRAJECTORY_EVIDENCE'},
      'analyzer_output_authority':{'failure_window_is_proposal':True,'mechanism_is_semantic_hypothesis':True,'candidate_repair_is_proposal':True,'benefit_harm_authority':False,'training_label_authority':False,'promotion_authority':False},
      'requires_environment_verification':True,
      'evidence_pack_sha256':'0'*64,
    }
    pack['evidence_pack_sha256']=domain_hash('ANALYZER_EVIDENCE_PACK_V1',pack,excluded_field='evidence_pack_sha256')
    return pack


def run_registry(repo: Path, registry: Path, out: Path) -> int:
    py = sys.executable
    script=repo/'scripts/cognitive_runtime/run_registry_v1.py'
    env=os.environ.copy(); env['PYTHONPATH']=str(repo/'src') + (os.pathsep+env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    if env.get('OPENAI_API_KEY'):
        cp=subprocess.run([py,str(script),'--registry',str(registry),'--output-root',str(out)],env=env)
        return cp.returncode
    manifest=load_json(repo/'configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json')
    loader=manifest.get('historical_credential_loader_default')
    if not isinstance(loader,str) or not Path(loader).is_file():
        raise RuntimeError('OPENAI_CREDENTIAL_LOADER_UNAVAILABLE')
    cmd='source "$1"; exec "$2" "$3" --registry "$4" --output-root "$5"'
    cp=subprocess.run(['bash','-c',cmd,'_',loader,py,str(script),str(registry),str(out)],env=env)
    return cp.returncode


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--v1232k-state-root',required=True)
    args=ap.parse_args()
    state=Path(args.v1232k_state_root).resolve()
    terminal,handoff,universe,cohort,index=validate_handoff(state)
    repo,role_auth=discover_strong_repo(state)
    import_repo(repo)
    api=assert_fixed_head_api_contract(repo)

    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.reference_loop.bundle_reader import validate_attempt_bundle
    from pchsi.reference_loop.mechanical import extract_mechanical_episode_evidence
    from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
    from pchsi.cognitive_runtime.projections import local_projection
    from pchsi.cognitive_runtime.schema_registry import validate_artifact
    from pchsi.analyzer.outcome_router import route_episode

    build_round_analyzer_resource_budget=api['build_round_analyzer_resource_budget']
    validate_round_analyzer_resource_budget=api['validate_round_analyzer_resource_budget']
    select_failure_only_u_reg=api['select_failure_only_u_reg']
    build_clean_analyzer_task_access_record=api['build_clean_analyzer_task_access_record']
    build_local_u_reg_manifest=api['build_local_u_reg_manifest']
    build_group_signature_binding=api['build_group_signature_binding']
    select_dev_source_call=api['select_dev_source_call']
    build_group_manifests=api['build_group_manifests']
    build_group_synthesis_inputs=api['build_group_synthesis_inputs']
    load_attempt_directory_v1=api['load_attempt_directory_v1']
    AttemptReceiptV1=api['AttemptReceiptV1']
    EpisodeArtifactV1=api['EpisodeArtifactV1']

    round_id=str(handoff['round_id']); parent_policy_id=str(handoff['parent_policy_id'])
    handoff_path=state/'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json'; handoff_sha=sha256_file(handoff_path)
    stage_rows=runtime_local_stage_rows(repo); cap,exp_contract=derive_local_cap(repo,stage_rows)
    budget=build_round_analyzer_resource_budget(round_id=round_id,policy_version=parent_policy_id,producer_role='REFERENCE_EXPERIMENT_CONTRACT',source_authority_sha256=handoff_sha,local_stage_rows=stage_rows,local_logical_call_cap=cap)
    validate_round_analyzer_resource_budget(budget)

    idx_rows=index.get('rows'); fail_ids=cohort.get('failure_scientific_cell_ids')
    if not isinstance(idx_rows,list) or not isinstance(fail_ids,list) or not fail_ids:
        raise RuntimeError('FAILURE_COHORT_OR_INDEX_INVALID')
    resolved_authorities,path_reconciliation=recover_bundle_authorities(
        state_root=state,
        handoff=handoff,
        index=index,
        failure_ids=fail_ids,
        attempt_receipt_type=AttemptReceiptV1,
        episode_artifact_type=EpisodeArtifactV1,
    )
    failure_rows=[]
    source_campaign_sha=str(handoff.get('rollout_request_sha256') or handoff_sha)
    for cid in fail_ids:
        a=resolved_authorities[str(cid)]
        failure_rows.append({
            'classification':'TASK_FAILURE',
            'source_campaign_sha256':source_campaign_sha,
            'policy_interface_profile_id':'I1_EXECUTION_PROFILE_V1',
            'scientific_cell_id':str(cid),
            'execution_attempt_id':a['execution_attempt_id'],
            'task_id':a['task_id'],
            'task_type':a['task_type'],
            'gamefile_sha256':a['gamefile_sha256'],
            'attempt_bundle_sha256':a['attempt_bundle_sha256'],
            'episode_semantic_sha256':a['episode_semantic_sha256'],
        })
    failure_universe_bytes=canonical_jsonl_bytes(failure_rows)
    failure_universe_sha=hashlib.sha256(failure_universe_bytes).hexdigest()
    selected=select_failure_only_u_reg(
        failure_rows=failure_rows,
        resource_budget=budget,
        source_campaign_sha256=source_campaign_sha,
    )

    # Full byte-level bundle validation is required for every selected source,
    # but not for every unselected failure in the rollout. This preserves the
    # deterministic selector while avoiding a needless full parse of the entire
    # failure cohort. It still occurs before output-root creation/provider calls.
    bundles={}
    for srow in selected:
        cid=str(srow['scientific_cell_id'])
        a=resolved_authorities[cid]
        b=validate_attempt_bundle(Path(a['bundle_path']))
        if (
            b.attempt_bundle_sha256!=a['attempt_bundle_sha256']
            or b.episode_semantic_sha256!=a['episode_semantic_sha256']
            or b.episode.get('execution_attempt_id')!=a['execution_attempt_id']
            or b.task_id!=a['task_id']
            or b.episode.get('task_type')!=a['task_type']
        ):
            raise RuntimeError('SELECTED_BUNDLE_AUTHORITY_MISMATCH:'+cid)
        bundles[cid]=b

    selected_enriched=[]
    for srow in selected:
        cid=str(srow['scientific_cell_id'])
        b=bundles[cid]
        source_unit_id=domain_hash(
            'V1232Q_ANALYZER_SOURCE_UNIT_ID_V1',
            {
                'round_id':round_id,
                'scientific_cell_id':cid,
                'attempt_bundle_sha256':b.attempt_bundle_sha256,
                'handoff_sha256':handoff_sha,
            },
        )
        row=dict(srow)
        row['source_unit_id']=source_unit_id
        row['gamefile_sha256']=b.gamefile_sha256
        selected_enriched.append(row)
    selected=selected_enriched

    badcase=find_badcase_root(state)
    activation=domain_hash('V1232Q_STRONG_ANALYZER_WAVE1_ACTIVATION_V1',{'handoff_sha256':handoff_sha,'role_authority_sha256':sha256_file(repo/'docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json'),'resource_budget_sha256':budget['budget_sha256']})
    out=badcase/'new_human_pi1/control/v1232q_strong_analyzer_wave1_and_canonical_act3_reuse'/activation
    out.mkdir(parents=True,exist_ok=False)
    write_new_json(out/'ROUND_ANALYZER_RESOURCE_BUDGET_V1.json',budget)
    write_new_json(out/'V1232Q_SOURCE_ROLLOUT_HANDOFF_COPY.json',handoff)
    path_reconciliation['round_id']=round_id
    path_reconciliation['rollout_handoff_sha256']=handoff_sha
    path_reconciliation['receipt_sha256']=domain_hash(
        'V1232Q_ATTEMPT_BUNDLE_PATH_AUTHORITY_RECONCILIATION_V1',
        path_reconciliation,
        excluded_field='receipt_sha256',
    )
    write_new_json(
        out/'V1232Q_ATTEMPT_BUNDLE_PATH_AUTHORITY_RECONCILIATION_V1.json',
        path_reconciliation,
    )
    failure_universe_path=out/'CURRENT_ROUND_TRAIN_UPDATE_FAILURE_UNIVERSE_V1.jsonl'
    write_new_bytes(failure_universe_path,failure_universe_bytes)
    if sha256_file(failure_universe_path)!=failure_universe_sha:
        raise RuntimeError('FAILURE_UNIVERSE_FILE_SHA_MISMATCH')
    u_reg=build_local_u_reg_manifest(
        round_id=round_id,
        policy_version=parent_policy_id,
        evidence_cutoff_sha256=handoff_sha,
        failure_universe_file_sha256=failure_universe_sha,
        source_campaign_sha256=source_campaign_sha,
        resource_budget=budget,
        selected_units=selected,
    )
    write_new_json(out/'CLEAN_ANALYZER_LOCAL_U_REG_V1.json',u_reg)

    # The rollout request itself is the exact round-start Memory authority.
    req_path=_require_abs_regular_file(handoff.get('rollout_request_path'),'ROLLOUT_REQUEST')
    if sha256_file(req_path)!=handoff.get('rollout_request_sha256'):
        raise RuntimeError('ROLLOUT_REQUEST_SHA_MISMATCH')
    req=load_json(req_path)
    memory_sha=req.get('round_start_memory_snapshot_sha256')
    if not isinstance(memory_sha,str) or len(memory_sha)!=64:
        raise RuntimeError('ROUND_START_MEMORY_SNAPSHOT_AUTHORITY_MISSING')
    if req.get('round_id')!=round_id or req.get('parent_policy_id')!=parent_policy_id:
        raise RuntimeError('ROLLOUT_REQUEST_ROUND_POLICY_IDENTITY_MISMATCH')

    units=[]; selected_meta=[]; access_manifest_rows=[]
    for rank,s in enumerate(selected):
        cid=str(s['scientific_cell_id']); b=bundles[cid]
        mechanical=extract_mechanical_episode_evidence(b)
        pack=evidence_pack(b,round_id=round_id,parent_policy_id=parent_policy_id,handoff_sha=handoff_sha,memory_snapshot_sha=memory_sha,mechanical=mechanical,domain_hash=domain_hash)
        route=route_episode(pack)
        if route.get('route_status')!='SCIENTIFIC_OUTCOME_AVAILABLE' or route.get('trajectory_outcome')!='FAILURE':
            raise RuntimeError('SELECTED_FAILURE_PACK_ROUTE_MISMATCH:'+cid)
        source_unit_id=str(s['source_unit_id'])
        ur=out/'units'/source_unit_id; ur.mkdir(parents=True,exist_ok=False)
        write_new_json(ur/'analyzer_evidence_pack.json',pack)
        proj=local_projection(ur/'analyzer_evidence_pack.json'); write_new_json(ur/'local_projection.json',proj)
        access=build_clean_analyzer_task_access_record(round_id=round_id,source_unit_id=source_unit_id,task_id=b.task_id,gamefile_sha256=b.gamefile_sha256,source_campaign_sha256=source_campaign_sha,evidence_cutoff_sha256=handoff_sha)
        write_new_json(ur/'task_access_record.json',access)
        sm={'schema_id':'V1232Q_ANALYZER_SOURCE_UNIT_MANIFEST_V1','schema_version':1,'round_id':round_id,'source_unit_id':source_unit_id,'selection_rank':rank,'scientific_cell_id':cid,'execution_attempt_id':b.episode['execution_attempt_id'],'task_id':b.task_id,'task_type':b.episode.get('task_type'),'gamefile_sha256':b.gamefile_sha256,'attempt_bundle_path':str(b.bundle_root),'attempt_bundle_sha256':b.attempt_bundle_sha256,'episode_semantic_sha256':b.episode_semantic_sha256,'evidence_pack_sha256':pack['evidence_pack_sha256'],'rollout_handoff_sha256':handoff_sha,'source_unit_manifest_sha256':'0'*64}
        sm['source_unit_manifest_sha256']=domain_hash('V1232Q_ANALYZER_SOURCE_UNIT_MANIFEST_V1',sm,excluded_field='source_unit_manifest_sha256'); write_new_json(ur/'source_unit_manifest.json',sm)
        identity=build_scientific_unit_identity(scientific_unit_type='EPISODE',scientific_unit_id=source_unit_id,source_unit_manifest_sha256=sm['source_unit_manifest_sha256'],task_set_manifest_sha256=u_reg['u_reg_sha256'],task_id=b.task_id,gamefile_sha256=b.gamefile_sha256,group_manifest_sha256=None,round_evidence_package_sha256=handoff_sha)
        write_new_json(ur/'scientific_unit_identity.json',identity)
        access_manifest_rows.append({
            'source_unit_id':source_unit_id,
            'task_access_record_path':str((ur/'task_access_record.json').relative_to(out)),
            'task_access_record_sha256':access['task_access_sha256'],
        })
        for sid,cid2 in (('L-A0','A0'),('L-A1','A1')):
            units.append({'source_unit_id':source_unit_id,'scientific_unit_identity_path':str((ur/'scientific_unit_identity.json').relative_to(out)),'stage_id':sid,'condition_id':cid2,'input_projection_path':str((ur/'local_projection.json').relative_to(out)),'task_access_record_path':str((ur/'task_access_record.json').relative_to(out)),'expected_common_evidence_sha256':pack['evidence_pack_sha256'],'expected_a1_local_result_sha256':None,'expected_memory_pack_sha256':None})
        selected_meta.append({'source_unit_id':source_unit_id,'scientific_cell_id':cid,'bundle_path':str(b.bundle_root),'task_id':b.task_id,'task_type':b.episode.get('task_type'),'gamefile_sha256':b.gamefile_sha256,'pack_sha256':pack['evidence_pack_sha256'],'task_access_sha256':access['task_access_sha256'],'source_evidence_index_row_sha256':s['source_evidence_index_row_sha256']})
    access_manifest={
        'schema_id':'CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1',
        'schema_version':1,
        'round_id':round_id,
        'source_campaign_sha256':source_campaign_sha,
        'evidence_cutoff_sha256':handoff_sha,
        'row_count':len(access_manifest_rows),
        'rows':access_manifest_rows,
        'manifest_sha256':'0'*64,
    }
    access_manifest['manifest_sha256']=domain_hash(
        'CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1',
        access_manifest,
        excluded_field='manifest_sha256',
    )
    access_manifest_path=out/'CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1.json'
    write_new_json(access_manifest_path,access_manifest)
    registry={'schema_id':'RUNTIME_INPUT_REGISTRY_V1','schema_version':1,'registry_role':'FORMAL_A0_A3','round_id':round_id,'policy_version':parent_policy_id,'task_access_manifest_sha256':sha256_file(access_manifest_path),'units':units,'registry_sha256':'0'*64}
    registry['registry_sha256']=domain_hash('RUNTIME_INPUT_REGISTRY_V1',registry,excluded_field='registry_sha256'); validate_artifact('RUNTIME_INPUT_REGISTRY_V1',registry)
    regpath=out/'CLEAN_ANALYZER_LOCAL_RUNTIME_INPUT_REGISTRY_V1.json'; write_new_json(regpath,registry)
    write_new_json(out/'V1232Q_SELECTED_SOURCE_UNIVERSE_V1.json',{'schema_id':'V1232Q_SELECTED_SOURCE_UNIVERSE_V1','schema_version':1,'round_id':round_id,'source_count':len(selected_meta),'selection_authority_sha256':budget['budget_sha256'],'rows':selected_meta})

    liveout=out/'strong_local_runtime'
    rc=run_registry(repo,regpath,liveout)
    if rc!=0: raise RuntimeError('STRONG_LOCAL_REGISTRY_RUNNER_FAILED:'+str(rc))
    execm=load_json(liveout/'execution_manifest.json')
    rows=execm.get('rows');
    if not isinstance(rows,list): raise RuntimeError('LOCAL_EXECUTION_MANIFEST_ROWS_INVALID')
    by_source=defaultdict(dict)
    hard=[]
    for r in rows:
        if not isinstance(r,dict): continue
        by_source[str(r.get('source_unit_id'))][str(r.get('stage_id'))]=r
        if r.get('hard_stop') is True: hard.append(r)
    complete=[]; censored=[]
    a1_data={}
    for meta in selected_meta:
        sid=meta['source_unit_id']; sr=by_source.get(sid,{})
        if all(sr.get(x,{}).get('status')=='ACCEPTED' for x in ('L-A0','L-A1')):
            complete.append(sid)
            a1row=sr['L-A1']; art=load_json(Path(str(a1row['call_dir']))/'validated_artifact.json'); a1_data[sid]=(art,meta,bundles[meta['scientific_cell_id']])
        else: censored.append({'source_unit_id':sid,'A0':sr.get('L-A0'),'A1':sr.get('L-A1')})
    wave={'schema_id':'V1232Q_STRONG_LOCAL_WAVE_TERMINAL_V1','schema_version':1,'round_id':round_id,'selected_source_count':len(selected_meta),'complete_pair_count':len(complete),'censored_source_count':len(censored),'hard_stop_count':len(hard),'complete_source_unit_ids':complete,'censored_sources':censored,'automatic_retry_performed':False,'human_disposition_required':False,'wave_sha256':'0'*64}
    wave['wave_sha256']=domain_hash('V1232Q_STRONG_LOCAL_WAVE_TERMINAL_V1',wave,excluded_field='wave_sha256'); write_new_json(out/'V1232Q_STRONG_LOCAL_WAVE_TERMINAL_V1.json',wave)
    if hard or censored:
        print('STATUS=V1232Q_STRONG_ANALYZER_LOCAL_WAVE_TERMINAL_WITH_CENSORSHIP')
        print('V1232Q_OUTPUT_ROOT='+str(out)); print('V1232Q_COMPLETE_PAIR_COUNT='+str(len(complete))); print('V1232Q_CENSORED_SOURCE_COUNT='+str(len(censored))); print('HUMAN_DISPOSITION_REQUIRED=false')
        return 20

    signatures=[]; source_contexts={}; source_binding_censored=[]; signature_failures=[]
    local_results=[]
    for sid,(a1,meta,b) in a1_data.items():
        local_results.append(a1)
        pack=load_json(out/'units'/sid/'analyzer_evidence_pack.json')
        raw=load_attempt_directory_v1(Path(meta['bundle_path']))
        traces={x.model_call_index:x for x in raw.traces}
        calls={x.model_call_index:x for x in raw.policy_calls}
        for err in a1.get('error_instances',[]):
            try:
                sig=build_group_signature_binding(
                    local_result=a1,
                    error=err,
                    evidence_pack=pack,
                    action_traces_by_call=traces,
                )
            except Exception as e:
                signature_failures.append({
                    'source_unit_id':sid,
                    'error_instance_id':err.get('error_instance_id'),
                    'reason':type(e).__name__+':'+str(e),
                })
                continue
            signatures.append(sig)
            try:
                sel=select_dev_source_call(local_result=a1,error=err)
            except Exception as e:
                source_binding_censored.append({
                    'source_unit_id':sid,
                    'error_instance_id':err.get('error_instance_id'),
                    'reason':type(e).__name__+':'+str(e),
                })
                continue
            if sel.get('formal_eligible') is not True:
                source_binding_censored.append({
                    'source_unit_id':sid,
                    'error_instance_id':err.get('error_instance_id'),
                    'reason':'NO_UNIQUE_LINKED_REPAIR_SOURCE_CALL',
                })
                continue
            call_index=int(sel['source_call_index'])
            call=calls.get(call_index)
            if call is None:
                source_binding_censored.append({
                    'source_unit_id':sid,
                    'error_instance_id':err.get('error_instance_id'),
                    'reason':'SOURCE_CALL_NOT_PRESENT',
                })
                continue
            state_sha=domain_hash(
                'V1232Q_CURRENT_ROUND_ANALYZER_GROUP_SOURCE_CONTEXT_V1',
                {
                    'round_id':round_id,
                    'parent_policy_id':parent_policy_id,
                    'source_unit_id':sid,
                    'source_bundle_sha256':b.attempt_bundle_sha256,
                    'model_call_index':call_index,
                    'observation_sha256':call.observation_sha256,
                    'menu_sha256':call.admissible_commands_sequence_sha256,
                    'executed_history_sha256':call.executed_history_sha256,
                    'prompt_sha256':call.prompt_sha256,
                    'round_start_memory_snapshot_sha256':memory_sha,
                },
            )
            ctx={
                'source_unit_id':sid,
                'local_result_sha256':a1['local_result_sha256'],
                'error_instance_id':err['error_instance_id'],
                'source_state_sha256':state_sha,
                'menu_sha256':call.admissible_commands_sequence_sha256,
                'source_call_index':call_index,
                'public_task_goal':call.public_task_goal,
                'observation':call.observation,
                'admissible_commands':list(call.admissible_commands),
                'executed_history':[{'action':a,'resulting_observation':o} for a,o in call.executed_history],
                'interface_feedback_before':call.interface_feedback_before,
                'budget_before':dict(call.budget_before),
                'source_context_identity_role':'ANALYZER_GROUP_BINDING_ONLY_F0F1_REPLAY_REBIND_REQUIRED',
            }
            key=(a1['local_result_sha256'],err['error_instance_id'])
            if key in source_contexts:
                raise RuntimeError('DUPLICATE_GROUP_SOURCE_CONTEXT:'+repr(key))
            source_contexts[key]=ctx

    # Signature production is deterministic evidence compilation. Missing one
    # signature would silently change the group denominator, so fail closed.
    if signature_failures:
        failure={
            'schema_id':'V1232Q_ACT3_SIGNATURE_FAILURE_V1',
            'schema_version':1,
            'round_id':round_id,
            'failure_count':len(signature_failures),
            'rows':signature_failures,
            'human_disposition_required':False,
        }
        write_new_json(out/'V1232Q_ACT3_SIGNATURE_FAILURE_V1.json',failure)
        print('STATUS=V1232Q_ACT3_SIGNATURE_COMPILATION_FAIL_CLOSED')
        print('V1232Q_OUTPUT_ROOT='+str(out))
        print('V1232Q_SIGNATURE_FAILURE_COUNT='+str(len(signature_failures)))
        print('HUMAN_DISPOSITION_REQUIRED=false')
        return 21
    if not signatures:
        raise RuntimeError('NO_A1_ERROR_INSTANCE_SIGNATURES')

    mechanical_signatures={(x['local_result_sha256'],x['error_instance_id']):x for x in signatures}
    groups=build_group_manifests(
        local_results=local_results,
        mechanical_signatures=mechanical_signatures,
    )
    source_closed_groups,partial_groups,no_source_groups=classify_source_closed_groups(
        groups,source_contexts
    )
    if not source_closed_groups:
        raise RuntimeError('NO_SOURCE_CLOSED_GROUPS')
    synths=build_group_synthesis_inputs(
        source_closed_groups,
        source_bindings=source_contexts,
    )
    if len(synths)!=len(source_closed_groups):
        raise RuntimeError('GROUP_SYNTHESIS_CARDINALITY_MISMATCH')

    # Preserve the complete deterministic group universe and source-closure
    # census. No top-up/replacement from non-source-closed groups is allowed.
    all_group_rows=[]
    for g in groups:
        all_group_rows.append({
            'group_id':g['group_id'],
            'group_manifest_sha256':g['group_manifest_sha256'],
            'member_count':len(g['membership_records']),
            'source_closed':g in source_closed_groups,
            'partial_source_binding':g in partial_groups,
            'no_source_binding':g in no_source_groups,
        })
    write_new_json(
        out/'V1232Q_COMPLETE_GROUP_UNIVERSE_V1.json',
        {
            'schema_id':'V1232Q_COMPLETE_GROUP_UNIVERSE_V1',
            'schema_version':1,
            'round_id':round_id,
            'group_count':len(groups),
            'source_closed_group_count':len(source_closed_groups),
            'partial_group_count':len(partial_groups),
            'no_source_group_count':len(no_source_groups),
            'source_binding_censored_count':len(source_binding_censored),
            'rows':all_group_rows,
            'human_group_selection_performed':False,
            'group_top_up_performed':False,
        },
    )

    group_rows=[]
    for g,synth in zip(source_closed_groups,synths,strict=True):
        members=[]
        for m in synth['member_rows']:
            key=(m['local_result_sha256'],m['error_instance_id'])
            c=source_contexts.get(key)
            if c is None:
                raise RuntimeError('GROUP_MEMBER_CONTEXT_MISSING:'+repr(key))
            for field in ('source_state_sha256','menu_sha256','source_call_index'):
                if c.get(field)!=m.get(field):
                    raise RuntimeError('GROUP_MEMBER_CONTEXT_IDENTITY_MISMATCH:'+field)
            members.append(c)
        gr=out/'groups'/g['group_id']
        gr.mkdir(parents=True,exist_ok=False)
        write_new_json(gr/'group_manifest.json',g)
        write_new_json(gr/'group_synthesis_input.json',synth)
        write_new_value(gr/'source_contexts.json',members)
        group_rows.append({
            'group_id':g['group_id'],
            'group_manifest_sha256':g['group_manifest_sha256'],
            'group_manifest_path':str(gr/'group_manifest.json'),
            'group_synthesis_input_sha256':synth['group_synthesis_input_sha256'],
            'group_synthesis_input_path':str(gr/'group_synthesis_input.json'),
            'source_contexts_path':str(gr/'source_contexts.json'),
            'member_count':len(members),
        })

    prep={
        'schema_id':'V1232Q_DETERMINISTIC_GROUP_PREPARATION_V1',
        'schema_version':1,
        'round_id':round_id,
        'source_wave_sha256':wave['wave_sha256'],
        'bundle_path_reconciliation_sha256':path_reconciliation['receipt_sha256'],
        'formal_signature_count':len(signatures),
        'complete_group_count':len(groups),
        'source_closed_group_count':len(group_rows),
        'partial_group_count':len(partial_groups),
        'no_source_group_count':len(no_source_groups),
        'source_binding_censored_count':len(source_binding_censored),
        'groups':group_rows,
        'source_binding_censored':source_binding_censored,
        'source_contexts_are_analyzer_group_bindings_not_f0f1_replay_authority':True,
        'historical_act3_attempt_loader_reused':True,
        'build_group_manifests_reused':True,
        'build_group_synthesis_inputs_reused':True,
        'human_group_selection_performed':False,
        'analyzer_self_denominator_selection_performed':False,
        'group_top_up_performed':False,
        'next':'AUTOMATIC_EXISTING_GROUP_ANALYZER_TAIL_THEN_DYNAMIC_STRONG_PLANNER_PRE',
        'prep_sha256':'0'*64,
    }
    prep['prep_sha256']=domain_hash(
        'V1232Q_DETERMINISTIC_GROUP_PREPARATION_V1',prep,
        excluded_field='prep_sha256',
    )
    write_new_json(out/'V1232Q_DETERMINISTIC_GROUP_PREPARATION_V1.json',prep)
    terminal_o={
        'schema_id':'PCHSI_V1232Q_TERMINAL_V1',
        'schema_version':1,
        'status':'STRONG_ANALYZER_LOCAL_WAVE_AND_CANONICAL_ACT3_GROUP_PREP_COMPLETE',
        'round_id':round_id,
        'parent_policy_id':parent_policy_id,
        'rollout_handoff_sha256':handoff_sha,
        'resource_budget_sha256':budget['budget_sha256'],
        'bundle_path_reconciliation_sha256':path_reconciliation['receipt_sha256'],
        'selected_source_count':len(selected_meta),
        'complete_local_pair_count':len(complete),
        'complete_group_count':len(groups),
        'source_closed_group_count':len(group_rows),
        'human_scientific_decision_count':0,
        'automatic_retry_count':0,
        'environment_execution_count':0,
        'training_execution_count':0,
        'next':'EXISTING_STRONG_GROUP_ANALYZER_TAIL_G_A2_A3_C_P_X_THEN_DYNAMIC_PRE_V2',
        'terminal_sha256':'0'*64,
    }
    terminal_o['terminal_sha256']=domain_hash(
        'PCHSI_V1232Q_TERMINAL_V1',terminal_o,
        excluded_field='terminal_sha256',
    )
    write_new_json(out/'PCHSI_V1232Q_TERMINAL_V1.json',terminal_o)
    print('STATUS=V1232Q_STRONG_ANALYZER_LOCAL_WAVE_AND_CANONICAL_GROUP_PREP_COMPLETE')
    print('V1232Q_OUTPUT_ROOT='+str(out))
    print('V1232Q_SELECTED_SOURCE_COUNT='+str(len(selected_meta)))
    print('V1232Q_COMPLETE_LOCAL_PAIR_COUNT='+str(len(complete)))
    print('V1232Q_COMPLETE_GROUP_COUNT='+str(len(groups)))
    print('V1232Q_SOURCE_CLOSED_GROUP_COUNT='+str(len(group_rows)))
    print('V1232Q_PROVIDER_CALL_COUNT='+str(len(rows)))
    print('HUMAN_SCIENTIFIC_DECISION_COUNT=0')
    print('V1232Q_NEXT='+terminal_o['next'])
    return 0

if __name__=='__main__':
    raise SystemExit(main())
