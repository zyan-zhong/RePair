"""Offline continuation from the existing training receipts to SELECT inputs.

No actor, environment, model, training, scheduling, or promotion executor.
The SELECT grid is a proposal until a separate protocol authorization exists.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

TRAINER_REL='scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build'


def need(ok,why):
    if not ok: raise ValueError(why)


def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()


def regular(path:Path)->Path:
    path=Path(path)
    need(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'REGULAR_FILE_REQUIRED:'+str(path))
    return path


def file_sha(path:Path)->str:
    h=hashlib.sha256()
    with regular(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def load_module(path:Path,name:str,expected:str):
    need(file_sha(path)==expected,'DEPENDENCY_SHA_MISMATCH:'+name)
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec is not None and spec.loader is not None,'IMPORT_SPEC')
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m


def load_helpers(repo:Path,refs:dict)->dict:
    sys.path[:0]=[str(repo/'src'),str(repo/TRAINER_REL)]
    return {name:load_module(Path(ref['path']),'_select_existing_'+name,ref['sha256']) for name,ref in refs.items()}


def read_packet(path:Path,expected:str,helpers:dict)->dict[str,bytes]:
    return helpers['handoff'].read_packet(path,expected)


def obj(raw:bytes):
    from pchsi.reference_loop.canonical import strict_json_loads
    v=strict_json_loads(raw);need(isinstance(v,dict),'JSON_OBJECT_REQUIRED');return v


def cb(v):
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes
    return canonical_json_bytes(v)


def by_suffix(files:dict,suffix:str)->tuple[str,bytes]:
    names=[n for n in files if n.endswith(suffix)]
    need(len(names)==1,'NONUNIQUE_REQUIRED_ARTIFACT:'+suffix)
    return names[0],files[names[0]]


def verify_training_evidence(t:dict,q:dict,helpers:dict,formal_source:Path)->dict:
    from round_training.common import require_domain_sha
    from round_training.contracts import validate_training_contract
    from pchsi.reference_loop.canonical import domain_hash
    clean=helpers['clean_adapter'];validated=clean.validate_packet(q)
    plan=validated['plan'];order=validated['order'];native=validated['native']
    c=obj(t['TRAINING_CONTRACT.json']);validate_training_contract(c,order)
    init=obj(t['INITIALIZATION_RECEIPT.json']);request=obj(t['INITIALIZATION_REQUEST.json'])
    binding=obj(t['TRAINING_STAGE_BINDING.json']);auth=obj(t['TRAINING_AUTHORIZATION.json'])
    result=obj(t['TRAINING_RESULT.json']);candidate=obj(t['CANDIDATE_HANDOFF.json'])
    for value,field in [(binding,'stage_binding_sha256'),(auth,'authorization_sha256'),
        (result['stage_receipt'],'stage_receipt_sha256'),(result['output_artifact_index'],'artifact_index_sha256')]:
        require_domain_sha(value,schema_id=value['schema_id'],sha_field=field)
    for value,field in [(request,'request_sha256'),(init,'initialization_receipt_sha256')]:
        need(domain_hash(value['schema_id'],value,excluded_field=field)==value[field], 'UPSTREAM_DOMAIN_HASH:'+field)
    clean.verify_seed_zero_receipt(init,plan,c['clean_runtime'])
    manifest=obj(by_suffix(t,'/formal_run_manifest.json')[1])
    need(result['run_manifest']==candidate['run_manifest']==manifest,'CANDIDATE_RUN_MANIFEST_MISMATCH')
    need(manifest['research_planner_training_plan_domain_sha256']==plan['training_plan_sha256']==candidate['training_plan_sha256'],'PLAN_IDENTITY')
    need(manifest['training_contract_file_sha256']==sha(t['TRAINING_CONTRACT.json']),'TRAINING_CONTRACT_BYTES')
    need(manifest['sample_order_manifest_file_sha256']==sha(q['ROUND_SAMPLE_ORDER_MANIFEST_V1.json']),'SAMPLE_ORDER_BYTES')
    need(manifest['trainer_native_dataset_sha256']==sha(q['POLICY_T2_TRAINER_NATIVE_V1.jsonl']),'DATASET_BYTES')
    need(manifest['interface_profile_id']==plan['interface_profile_id']=='I1_EXECUTION_PROFILE_V1','I1_REQUIRED')
    need(auth['authorization_status']=='APPROVED' and auth['stage_binding_sha256']==binding['stage_binding_sha256']==manifest['stage_binding_sha256'],'EXECUTION_AUTHORITY')
    term=obj(by_suffix(t,'/terminal_stage_receipt.json')[1]);start=obj(by_suffix(t,'/started_stage_receipt.json')[1])
    inp=obj(by_suffix(t,'/input_artifact_index.json')[1]);out=obj(by_suffix(t,'/output_artifact_index.json')[1])
    for value,field in [(term,'stage_receipt_sha256'),(start,'stage_receipt_sha256'),(inp,'artifact_index_sha256'),(out,'artifact_index_sha256')]:
        require_domain_sha(value,schema_id=value['schema_id'],sha_field=field)
    need(term==result['stage_receipt'] and out==result['output_artifact_index'],'RECEIPT_COPY_MISMATCH')
    need(term['terminal_status']=='ACCEPTED' and term['model_training_executed'] is True and term['model_training_execution_status']=='COMPLETED','TRAINING_NOT_COMPLETED')
    need(term['authorization_sha256']==auth['authorization_sha256'] and term['started_from_receipt_sha256']==start['stage_receipt_sha256'],'RECEIPT_CHAIN')
    need(term['input_artifact_index_sha256']==inp['artifact_index_sha256'] and term['output_artifact_index_sha256']==out['artifact_index_sha256'],'INDEX_CHAIN')
    need(term['runner_freeze_root_sha256']==manifest['runner_freeze_root_sha256']==request['runtime']['source_code_root_sha256'],'RUNNER_CHAIN')
    for ref in out['artifacts']:
        _,raw=by_suffix(t,'/'+Path(ref['path']).name)
        need(sha(raw)==ref['sha256'] and len(raw)==ref['size_bytes'],'OUTPUT_INDEX_BYTES:'+ref['logical_name'])
    declared=obj(by_suffix(t,'/adapter_artifact_manifest.json')[1])
    from round_training.common import canonical_json_bytes as training_json_bytes
    need(sha(training_json_bytes({'required_files':declared['required_files'],'files':declared['files']}))==declared['adapter_bundle_sha256']==manifest['adapter_bundle_sha256'],'ADAPTER_MANIFEST_HASH')
    need(manifest['initial_trainable_parameter_sha256']==init['initial_trainable_parameter_sha256'],'INITIAL_PARAMETER_IDENTITY')
    need(candidate['promotion_eligible'] is False and manifest['promotion_eligible'] is False and manifest['diagnostic_only'] is True,'DIAGNOSTIC_SCOPE_LOST')
    need(candidate['evaluation_executed'] is False,'EVALUATION_ALREADY_RECORDED')
    need(candidate['archive_provenance_complete']==manifest['archive_provenance_complete']==plan['archive_provenance_complete'],'ARCHIVAL_STATE_CHANGED')
    ref=request['runtime']['formal_source']
    formal=load_pure_training_checks(formal_source,ref['sha256'])
    clean.bind_formal_constants(formal,c,order)
    # Reuse the original native-row loader with byte-identical archive files.
    # Only temporary local paths change; all content and schema checks remain.
    import tempfile, copy
    from round_training.adapters import frozen_formal_train_peft as old_adapter
    with tempfile.TemporaryDirectory() as td:
        local=copy.deepcopy(c)
        for field,name in [('path','POLICY_T2_TRAINER_NATIVE_V1.jsonl'),
                           ('manifest_path','POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json')]:
            path=Path(td)/name;path.write_bytes(q[name]);local['dataset'][field]=str(path)
        records=old_adapter._load_records(local)
        old_adapter._verify_order(formal,records=records,contract=local,sample_order=order)
    formal.load_frozen_materialized_records=lambda:records
    original_plan=formal.build_formal_run_plan(seed=c['budget']['training_seed'])
    ledger=[obj(x) for x in by_suffix(t,'/training_step_ledger.jsonl')[1].splitlines() if x]
    for row in ledger:
        row['case_ids']=tuple(row['case_ids']);row['example_indices']=tuple(row['example_indices'])
    totals=formal.validate_completed_formal_ledger(plan=original_plan,ledger=ledger)
    for k,v in totals.items():need(manifest[k]==v,'LEDGER_TOTAL_MISMATCH:'+k)
    need(auth['authorized_optimizer_steps']==totals['optimizer_step_count'] and auth['authorized_target_loss_tokens']==totals['target_loss_token_count'],'AUTHORIZED_BUDGET')
    return {**totals,'round_id':plan['round_id'],'training_plan_sha256':plan['training_plan_sha256'],
        'adapter_bundle_sha256':declared['adapter_bundle_sha256'],'adapter_file_manifest':declared,
        'initial_parameters':manifest['initial_trainable_parameter_sha256'],
        'final_parameters':manifest['final_trainable_parameter_sha256'],
        'parameters_changed':manifest['initial_trainable_parameter_sha256']!=manifest['final_trainable_parameter_sha256'],
        'stage_receipt_sha256':term['stage_receipt_sha256'],'stage_binding_sha256':binding['stage_binding_sha256'],
        'promotion_eligible':False,'archive_provenance_complete':manifest['archive_provenance_complete'],
        'candidate':candidate,'plan':plan,'base_binding':init['base_binding']}


def load_pure_training_checks(path:Path,expected_sha:str):
    """Load original pure functions only, exactly as the prior handoff does.

    No Transformers/PEFT import, model initialization or optimizer code runs.
    """
    import ast, math, types
    from collections.abc import Sequence
    raw=regular(path).read_bytes();need(sha(raw)==expected_sha,'FORMAL_SOURCE_SHA')
    names={'_ordering_key','build_training_orders','group_training_orders',
           'validate_formal_seed','build_formal_run_plan','validate_completed_formal_ledger'}
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    need(len(nodes)==len(names) and {n.name for n in nodes}==names,'PURE_CHECK_FUNCTION_SET')
    m=types.ModuleType('_verified_formal_training_checks')
    m.__dict__.update(math=math,hashlib=hashlib,Sequence=Sequence)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),m.__dict__)
    return m


def pool_references(q:dict)->dict:
    index=obj(q['INPUT_ARTIFACT_INDEX.json']);audit=obj(q['CLEAN_DATA_ACCESS_AUDIT.json'])
    pools={name:None for name in ('TRAIN_UPDATE','TRAIN_SELECT','TRAIN_AUDIT')}
    for ref in index['artifacts']:
        name=ref['logical_name']
        if name in pools:
            need(pools[name] is None,'DUPLICATE_POOL_REFERENCE')
            pools[name]={**ref,'expected_count':audit['pool_counts'][name]}
    need(all(pools.values()),'MISSING_POOL_REFERENCE')
    return pools


def load_bound_pool_metadata(refs:dict,helper,census:dict,per_task_cap:int)->dict:
    pools={}
    for name,ref in refs.items():
        raw=regular(Path(ref['path'])).read_bytes();need(sha(raw)==ref['sha256'],'POOL_FILE_HASH:'+name)
        rows=[obj(x) for x in raw.splitlines() if x]
        need(len(rows)==ref['expected_count'],'POOL_ROW_COUNT:'+name)
        pools[name]=rows
    helper.audit_pool_metadata(census,pools,per_task_cap)
    return pools


def draft_task_seed_grid(rows:list[dict],seeds:tuple[int,...])->dict:
    need(rows and seeds and len(set(seeds))==len(seeds) and all(type(x)is int and x>=0 for x in seeds),'GRID_INPUT')
    need(all(r.get('split')=='train' and r.get('train_pool')=='TRAIN_SELECT' for r in rows),'SELECT_TRAIN_ONLY')
    need(len({r['id'] for r in rows})==len(rows) and len({r['index'] for r in rows})==len(rows),'DUPLICATE_SELECT_IDENTITY')
    cross=[{'select_local_index':i,'source_index':r['index'],'task_id':r['id'],'gamefile_sha256':r['gamefile_sha256']} for i,r in enumerate(rows)]
    return {'schema_id':'SELECT_TASK_SEED_GRID_PROPOSAL_V1','status':'DRAFT_NOT_AUTHORIZED',
        'task_count':len(rows),'replicate_seeds':list(seeds),'paired_cells':len(rows)*len(seeds),
        'condition_episodes':2*len(rows)*len(seeds),'primary_statistical_unit':'unique_task',
        'order':'seed-major then bound metadata order','index_crosswalk':cross,
        'pairs':[{'task_id':r['id'],'select_local_index':i,'source_index':r['index'],'seed':seed}
                 for seed in seeds for i,r in enumerate(rows)],
        'protocol_frozen':False,'execution_authorized':False,
        'select_detail_visibility':'SELECT_SUMMARY_ONLY','benchmark_feedback_forbidden':True}


def verify_adapter_files(root:Path,manifest:dict)->None:
    need(root.is_dir() and not any(x.is_symlink() for x in (root,*root.parents)),'ADAPTER_DIRECTORY')
    entries=list(root.rglob('*'));need(not any(p.is_symlink() for p in entries),'ADAPTER_SYMLINK')
    names={str(p.relative_to(root)) for p in entries if p.is_file()}
    need(names==set(manifest['files']),'ADAPTER_FILE_SET')
    for name,spec in manifest['files'].items():
        need(not Path(name).is_absolute() and '..' not in Path(name).parts,'ADAPTER_FILE_PATH')
        p=regular(root/name)
        need(p.stat().st_size==spec['size_bytes'] and file_sha(p)==spec['sha256'],'ADAPTER_FILE_BYTES:'+name)


def write_once(path:Path,raw:bytes)->None:
    need(not any(p.is_symlink() for p in (path,*path.parents)),'OUTPUT_SYMLINK')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():need(path.is_file() and path.read_bytes()==raw,'OUTPUT_CONFLICT');return
    with path.open('xb') as f:f.write(raw)
