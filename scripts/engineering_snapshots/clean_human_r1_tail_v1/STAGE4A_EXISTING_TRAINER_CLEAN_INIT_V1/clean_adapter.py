"""Thin clean-parent adapter for the frozen Generic Training Stage V2.1.

The original seeded initializer, PEFT continuation adapter, optimizer loop,
loss normalization, schedule builder, ledger validator and writer are reused.
A seed-zero adapter is initialization evidence, NOT a trained pilot checkpoint.
"""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

TRAINER_REL=Path('scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build')

def need(ok: bool, why: str) -> None:
    if not ok: raise ValueError(why)

def cb(value: Any) -> bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def obj(raw: bytes) -> dict:
    from pchsi.reference_loop.canonical import strict_json_loads
    value=strict_json_loads(raw);need(isinstance(value,dict),'JSON_OBJECT_REQUIRED');return value

def regular(path: Path) -> Path:
    path=Path(path)
    need(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)), 'REGULAR_FILE_REQUIRED:'+str(path))
    return path

def file_sha(path: Path) -> str:
    p=regular(path);h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,regular(path));need(spec is not None and spec.loader is not None,'MODULE_SPEC')
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def checked_ref(ref: dict) -> Path:
    p=Path(ref['path']);need(file_sha(p)==ref['sha256'],'BOUND_FILE_HASH:'+str(p));return p

def validate_packet(files: dict[str,bytes]) -> dict:
    """Validate the frozen plan packet, not a newly invented scientific plan."""
    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.cognitive_runtime.researcher import finalize_field_adjudication
    from pchsi.round_control.role_authority import resolve_authority_plan,AuthorityPhaseV1,ResearchRoleV1
    from round_training.contracts import validate_training_contract
    ix=obj(files['FILES.sha256.json'])
    need(set(files)==set(ix)|{'FILES.sha256.json'},'PACKET_FILE_SET')
    for n,h in ix.items():need(sha(files[n])==h,'PACKET_FILE_HASH:'+n)
    get=lambda n:obj(files[n])
    plan=get('RESEARCH_PLANNER_TRAINING_PLAN_V1.json');c=get('ROUND_LOCAL_TRAINING_CONTRACT_V1.json');order=get('ROUND_SAMPLE_ORDER_MANIFEST_V1.json')
    ap=get('PRIMARY_PLAN_APPROVAL_RECEIPT.json');decision=get('PRIMARY_DECISION.json');nxt=get('NEXT_STAGE_BINDING.json');status=get('STATUS.json')
    need(plan['training_plan_sha256']==domain_hash(plan['schema_id'],plan,excluded_field='training_plan_sha256'),'PLAN_DOMAIN_HASH')
    adjud=get('POST_FIELD_ADJUDICATION.json');need(finalize_field_adjudication(adjud)==adjud,'ADJUDICATION_DOMAIN')
    need(ap['approval_status']=='FROZEN' and ap['training_plan_sha256']==plan['training_plan_sha256'],'PLAN_APPROVAL_REQUIRED')
    need(ap['decision_sha256']==sha(files['PRIMARY_DECISION.json'])==nxt['primary_decision_sha256'],'DECISION_APPROVAL_ID')
    need(ap['adjudication_sha256']==plan['post_adjudication_sha256']==adjud['adjudication_sha256'],'ADJUDICATION_PLAN_ID')
    auth=nxt['authority_context'];actor=resolve_authority_plan(phase=AuthorityPhaseV1(auth['phase']),takeover_evaluation=auth.get('takeover_evaluation')).primary_actor(ResearchRoleV1.RESEARCH_PLANNER_POST)
    need(actor==plan['decision_actor']==ap['decision_actor']==decision['decision_actor'],'PRIMARY_ACTOR_BINDING')
    if actor!='HUMAN':need(auth.get('registered_primary_decision_sha256')==ap['decision_sha256'],'REGISTERED_PRIMARY_DECISION_REQUIRED')
    need(status['training_plan_frozen'] is True and status['post_adjudication_frozen'] is True,'PLAN_NOT_FROZEN')
    need(status['clean_access_verified'] is True and get('CLEAN_DATA_ACCESS_AUDIT.json')['metadata_membership_verified'] is True,'CLEAN_ACCESS_REQUIRED')
    need(plan['interface_profile_id']=='I1_EXECUTION_PROFILE_V1','FROZEN_INTERFACE_CHANGED')
    recipe=plan['policy_training_recipe'];need(recipe['action']=='DIAGNOSTIC_TRAINING_PLAN','UNSUPPORTED_PLAN_NO_FALLBACK')
    need(recipe['selected_arm_ids']==['T0','T2'] and recipe['diagnostic_only'] is True and recipe['promotion_eligible'] is False,'DIAGNOSTIC_SCOPE')
    need(recipe['verified_positive'] is False and recipe['automatic_arm_fallback_allowed'] is False,'DIAGNOSTIC_LABELS')
    need(recipe['budget']==c['budget'] and recipe['optimization']==c['optimization'] and plan['peft']==c['peft'],'CONTRACT_DIFFERS_FROM_PLAN')
    need(c['parent']['policy_id']==plan['parent_policy_id'] and c['parent']['pilot_adapter_reuse_allowed'] is False,'CLEAN_PARENT_ONLY')
    need(c['parent']['base_model_local_path']==plan['parent_model_binding']['base_model_local_path'],'CLEAN_SNAPSHOT_BINDING')
    need(recipe['native_dataset_sha256']==c['dataset']['sha256']==sha(files['POLICY_T2_TRAINER_NATIVE_V1.jsonl']),'NATIVE_BYTES')
    for name,digest in nxt['input_file_sha256s'].items():need(sha(files[name])==digest,'NEXT_BINDING_FILE_HASH:'+name)
    validate_training_contract(c,order)
    need(c['budget']['micro_batch_size']==1,'EXISTING_SINGLETON_COLLATOR_ONLY')
    need(c['budget']['training_seed']==c['budget']['data_seed'],'MATCHED_SEEDS_REQUIRED')
    native=[obj(l) for l in files['POLICY_T2_TRAINER_NATIVE_V1.jsonl'].splitlines() if l]
    need(len(native)==c['dataset']['row_count'],'NATIVE_POPULATION')
    need(sum(sum(t!=-100 for t in r['tokenization']['labels'][1:]) for r in native)==c['dataset']['one_pass_target_loss_token_count'],'NATIVE_TARGET_COUNT')
    return {'plan':plan,'contract':c,'order':order,'next':nxt,'native':native,'approval':ap,'initializer':get('CLEAN_INITIALIZATION_HANDOFF.json'),'files':files}

def verify_clean_base(binding: dict) -> dict:
    """Use a frozen model-only byte manifest at the clean snapshot path."""
    mp=regular(Path(binding['manifest_path']))
    need(file_sha(mp)==binding['manifest_sha256'],'BASE_MANIFEST_HASH')
    m=json.loads(mp.read_bytes());root=Path(binding['snapshot_path'])
    need(root.is_dir() and not any(p.is_symlink() for p in (root,*root.parents)),'CLEAN_SNAPSHOT_NON_SYMLINK_REQUIRED')
    need(m['repository_id']==binding['repository_id'] and m['snapshot_revision']==binding['revision'],'BASE_REVISION')
    need(m.get('project_adapter') is None and m.get('lora_enabled') is False,'BASE_HAS_PROJECT_ADAPTER')
    entries=m.get('files');need(isinstance(entries,dict) and entries,'BASE_FILE_MAP')
    # Never load an old project adapter or unbound pickle weights from this path.
    for p in root.iterdir():
        need(not p.name.startswith('adapter_') and p.suffix not in {'.bin','.pt','.pth','.py'},'CLEAN_BASE_UNEXPECTED_ADAPTER_OR_EXECUTABLE')
    for name,spec in entries.items():
        rel=Path(name);need(not rel.is_absolute() and len(rel.parts)==1 and '\\' not in name,'BASE_FILE_PATH')
        p=regular(root/rel)
        need(p.stat().st_size==spec['size_bytes'] and file_sha(p)==spec['sha256'],'BASE_FILE_BYTES:'+name)
    weight_names={n for n in entries if n.endswith('.safetensors')}
    need(weight_names,'BASE_SAFETENSORS_REQUIRED')
    need({p.name for p in root.glob('*.safetensors')}==weight_names,'UNBOUND_BASE_WEIGHT_FILE')
    index=root/'model.safetensors.index.json'
    if index.exists():
        need(index.name in entries,'UNBOUND_WEIGHT_INDEX')
        shards=set(json.loads(index.read_bytes())['weight_map'].values())
        need(shards==weight_names,'BASE_INDEX_SHARD_SET')
    return m

def bind_formal_constants(parent, contract: dict, order: dict) -> None:
    """Round-local parameters, identical to the existing adapter's binding."""
    b=contract['budget'];d=contract['dataset'];o=contract['optimization'];p=contract['peft']
    mapping={'FORMAL_TRAINING_SEEDS':(b['training_seed'],),'FORMAL_EXAMPLE_COUNT':d['row_count'],
        'FORMAL_DATASET_PASSES':b['epochs'],'FORMAL_MICRO_BATCH':b['micro_batch_size'],
        'FORMAL_GRAD_ACCUM':b['gradient_accumulation_steps'],'FORMAL_EFFECTIVE_BATCH':b['effective_batch_size'],
        'FORMAL_STEPS_PER_PASS':b['optimizer_steps']//b['epochs'],'FORMAL_OPTIMIZER_STEPS':b['optimizer_steps'],
        'FORMAL_TARGET_LOSS_TOKENS_PER_PASS':d['one_pass_target_loss_token_count'],
        'FORMAL_TARGET_LOSS_TOKEN_BUDGET':b['target_loss_token_budget'],'FORMAL_WARMUP_STEPS':o['warmup_steps'],
        'FORMAL_MAX_SEQUENCE_LENGTH':d['max_sequence_length'],'FORMAL_LEARNING_RATE':o['learning_rate'],
        'FORMAL_WEIGHT_DECAY':o['weight_decay'],'FORMAL_MAX_GRAD_NORM':o['max_grad_norm'],
        'FORMAL_LORA_R':p['r'],'FORMAL_LORA_ALPHA':p['lora_alpha'],'FORMAL_LORA_DROPOUT':p['lora_dropout'],
        'FORMAL_LORA_TARGET_MODULES':tuple(p['target_modules']),'_ORDER_DOMAIN':order['ordering_domain']}
    for k,v in mapping.items():setattr(parent,k,v)

def load_clean_formal(contract: dict, order: dict):
    rt=contract['clean_runtime'];ref=rt['formal_source'];checked_ref(ref)
    parent=module(Path(ref['path']),'_clean_bound_frozen_formal_train')
    bind_formal_constants(parent,contract,order)
    parent.BASE_MODEL_SNAPSHOT_PATH=Path(rt['base_binding']['snapshot_path'])
    # Replace pilot materialization-dependent artifact lookup with byte checking
    # against the same immutable base-model manifest, at the clean location.
    parent.verify_exact_base_model_artifact=lambda:verify_clean_base(rt['base_binding'])
    return parent

def verify_seed_zero_receipt(receipt: dict, plan: dict, runtime: dict) -> None:
    need(receipt.get('schema_id')=='CLEAN_SEEDED_LORA_INITIALIZATION_RECEIPT_V1','SMOKE_RECEIPT_SCHEMA')
    from round_training.common import require_domain_sha
    require_domain_sha(receipt,schema_id=receipt['schema_id'],sha_field='initialization_receipt_sha256')
    need(receipt.get('status')=='PASS' and receipt.get('training_executed') is False and receipt.get('optimizer_step_count')==0,'ZERO_STEP_SMOKE_REQUIRED')
    need(receipt['training_plan_sha256']==plan['training_plan_sha256'],'SMOKE_PLAN_ID')
    need(receipt['seed']==plan['policy_training_recipe']['budget']['training_seed'],'SMOKE_SEED')
    need(receipt['lora_a_nonzero'] is True and receipt['lora_b_all_zero'] is True and receipt['base_parameters_frozen'] is True,'INITIALIZATION_NOT_NOOP_LORA')
    need(receipt['repeat_seed_parameter_hash_equal'] is True and receipt['saved_adapter_reload_hash_equal'] is True,'INITIALIZATION_HASH_REPLAY')
    need(receipt['enabled_vs_disabled_logits_exact_equal'] is True and receipt['logits_finite'] is True,'INITIALIZATION_LOGITS')
    need(receipt['initial_trainable_parameter_sha256']==receipt['repeat_initial_trainable_parameter_sha256']==receipt['reloaded_trainable_parameter_sha256'],'INITIAL_PARAMETER_HASH_MISMATCH')
    if runtime:
        need(receipt['source_code_root_sha256']==runtime['source_code_root_sha256'],'SMOKE_CODE_ROOT')
        need(receipt['base_binding']==runtime['base_binding'],'SMOKE_BASE_BINDING')

def _configured_legacy(context):
    """Load an isolated copy of the existing adapter and bind only clean inputs."""
    c=context.training_contract;rt=c['clean_runtime']
    checked_ref(rt['legacy_adapter_source'])
    old=module(Path(rt['legacy_adapter_source']['path']),'_isolated_existing_formal_peft_adapter')
    install=old._install_parent_adapter
    # Keep old _build_model unchanged. Its parent adapter now is the freshly
    # initialized step-zero adapter, never a pilot-trained checkpoint.
    old._load_parent_module=lambda contract:load_clean_formal(contract,context.sample_order)
    def install_clean(parent,*,context):
        install(parent,context=context)
        from round_training.contracts import validate_training_contract
        def check_current():
            need(file_sha(context.package_root/context.binding['training_contract_ref']['path'])==context.binding['training_contract_ref']['sha256'],'RUNTIME_CONTRACT_CHANGED')
            validate_training_contract(context.training_contract,context.sample_order)
            old.validate_runtime_capabilities(context.training_contract)
        def check_data():
            records=old._load_records(context.training_contract)
            old._verify_order(parent,records=records,contract=context.training_contract,sample_order=context.sample_order)
            return records
        # The old formal schedule has an exact pilot effective-batch == 4
        # assertion. The frozen generic contract now owns that round-local
        # value; use its full budget/order checks, not a no-op or padding.
        def check_schedule():
            check_current();check_data()
            need(parent.FORMAL_EFFECTIVE_BATCH==context.training_contract['budget']['effective_batch_size'],'FORMAL_EFFECTIVE_BATCH_DRIFT')
            need(parent.FORMAL_MICRO_BATCH==1,'SINGLETON_COLLATOR_REQUIRED')
            parent.build_formal_run_plan(seed=context.training_contract['budget']['training_seed'])
        parent.verify_frozen_scientific_config=check_current
        parent.verify_frozen_materialization=check_data
        parent.verify_formal_schedule=check_schedule
        original_builder=parent.build_formal_run_manifest
        def run_manifest(**kw):
            out=original_builder(**kw)
            out.update(parent_initialization='CLEAN_SEEDED_ZERO_STEP_ADAPTER',
                initialization_receipt_sha256=rt['initialization_receipt_sha256'],
                interface_profile_id='I1_EXECUTION_PROFILE_V1',archive_provenance_complete=False)
            return out
        parent.build_formal_run_manifest=run_manifest
    old._install_parent_adapter=install_clean
    old.input_artifact_refs=lambda context:input_artifact_refs(context)
    return old

def validate_profile_without_model_load(context) -> dict:
    c=context.training_contract;rt=c['clean_runtime']
    from round_training.contracts import validate_training_contract
    validate_training_contract(c,context.sample_order)
    receipt=obj(checked_ref(rt['initialization_receipt_ref']).read_bytes())
    plan=obj(checked_ref(rt['plan_ref']).read_bytes())
    verify_seed_zero_receipt(receipt,plan,rt)
    need(c['parent']['policy_id']==plan['parent_policy_id'],'PARENT_POLICY_ID')
    need(c['parent']['final_trainable_parameter_sha256']==receipt['initial_trainable_parameter_sha256'],'PARENT_INITIAL_HASH')
    need(c['parent']['adapter_path']==receipt['adapter_path'],'ONLY_SMOKE_ADAPTER_ALLOWED')
    need(c['parent']['pilot_adapter_reuse_allowed'] is False,'PILOT_ADAPTER_FORBIDDEN')
    return _configured_legacy(context).validate_profile_without_model_load(context)

def input_artifact_refs(context) -> list[dict]:
    c=context.training_contract;rt=c['clean_runtime']
    refs=[]
    for name,ref,kind in [
        ('FROZEN_FORMAL_TRAIN_SOURCE',rt['formal_source'],'EXECUTION_SOURCE'),
        ('EXISTING_PEFT_ADAPTER_SOURCE',rt['legacy_adapter_source'],'EXECUTION_SOURCE'),
        ('MODEL_INITIALIZATION_RECEIPT',rt['initialization_receipt_ref'],'VALIDATED_SCIENTIFIC_ARTIFACT'),
        ('CURRENT_PLANNER_PLAN',rt['plan_ref'],'DECISION_ARTIFACT'),
        ('BASE_MODEL_BYTE_MANIFEST',{'path':rt['base_binding']['manifest_path'],'sha256':rt['base_binding']['manifest_sha256']},'MODEL_ARTIFACT_MANIFEST'),
        ('CLEAN_STEP_ZERO_ADAPTER_MANIFEST',{'path':c['parent']['adapter_artifact_manifest_path'],'sha256':c['parent']['adapter_artifact_manifest_sha256']},'MODEL_ARTIFACT_MANIFEST'),
        ('TRAINER_NATIVE_DATASET',{'path':c['dataset']['path'],'sha256':c['dataset']['sha256']},'TRAINING_DATASET'),
        ('TRAINER_NATIVE_DATASET_MANIFEST',{'path':c['dataset']['manifest_path'],'sha256':c['dataset']['manifest_file_sha256']},'TRAINING_DATASET_MANIFEST')]:
        p=checked_ref(ref);refs.append({'logical_name':name,'path':str(p),'sha256':ref['sha256'],'size_bytes':p.stat().st_size,'retention_class':kind,'schema_id':None})
    m=json.loads(Path(c['parent']['adapter_artifact_manifest_path']).read_bytes())
    for name,spec in m['files'].items():
        p=checked_ref({'path':str(Path(c['parent']['adapter_path'])/name),'sha256':spec['sha256']})
        refs.append({'logical_name':'CLEAN_STEP_ZERO_'+name,'path':str(p),'sha256':spec['sha256'],'size_bytes':p.stat().st_size,'retention_class':'MODEL_ARTIFACT','schema_id':None})
    return refs

def execute_training_stage(*,context,output_dir:Path,runner_freeze_root_sha256:str) -> dict:
    validate_profile_without_model_load(context)
    return _configured_legacy(context).execute_training_stage(context=context,output_dir=output_dir,runner_freeze_root_sha256=runner_freeze_root_sha256)
