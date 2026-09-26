#!/usr/bin/env python3
"""Existing Trainer clean-parent binding. No arm selection or optimizer rewrite.

Default: offline preparation. Explicit --submit-smoke: initialization only.
Explicit --submit-training --approve-binding SHA: separate single-run authority.
"""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, os, re, shlex, stat, subprocess, sys, tempfile, zipfile
from pathlib import Path
import clean_adapter as a
HERE=Path(__file__).resolve().parent


def write_once(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() or path.is_symlink():
        a.need(a.regular(path).read_bytes()==raw,'EXISTING_OUTPUT_DIFFERS:'+str(path));return
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        view=memoryview(raw)
        while view:
            n=os.write(fd,view);a.need(n>0,'WRITE_NO_PROGRESS');view=view[n:]
        os.fsync(fd)
    finally:os.close(fd)

def put(path: Path, value: dict) -> None:write_once(path,a.cb(value))

def tagged(value: dict, field: str) -> dict:
    from round_training.common import domain_sha256
    x=copy.deepcopy(value);x[field]=domain_sha256(x['schema_id'],x,sha_field=field);return x

def read_zip(path:Path,digest:str) -> dict[str,bytes]:
    a.need(a.file_sha(path)==digest,'SOURCE_REVIEW_HASH')
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();a.need(len({i.filename for i in infos})==len(infos),'DUPLICATE_ZIP')
        a.need(sum(i.file_size for i in infos)<150_000_000,'ZIP_SIZE_LIMIT')
        for i in infos:
            p=Path(i.filename);a.need(not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename and not stat.S_ISLNK(i.external_attr>>16),'UNSAFE_ZIP')
        return {i.filename:z.read(i) for i in infos if not i.is_dir()}

def setup(request:dict,verify=True) -> Path:
    repo=Path(request['repo'])
    for p in (repo/'src',repo/a.TRAINER_REL,HERE):
        if str(p) not in sys.path:sys.path.insert(0,str(p))
    from round_training import contracts
    a.need(Path(contracts.__file__).resolve()==repo/a.TRAINER_REL/'round_training/contracts.py','WRONG_TRAINER_IMPORT')
    if verify:
        # Reuse the full-tree verifier already used in Stage3V/3Y/3Z.
        src=request['existing_verifier'];p=a.checked_ref(src)
        helper=p.parent/'orchestration.py';a.need(a.file_sha(helper)==src['orchestration_sha256'],'VERIFIER_DEPENDENCY_CHANGED')
        prior=sys.modules.pop('orchestration',None)
        try:
            a.module(helper,'orchestration');m=a.module(p,'_existing_full_tree_verifier')
            m.strict_repo(repo,request['fixed_head'],request['fixed_tree'])
        finally:
            sys.modules.pop('orchestration',None)
            if prior is not None:sys.modules['orchestration']=prior
    return repo

def package_identity() -> str:
    mp=HERE/'PACKAGE_FILES.sha256'
    for line in mp.read_text().splitlines():
        if not line:continue
        digest,rel=line.split('  ',1);p=Path(rel)
        a.need(not p.is_absolute() and '..' not in p.parts,'PACKAGE_PATH')
        a.need(a.file_sha(HERE/p)==digest,'PACKAGE_HASH:'+rel)
    return a.file_sha(mp)

def load_source(request:dict) -> dict:
    setup(request);files=read_zip(Path(request['source_review']['path']),request['source_review']['sha256']);data=a.validate_packet(files)
    nxt=data['next'];root=Path(nxt['plan_path']).parent
    # The packet is not a substitute for verifying the active upstream files.
    for name,digest in nxt['input_file_sha256s'].items():
        a.need(a.file_sha(root/name)==digest,'UPSTREAM_BOUND_BYTES_CHANGED:'+name)
    for name in ('CLEAN_INITIALIZATION_HANDOFF.json','PRIMARY_DECISION.json'):
        a.need(a.file_sha(root/name)==a.sha(files[name]),'UPSTREAM_HANDOFF_CHANGED:'+name)
    refs=a.obj(files['INPUT_ARTIFACT_INDEX.json'])
    # Existing artifact index records both source archives and split metadata.
    for ref in refs.get('artifacts',refs.get('refs',[])):
        if 'path' in ref and 'sha256' in ref:a.checked_ref(ref)
    a.need(data['initializer']['clean_snapshot_path']==data['contract']['parent']['base_model_local_path'],'INITIALIZER_SNAPSHOT')
    a.checked_ref({'path':data['initializer']['source_path'],'sha256':data['initializer']['source_sha256']})
    return data

def execution_sources(request:dict,data:dict) -> dict:
    repo=Path(request['repo']);trainer=repo/a.TRAINER_REL
    refs={str(p):a.file_sha(p) for p in sorted((trainer/'round_training').rglob('*.py'))}
    refs[data['initializer']['source_path']]=data['initializer']['source_sha256']
    refs[str(HERE/'clean_adapter.py')]=a.file_sha(HERE/'clean_adapter.py')
    refs[str(HERE/'run_stage.py')]=a.file_sha(HERE/'run_stage.py')
    return refs

def prepare(request:dict) -> Path:
    pkg_sha=package_identity();data=load_source(request);repo=Path(request['repo'])
    # Read only the immutable model-byte manifest reference from the existing
    # profile. No pilot dataset, training config, adapter or outputs are loaded.
    legacy_profile=a.obj((repo/a.TRAINER_REL/'profiles/human_reference_t2/ROUND_LOCAL_TRAINING_CONTRACT_V1.json').read_bytes())
    lp=legacy_profile['parent'];c=data['contract'];init=data['initializer']
    a.need(lp['base_model_revision']==c['parent']['base_model_revision'],'BASE_REVISION_REUSE_MISMATCH')
    base={'snapshot_path':c['parent']['base_model_local_path'],
          'manifest_path':lp['base_model_artifact_manifest_path'],
          'manifest_sha256':lp['base_model_artifact_manifest_sha256'],
          'repository_id':lp['base_model_repository'],'revision':c['parent']['base_model_revision']}
    a.need(a.file_sha(Path(base['manifest_path']))==base['manifest_sha256'],'BASE_MANIFEST_HASH')
    sources=execution_sources(request,data);code_root=a.sha(a.cb(sources))
    identity=a.sha(a.cb({'plan':data['plan']['training_plan_sha256'],'source_review':request['source_review']['sha256'],
        'package':pkg_sha,'code':code_root,'base':base}))
    root=Path(request['output_parent'])/identity
    formal={'path':init['source_path'],'sha256':init['source_sha256']}
    legacy=repo/a.TRAINER_REL/'round_training/adapters/frozen_formal_train_peft.py'
    rt={'base_binding':base,'formal_source':formal,'legacy_adapter_source':{'path':str(legacy),'sha256':a.file_sha(legacy)},
        'source_code_root_sha256':code_root,'source_code_files':sources,
        'plan_ref':{'path':data['next']['plan_path'],'sha256':a.sha(data['files']['RESEARCH_PLANNER_TRAINING_PLAN_V1.json'])}}
    prepared={'schema_id':'EXISTING_CLEAN_INITIALIZATION_REQUEST_V1','schema_version':1,'package_sha256':pkg_sha,
        'request':request,'plan_sha256':data['plan']['training_plan_sha256'],'runtime':rt,
        'upstream_next_stage':data['next'],'upstream_review_sha256':request['source_review']['sha256'],
        'output_root':str(root),'training_authorized':False,'model_initialization_authorized':False}
    prepared=tagged(prepared,'request_sha256')
    put(root/'INITIALIZATION_REQUEST.json',prepared)
    write_once(root/'ROUND_SAMPLE_ORDER.unchanged.json',data['files']['ROUND_SAMPLE_ORDER_MANIFEST_V1.json'])
    write_once(root/'ROUND_TRAINING_CONTRACT.unchanged.json',data['files']['ROUND_LOCAL_TRAINING_CONTRACT_V1.json'])
    print('PREPARED_ROOT='+str(root),flush=True)
    print('PLAN_SHA256='+data['plan']['training_plan_sha256'],flush=True)
    print('FROZEN_BUDGET='+json.dumps(c['budget'],sort_keys=True),flush=True)
    print('CORE_REPOSITORY_MODIFIED=false\nTRAINING_EXECUTION=false',flush=True)
    return root

def checked_request(path:Path) -> dict:
    raw=a.regular(path).read_bytes()
    # Slurm worker intentionally does not inherit caller PYTHONPATH. Bootstrap
    # the fixed repository before importing its strict JSON/domain validators.
    bootstrap=json.loads(raw);setup(bootstrap['request'])
    x=a.obj(raw)
    from round_training.common import require_domain_sha
    require_domain_sha(x,schema_id=x['schema_id'],sha_field='request_sha256')
    a.need(x['package_sha256']==package_identity(),'PACKAGE_CHANGED_AFTER_PREPARE')
    for p,digest in x['runtime']['source_code_files'].items():a.need(a.file_sha(Path(p))==digest,'FROZEN_SOURCE_CHANGED:'+p)
    a.need(a.sha(a.cb(x['runtime']['source_code_files']))==x['runtime']['source_code_root_sha256'],'CODE_ROOT_HASH')
    return x

def versions() -> dict:
    import platform,importlib.metadata
    return {'python':platform.python_version(),**{n:importlib.metadata.version(n) for n in ('torch','peft','transformers','tokenizers','numpy','safetensors')}}

def smoke(path:Path) -> None:
    x=checked_request(path);root=Path(x['output_root'])
    receipt_path=root/'INITIALIZATION_RECEIPT.json'
    if receipt_path.exists():
        compile_binding(x,a.obj(receipt_path.read_bytes()));print('EXISTING_INITIALIZATION_REUSED=true');return
    auth=a.obj(a.regular(root/'SMOKE_AUTHORIZATION.json').read_bytes())
    a.need(auth.get('request_sha256')==x['request_sha256'] and auth.get('authorization_scope')=='INITIALIZATION_ONLY_NO_OPTIMIZER','SMOKE_AUTHORIZATION_REQUIRED')
    lock=root/'SMOKE_EXECUTION_STARTED.json'
    a.need(not lock.exists(),'SMOKE_ATTEMPT_ALREADY_STARTED_NO_AUTOMATIC_RETRY')
    put(lock,{'request_sha256':x['request_sha256'],'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'optimizer_step_count':0})
    data=load_source(x['request']);c=copy.deepcopy(data['contract']);c['clean_runtime']=x['runtime']
    import torch,gc
    a.need(torch.cuda.is_available() and torch.cuda.device_count()==1,'ONE_CUDA_DEVICE_REQUIRED')
    a.need(torch.cuda.is_bf16_supported(),'BF16_REQUIRED')
    print('PHASE=VERIFY_CLEAN_BASE_MODEL_BYTES',flush=True);a.verify_clean_base(x['runtime']['base_binding'])
    parent=a.load_clean_formal(c,data['order']);model=None
    try:
        print('PHASE=EXISTING_SEEDED_LORA_INITIALIZATION_ZERO_STEPS',flush=True)
        model=parent.build_seeded_formal_lora_model(seed=c['budget']['training_seed'],device='cuda')
        params=dict(model.named_parameters());aa=[p for n,p in params.items() if '.lora_A.' in n];bb=[p for n,p in params.items() if '.lora_B.' in n]
        a.need(aa and bb,'LORA_A_B_REQUIRED')
        zero=all(torch.count_nonzero(p).item()==0 for p in bb)
        nonzero=all(torch.isfinite(p).all().item() and torch.count_nonzero(p).item()>0 for p in aa)
        frozen=all(not p.requires_grad for n,p in params.items() if 'lora_' not in n.lower())
        a.need(zero and nonzero and frozen,'SEEDED_LORA_INITIALIZATION_SHAPE_OR_FREEZE')
        h1=parent.hash_trainable_parameters(model)
        model.eval();row=data['native'][0]['tokenization'];ids=torch.tensor([row['input_ids'][:16]],dtype=torch.long,device='cuda')
        with torch.inference_mode():
            enabled=model(input_ids=ids).logits
            with model.disable_adapter():disabled=model(input_ids=ids).logits
            same=torch.equal(enabled,disabled);finite=bool(torch.isfinite(enabled).all() and torch.isfinite(disabled).all())
        a.need(same and finite,'ZERO_STEP_LORA_NOT_IDENTITY_OR_NONFINITE')
        adapter_root=root/'seed_zero_adapter';a.need(not adapter_root.exists(),'INITIALIZATION_OUTPUT_EXISTS')
        model.save_pretrained(adapter_root,safe_serialization=True)
        adapter_manifest=parent.build_adapter_artifact_manifest(adapter_root)
        adapter_manifest.update(schema_id='CLEAN_SEEDED_ZERO_STEP_ADAPTER_MANIFEST_V1',initialization_only=True,optimizer_step_count=0,training_executed=False)
        put(root/'SEED_ZERO_ADAPTER_MANIFEST.json',adapter_manifest)
        del model,params,aa,bb,enabled,disabled;model=None;gc.collect();torch.cuda.empty_cache()
        print('PHASE=REPEAT_SEED_HASH_CHECK',flush=True)
        model=parent.build_seeded_formal_lora_model(seed=c['budget']['training_seed'],device='cuda');h2=parent.hash_trainable_parameters(model)
        a.need(h1==h2,'SEEDED_INITIALIZATION_NOT_REPRODUCIBLE')
        del model;model=None;gc.collect();torch.cuda.empty_cache()
        print('PHASE=EXISTING_PEFT_ADAPTER_RELOAD_HASH_CHECK',flush=True)
        # Run the already-built continuation adapter's actual load/hash gate.
        legacy=a.module(Path(x['runtime']['legacy_adapter_source']['path']),'_smoke_original_peft_adapter')
        reload_contract=copy.deepcopy(c);reload_contract['parent'].update(adapter_path=str(adapter_root),final_trainable_parameter_sha256=h1)
        model=legacy._build_model(parent,contract=reload_contract,seed=c['budget']['training_seed'],device='cuda');h3=parent.hash_trainable_parameters(model)
        a.need(h3==h1,'SAVED_ADAPTER_RELOAD_MISMATCH')
        receipt=tagged({'schema_id':'CLEAN_SEEDED_LORA_INITIALIZATION_RECEIPT_V1','schema_version':1,'status':'PASS',
            'request_sha256':x['request_sha256'],'training_plan_sha256':data['plan']['training_plan_sha256'],
            'seed':c['budget']['training_seed'],'base_binding':x['runtime']['base_binding'],
            'source_code_root_sha256':x['runtime']['source_code_root_sha256'],
            'initial_trainable_parameter_sha256':h1,'repeat_initial_trainable_parameter_sha256':h2,'reloaded_trainable_parameter_sha256':h3,
            'repeat_seed_parameter_hash_equal':True,'saved_adapter_reload_hash_equal':True,'lora_a_nonzero':True,'lora_b_all_zero':True,
            'base_parameters_frozen':True,'enabled_vs_disabled_logits_exact_equal':True,'logits_finite':True,
            'probe_prefix_token_count':int(ids.shape[-1]),'adapter_path':str(adapter_root),
            'adapter_manifest_path':str(root/'SEED_ZERO_ADAPTER_MANIFEST.json'),
            'adapter_manifest_sha256':a.file_sha(root/'SEED_ZERO_ADAPTER_MANIFEST.json'),
            'adapter_bundle_sha256':adapter_manifest['adapter_bundle_sha256'],'software_versions':versions(),
            'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'optimizer_step_count':0,'training_executed':False,
            'new_trained_checkpoint_created':False},'initialization_receipt_sha256')
        put(receipt_path,receipt)
        compile_binding(x,receipt)
        print('CLEAN_INITIALIZATION_SMOKE_PASS=true\nOPTIMIZER_STEPS_EXECUTED=0\nTRAINING_EXECUTION=false',flush=True)
    finally:
        if model is not None:del model
        gc.collect();torch.cuda.empty_cache()

def compile_binding(x:dict,receipt:dict) -> dict:
    data=load_source(x['request']);a.verify_seed_zero_receipt(receipt,data['plan'],x['runtime']);root=Path(x['output_root']);c=copy.deepcopy(data['contract'])
    p=c['parent'];p.update(formal_train_path=x['runtime']['formal_source']['path'],formal_train_sha256=x['runtime']['formal_source']['sha256'],
        adapter_path=receipt['adapter_path'],adapter_artifact_manifest_path=receipt['adapter_manifest_path'],
        adapter_artifact_manifest_sha256=receipt['adapter_manifest_sha256'],adapter_bundle_sha256=receipt['adapter_bundle_sha256'],
        final_trainable_parameter_sha256=receipt['initial_trainable_parameter_sha256'],
        load_semantics='PEFT_LOAD_FRESH_SEEDED_STEP_ZERO_ADAPTER_IS_TRAINABLE_TRUE',
        initialization='CLEAN_BASE_SEEDED_LORA_SMOKE_VERIFIED')
    c['parent_compatibility_approval_token']='ROUND_TRAINING_EXECUTION_APPROVED_CLEAN_SEEDED_V1'
    c['execution_readiness']='SMOKE_VERIFIED_SEPARATE_EXECUTION_AUTHORIZATION_REQUIRED'
    rt=copy.deepcopy(x['runtime']);rt.update(initialization_receipt_ref={'path':str(root/'INITIALIZATION_RECEIPT.json'),'sha256':a.file_sha(root/'INITIALIZATION_RECEIPT.json')},
        initialization_receipt_sha256=receipt['initialization_receipt_sha256'])
    c['clean_runtime']=rt
    # No scientific fields are changed: only clean initialization/runtime refs.
    for key in ('budget','optimization','peft','dataset','execution','condition_id','round_id','diagnostic_only','promotion_eligible'):
        a.need(c[key]==data['contract'][key],'BINDING_CHANGED_FROZEN_SECTION:'+key)
    put(root/'TRAINING_CONTRACT.json',c)
    role={'schema_id':'ROUND_ROLE_BINDING_MANIFEST_V1','schema_version':1,'role_id':'TRAINER','round_id':c['round_id'],
        'role_kind':'TRAINING_EXECUTOR','implementation_kind':'DETERMINISTIC','authority_profile_id':'EXECUTE_FROZEN_TRAINING_CONTRACT_ONLY',
        'model_or_human_identity':'EXISTING_GENERIC_STAGE_CLEAN_ZERO_STEP_ADAPTER','shadow_only':False,
        'runtime_manifest_sha256':rt['source_code_root_sha256'],'checkpoint_or_adapter_sha256':receipt['adapter_bundle_sha256'],
        'schema_bundle_sha256':a.file_sha(root/'TRAINING_CONTRACT.json'),'visibility_profile_id':'TRAINING_ARTIFACTS_ONLY','prompt_bundle_sha256':None}
    put(root/'TRAINER_ROLE_BINDING.json',role)
    def ref(path:Path,schema=None):return {'path':str(path),'sha256':a.file_sha(path),'schema_id':schema}
    upstream=[]
    source_root=Path(data['next']['plan_path']).parent
    for name,digest in data['next']['input_file_sha256s'].items():
        upstream.append({'logical_name':'UPSTREAM_'+name,'path':str(source_root/name),'sha256':digest,'schema_id':None,'retention_class':'VALIDATED_SCIENTIFIC_ARTIFACT'})
    binding=tagged({'schema_id':'ROUND_TRAINING_STAGE_BINDING_V1','schema_version':1,'round_id':c['round_id'],
        'stage_id':'TRAINING_EXECUTION','profile_id':c['profile_id'],'package_root_relative_to_binding':'.',
        'trainer_role_binding_ref':ref(root/'TRAINER_ROLE_BINDING.json','ROUND_ROLE_BINDING_MANIFEST_V1'),
        'training_contract_ref':ref(root/'TRAINING_CONTRACT.json','ROUND_LOCAL_TRAINING_CONTRACT_V1'),
        'sample_order_ref':ref(Path(data['next']['sample_order_path']),'ROUND_SAMPLE_ORDER_MANIFEST_V1'),
        'runtime_adapter_ref':ref(HERE/'clean_adapter.py'),'upstream_artifact_refs':upstream,'previous_stage_receipt_sha256':None,
        'output_policy':{'training_output_parent':str(root/'training_outputs'),'stage_attempt_parent':str(root/'training_attempts'),
            'require_direct_child':True,'require_basename_equals_execution_attempt_id':True}},'stage_binding_sha256')
    put(root/'TRAINING_STAGE_BINDING.json',binding)
    from round_training.contracts import load_stage_context
    ctx=load_stage_context(root/'TRAINING_STAGE_BINDING.json');a.validate_profile_without_model_load(ctx)
    put(root/'NEXT_STAGE_BINDING.json',{'schema_id':'CLEAN_EXISTING_TRAINER_READY_V1','training_plan_sha256':data['plan']['training_plan_sha256'],
        'stage_binding_path':str(root/'TRAINING_STAGE_BINDING.json'),'stage_binding_sha256':binding['stage_binding_sha256'],
        'runner_freeze_root_sha256':rt['source_code_root_sha256'],'initialization_receipt_sha256':receipt['initialization_receipt_sha256'],
        'existing_entrypoint':'round_training.stage_runner.run_training_stage','training_execution_authorized':False,
        'archive_provenance_complete':False,'promotion_eligible':False,'next_gate':'SEPARATE_TRAINER_EXECUTION_AUTHORIZATION'})
    bundle=review_bundle(root,'INITIALIZATION_AND_BINDING_REVIEW.zip')
    print('EXISTING_TRAINER_BINDING_READY=true\nSTAGE_BINDING_SHA256='+binding['stage_binding_sha256'],flush=True)
    print('NEXT_GATE=SEPARATE_TRAINER_EXECUTION_AUTHORIZATION\nREVIEW_BUNDLE='+str(bundle)+'\nREVIEW_BUNDLE_SHA256='+a.file_sha(bundle),flush=True)
    return binding

def authorize_training(root:Path,binding_sha:str) -> dict:
    x=checked_request(root/'INITIALIZATION_REQUEST.json');receipt=a.obj(a.regular(root/'INITIALIZATION_RECEIPT.json').read_bytes())
    binding=compile_binding(x,receipt);a.need(binding_sha==binding['stage_binding_sha256'],'EXACT_TRAINING_BINDING_APPROVAL_REQUIRED')
    from round_training.contracts import load_stage_context,load_execution_authorization
    context=load_stage_context(root/'TRAINING_STAGE_BINDING.json');c=context.training_contract;attempt='train_'+binding_sha[:20]
    auth=tagged({'schema_id':'ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1','schema_version':1,'authorization_status':'APPROVED',
        'round_id':c['round_id'],'stage_id':'TRAINING_EXECUTION','profile_id':c['profile_id'],'stage_binding_sha256':binding_sha,
        'runner_freeze_root_sha256':x['runtime']['source_code_root_sha256'],'execution_attempt_id':attempt,
        'authorized_output_dir':str(root/'training_outputs'/attempt),'stage_attempt_root':str(root/'training_attempts'/attempt),
        'authorized_optimizer_steps':c['budget']['optimizer_steps'],'authorized_target_loss_tokens':c['budget']['target_loss_token_budget'],
        'diagnostic_only':c['diagnostic_only'],'promotion_eligible':c['promotion_eligible'],'training_execution_count_before':0},'authorization_sha256')
    p=root/'TRAINING_AUTHORIZATION.json'
    if not p.exists():
        # Preserve the generic runner's output-path freshness and identity gate.
        temp=root/'TRAINING_AUTHORIZATION.check.json';put(temp,auth)
        load_execution_authorization(temp,context=context,runner_freeze_root_sha256=x['runtime']['source_code_root_sha256'])
    put(p,auth);return auth

def train(path:Path) -> None:
    x=checked_request(path);root=Path(x['output_root']);receipt=a.obj(a.regular(root/'INITIALIZATION_RECEIPT.json').read_bytes())
    data=load_source(x['request']);a.verify_seed_zero_receipt(receipt,data['plan'],x['runtime'])
    a.need(versions()==receipt['software_versions'],'SOFTWARE_DIFFERS_FROM_INITIALIZATION')
    auth=a.obj(a.regular(root/'TRAINING_AUTHORIZATION.json').read_bytes())
    if (root/'TRAINING_RESULT.json').exists():print('EXISTING_TRAINING_RESULT_REUSED=true');return
    a.verify_clean_base(x['runtime']['base_binding'])
    from round_training.stage_runner import run_training_stage
    print('PHASE=ORIGINAL_GENERIC_TRAINING_STAGE',flush=True)
    result=run_training_stage(binding_path=root/'TRAINING_STAGE_BINDING.json',authorization_path=root/'TRAINING_AUTHORIZATION.json',runner_freeze_root_sha256=x['runtime']['source_code_root_sha256'])
    manifest=result['run_manifest'];a.need(manifest['optimizer_step_count']==data['contract']['budget']['optimizer_steps'],'ACTUAL_STEP_COUNT')
    a.need(manifest['target_loss_token_count']==data['contract']['budget']['target_loss_token_budget'],'ACTUAL_LOSS_TOKEN_COUNT')
    put(root/'TRAINING_RESULT.json',result)
    put(root/'CANDIDATE_HANDOFF.json',{'schema_id':'CLEAN_DIAGNOSTIC_CANDIDATE_HANDOFF_V1','candidate_alias':data['plan']['policy_training_recipe']['candidate_policy_alias'],
        'adapter_path':str(Path(auth['authorized_output_dir'])/'adapter'),'formal_run_manifest_path':str(Path(auth['authorized_output_dir'])/'formal_run_manifest.json'),
        'run_manifest':manifest,'training_plan_sha256':data['plan']['training_plan_sha256'],'interface_profile_id':'I1_EXECUTION_PROFILE_V1',
        'promotion_eligible':False,'archive_provenance_complete':False,'evaluation_executed':False,'lifecycle_advanced':False,
        'next_gate':'EXISTING_TRAIN_SELECT_I1_RAW_OFF_OFF_EVALUATION'})
    bundle=review_bundle(root,'TRAINING_REVIEW.zip')
    print('TRAINING_COMPLETED=true\nCORE_REPOSITORY_MODIFIED=false\nPROMOTION_PERFORMED=false\nNEXT_GATE=EXISTING_TRAIN_SELECT_I1_RAW_OFF_OFF_EVALUATION\nREVIEW_BUNDLE='+str(bundle),flush=True)

def worker_environment(source:dict) -> dict:
    e=dict(source)
    for k in list(e):
        if k in {'OUTPUT_ROOT','REPRO_ROOT','SOURCE_ADAPTER_ROOT','NATIVE_ROOT','MAINLINE_ROOT','PREFLIGHT_ROOT','REVIEW_ROOT','PYTHONPATH'} or any(t in k.upper() for t in ('API_KEY','ACCESS_TOKEN','HF_TOKEN','HUGGING_FACE_HUB_TOKEN','SECRET')):e.pop(k,None)
    e.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',WANDB_DISABLED='true')
    return e

def job_script(script:Path,request:Path,phase:str,python=None) -> str:
    py=python or '/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python'
    return '#!/bin/bash\nexec '+shlex.join([py,'-B',str(script),'--worker',phase,'--prepared-request',str(request)])+'\n'

def sbatch_args(script:Path,log:Path,resources:dict) -> list[str]:
    return ['sbatch','--parsable','--partition='+resources['partition'],'--gpus=1','--time='+resources['time'],'--no-requeue',
            '--job-name=clean_lora_init_train','--output='+str(log),'--error='+str(log),str(script)]

def invoke_sbatch(script:Path,log:Path,resources:dict) -> str:
    p=subprocess.run(sbatch_args(script,log,resources),env=worker_environment(os.environ),text=True,capture_output=True,timeout=60,check=False)
    a.need(p.returncode==0,'SBATCH_FAILED_RC_'+str(p.returncode))
    value=p.stdout.strip().split(';')[0];a.need(re.fullmatch(r'[0-9]+',value) is not None,'SBATCH_RESULT_AMBIGUOUS');return value

def submit_once(root:Path,phase:str,script:Path,resources:dict) -> dict:
    intent=root/(phase+'.SUBMIT_INTENT.json');receipt=root/(phase+'.SUBMIT_RECEIPT.json')
    if receipt.exists():
        x=json.loads(receipt.read_bytes());a.need(x['script_sha256']==a.file_sha(script) and x['resources']==resources,'SUBMIT_SCRIPT_OR_RESOURCE_CHANGED');print('EXISTING_JOB_REUSED='+x['job_id'],flush=True);return x
    a.need(not intent.exists(),'SUBMISSION_UNCONFIRMED_NO_AUTOMATIC_RETRY')
    payload={'phase':phase,'script_sha256':a.file_sha(script),'resources':resources}
    # Atomic create is the double-submission guard; do not remove on timeout.
    fd=os.open(intent,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:os.write(fd,a.cb(payload));os.fsync(fd)
    finally:os.close(fd)
    job=invoke_sbatch(script,root/(phase+'-%j.log'),resources)
    value={**payload,'job_id':job};put(receipt,value);print('SLURM_JOB_SUBMITTED='+job,flush=True);return value

def review_bundle(root:Path,name:str) -> Path:
    # No model weights or credentials are copied into the review.
    files={}
    for p in root.rglob('*'):
        if not p.is_file() or p.is_symlink() or p.suffix not in {'.json','.jsonl','.log'}:continue
        if 'seed_zero_adapter' in p.parts or 'adapter' in p.parts:continue
        if p.stat().st_size>4_000_000:continue
        files[str(p.relative_to(root))]=p.read_bytes()
    dest=root/name
    # Each phase can re-export its current evidence; use a digest-specific file
    # when an existing bundle would differ. Never overwrite old evidence.
    if dest.exists():
        with zipfile.ZipFile(dest) as z:old={n:z.read(n) for n in z.namelist()}
        if old==files:return dest
        dest=root/(Path(name).stem+'_'+a.sha(a.cb({n:a.sha(r) for n,r in files.items()}))[:12]+'.zip')
        if dest.exists():return dest
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,raw in sorted(files.items()):
            info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
    return dest

def show(root:Path):
    print('RUN_ROOT='+str(root))
    for phase in ('smoke','training'):
        p=root/(phase+'.SUBMIT_RECEIPT.json')
        if p.exists():
            r=json.loads(p.read_bytes());print(phase+'_JOB_ID='+r['job_id'])
            cmd=['squeue','-h','-j',r['job_id'],'-o','%i %T %M %N']
            try:
                q=subprocess.run(cmd,text=True,capture_output=True,check=False,timeout=20);print(q.stdout)
            except (OSError,subprocess.TimeoutExpired) as exc:print('STATUS_QUERY_UNAVAILABLE='+type(exc).__name__)
            log=root/(phase+'-'+r['job_id']+'.log')
            if log.exists():print('\n'.join(log.read_text(errors='replace').splitlines()[-25:]))
    for name in ('INITIALIZATION_RECEIPT.json','NEXT_STAGE_BINDING.json','CANDIDATE_HANDOFF.json'):
        p=root/name
        if p.exists():print(name+'='+p.read_text())

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--request',type=Path,default=HERE/'current_request.json')
    ap.add_argument('--submit-smoke',action='store_true');ap.add_argument('--submit-training',action='store_true');ap.add_argument('--approve-binding');ap.add_argument('--status',action='store_true')
    ap.add_argument('--worker',choices=['smoke','training']);ap.add_argument('--prepared-request',type=Path)
    args=ap.parse_args()
    if args.worker:
        a.need(args.prepared_request is not None,'PREPARED_REQUEST_REQUIRED')
        x=checked_request(args.prepared_request);root=Path(x['output_root'])
        try:(smoke if args.worker=='smoke' else train)(args.prepared_request)
        except BaseException as exc:
            record={'schema_id':'CLEAN_TRAINING_PHASE_STOP_V1','phase':args.worker,'error_type':type(exc).__name__,'message':str(exc),
                    'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'automatic_retry_authorized':False,'training_success_claimed':False}
            put(root/(args.worker+'.STOP.json'),record);b=review_bundle(root,args.worker.upper()+'_STOP_REVIEW.zip');print('REVIEW_BUNDLE='+str(b),flush=True);raise
        return 0
    a.need(not(args.submit_smoke and args.submit_training),'SEPARATE_SMOKE_AND_TRAINING_COMMANDS_REQUIRED')
    request=json.loads(args.request.read_bytes());root=prepare(request)
    if args.status:show(root);return 0
    if args.submit_smoke:
        x=json.loads((root/'INITIALIZATION_REQUEST.json').read_bytes())
        if (root/'INITIALIZATION_RECEIPT.json').exists():compile_binding(x,a.obj((root/'INITIALIZATION_RECEIPT.json').read_bytes()));return 0
        put(root/'SMOKE_AUTHORIZATION.json',{'authorization_scope':'INITIALIZATION_ONLY_NO_OPTIMIZER','request_sha256':x['request_sha256'],'training_authorized':False})
        script=root/'smoke.sbatch';write_once(script,job_script(HERE/'run_stage.py',root/'INITIALIZATION_REQUEST.json','smoke',request['python']).encode())
        submit_once(root,'smoke',script,request['slurm']);print('NEXT_GATE=CLEAN_INITIALIZATION_SMOKE\nTRAINING_AUTHORIZED=false',flush=True)
    elif args.submit_training:
        a.need(bool(args.approve_binding),'EXACT_BINDING_APPROVAL_REQUIRED');authorize_training(root,args.approve_binding)
        script=root/'training.sbatch';write_once(script,job_script(HERE/'run_stage.py',root/'INITIALIZATION_REQUEST.json','training',request['python']).encode())
        submit_once(root,'training',script,request['slurm']);print('NEXT_GATE=EXISTING_GENERIC_TRAINING_STAGE_EXECUTION',flush=True)
    else:print('NEXT_GATE=EXPLICIT_INITIALIZATION_SMOKE_AUTHORIZATION',flush=True)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError,RuntimeError) as exc:print('STOP='+type(exc).__name__+':'+str(exc),flush=True);raise SystemExit(21)
