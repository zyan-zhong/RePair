#!/usr/bin/env python3
"""Reuse frozen POST and renderer code to prepare a diagnostic training review.

This is a preparation-only adapter. It does not adjudicate unseen scientific
opinions, approve an arm, change labels, create weights, or submit a job.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, os, stat, subprocess, sys, tempfile, zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
TP=Path('scripts/engineering_snapshots/training_pipeline')
RENDERER=TP/'qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_preflight_v1_7_2/tools'
TRAINER=TP/'round_generic_training_stage_v2_1_hardening_build'
REPO=Path(os.environ.get('PCHSI_TEST_REPO','/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-stage3u-planner-derived-budget-v1'))

def need(ok: bool, message: str) -> None:
    if not ok: raise ValueError(message)

def sha(raw: bytes) -> str:return hashlib.sha256(raw).hexdigest()

def cb(value: Any) -> bytes:
    from pchsi.reference_loop.canonical import canonical_json_bytes
    return canonical_json_bytes(value)

def obj(raw: bytes) -> dict:
    from pchsi.reference_loop.canonical import strict_json_loads
    value=strict_json_loads(raw);need(isinstance(value,dict),'OBJECT_REQUIRED');return value

def regular(path: Path) -> bytes:
    need(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'NON_SYMLINK_FILE_REQUIRED:'+str(path))
    return path.read_bytes()

def load_zip(path: Path, expected: str) -> dict[str,bytes]:
    raw=regular(path);need(sha(raw)==expected,'INPUT_ARCHIVE_HASH_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        items=z.infolist(); names=[i.filename for i in items]
        need(len(names)==len(set(names)),'DUPLICATE_ZIP_MEMBERS')
        need(sum(i.file_size for i in items)<=100_000_000,'ZIP_SIZE_LIMIT')
        out={}
        for i in items:
            p=Path(i.filename)
            need(not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename,'INVALID_ARCHIVE_PATH')
            need(stat.S_IFMT(i.external_attr>>16)!=stat.S_IFLNK,'ZIP_SYMLINK_FORBIDDEN')
            if not i.is_dir():out[i.filename]=z.read(i)
        return out

def module_from(path: Path,name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec is not None and spec.loader is not None,'MODULE_SPEC_FAILED')
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod
    spec.loader.exec_module(mod);return mod

def renderer_module():
    # Keep the original renderer and its original common module byte-for-byte.
    old=sys.modules.pop('common',None)
    try:
        module_from(REPO/RENDERER/'common.py','common')
        return module_from(REPO/RENDERER/'renderer_adapter_core.py','_reused_t2_renderer')
    finally:
        sys.modules.pop('common',None)
        if old is not None:sys.modules['common']=old

def verify_repository(repo: Path,head: str) -> None:
    r=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],capture_output=True,check=True)
    need(r.stdout.strip().decode()==head,'FIXED_HEAD_MISMATCH')
    rows=subprocess.run(['git','-C',str(repo),'ls-tree','-r','-z',head],capture_output=True,check=True).stdout
    for row in rows.split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.split()
        need(kind==b'blob' and mode in (b'100644',b'100755'),'UNSUPPORTED_TREE_ENTRY')
        raw=regular(repo/os.fsdecode(name))
        need(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid.decode(),'FIXED_FILE_CHANGED:'+os.fsdecode(name))

def materialize_source_previews(files: dict[str,bytes]) -> dict:
    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.research_intelligence.clean_f0f1_manifest import build_clean_f0f1_branch_bindings
    from pchsi.research_intelligence.human_f0f1_runtime import build_branch_evidence_hash_v1,validate_candidate_content_hash_v1,validate_executable_exact_candidate_v1
    from pchsi.memory.source_state_contracts import RegisteredReplaySourceV1
    from pchsi.evaluation.policy_call_evidence import PolicyCallEvidenceV1
    from pchsi.evaluation.raw_policy_prompt import build_raw_policy_prompt,ExecutedTransition,InterfaceFeedbackCode
    m=obj(files['inputs/execution_manifest.json']);bindings=build_clean_f0f1_branch_bindings(m)
    result=obj(files['aggregation/CLEAN_REFERENCE_F0F1_RESULT_PACKAGE_V1.json'])
    need(domain_hash(result['schema_id'],result,excluded_field='result_package_sha256')==result['result_package_sha256'],'RESULT_HASH_MISMATCH')
    need(result['execution_manifest_sha256']==m['execution_manifest_sha256'] and result['incomplete_pair_count']==0,'RESULT_IDENTITY_OR_COMPLETENESS')
    groups=defaultdict(list)
    for b in bindings:
        if b['branch']=='F0':groups[b['source_state_sha256']].append(b)
    need(len(groups)==m['state_count'],'STATE_COUNT_MISMATCH')
    state_results={}
    for n,raw in files.items():
        if n.startswith('aggregation/states/') and n.endswith('.json'):
            s=obj(raw);need(domain_hash(s['schema_id'],s,excluded_field='state_result_sha256')==s['state_result_sha256'],'STATE_RESULT_HASH')
            need(s['state_result_sha256'] in result['state_result_sha256s'],'UNBOUND_STATE_RESULT')
            need(s['source_state_sha256'] not in state_results,'DUPLICATE_STATE_RESULT')
            state_results[s['source_state_sha256']]=s
    rcore=renderer_module();semantics=[];adapters=[];tokens={};proofs=[];runtimes={};calls_checked=0
    for state,rows in sorted(groups.items(),key=lambda kv:kv[1][0]['state_position']):
        need(sorted(b['continuation_seed'] for b in rows)==sorted(m['seed_schedule']),'REPLICATE_SET_MISMATCH')
        b=rows[0]
        candidate_raw=files['frozen_sources/candidates/'+b['candidate_artifact_file_sha256']+'.json']
        source_raw=files['frozen_sources/replays/'+b['replay_source_file_sha256']+'.json']
        need(sha(candidate_raw)==b['candidate_artifact_file_sha256'] and sha(source_raw)==b['replay_source_file_sha256'],'FROZEN_SOURCE_BYTES_CHANGED')
        source=RegisteredReplaySourceV1.from_json(source_raw)
        need(source.expected_source_fingerprint.fingerprint_sha256==state,'SOURCE_FINGERPRINT_MISMATCH')
        # Split access needs its original authority at admission; a path is not that authority.
        need(source.source_policy_condition==m['policy_version']+'::I1_EXECUTION_PROFILE_V1','NOT_BOUND_I1_SOURCE')
        candidate=obj(candidate_raw)
        validate_candidate_content_hash_v1(candidate,expected_candidate_sha256=b['source_candidate_sha256'])
        sr=state_results[state]
        need(sr['source_candidate_sha256']==b['source_candidate_sha256'] and sr['registered_repair_action']==b['registered_repair_action'],'STATE_CANDIDATE_MISMATCH')
        need(sr['stable_effect'] in ('NEUTRAL','UNCERTAIN'),'EXISTING_DIAGNOSTIC_RENDERER_LABEL_SCOPE_MISMATCH')
        contexts=[];refs=[]
        for pair_binding in rows:
            key='branches/'+pair_binding['pair_id']+'/F0/CLEAN_REFERENCE_F0F1_BRANCH_EVIDENCE_V1.json'
            rec=obj(files[key]);need(rec['branch_evidence_sha256']==build_branch_evidence_hash_v1(rec),'BRANCH_EVIDENCE_HASH_MISMATCH')
            need(rec['branch_binding_sha256']==pair_binding['branch_binding_sha256'] and rec['evidence_complete'] is True,'BRANCH_BINDING_MISMATCH')
            need(bool(rec['policy_calls']),'NO_SOURCE_F0_CALL')
            e=PolicyCallEvidenceV1.from_dict(rec['policy_calls'][0]['policy_call'])
            history=tuple(ExecutedTransition(a,o) for a,o in e.executed_history)
            prompt=build_raw_policy_prompt(public_task_goal=e.public_task_goal,observation=e.observation,
                executed_transitions=history,admissible_commands=e.admissible_commands,
                interface_feedback=None if e.interface_feedback_before is None else InterfaceFeedbackCode(e.interface_feedback_before))
            need(prompt==e.prompt_text and sha(prompt.encode())==source.base_policy_input_sha256,'EXACT_SOURCE_RAW_PROMPT_MISMATCH')
            need(e.model_call_index==source.model_call_index,'NOT_FIRST_SOURCE_CALL')
            action=validate_executable_exact_candidate_v1(candidate,expected_candidate_sha256=b['source_candidate_sha256'],expected_source_state_sha256=state,live_commands=e.admissible_commands)
            need(action==b['registered_repair_action'],'REPAIR_TARGET_CHANGED')
            contexts.append((prompt,tuple(e.admissible_commands),tuple(e.rendered_prompt_token_ids)))
            refs.append({'pair_id':pair_binding['pair_id'],'continuation_seed':pair_binding['continuation_seed'],'branch_evidence_sha256':rec['branch_evidence_sha256'],'source_prompt_sha256':e.prompt_sha256})
            calls_checked+=1
        need(all(c==contexts[0] for c in contexts),'REPLICATE_SOURCE_CONTEXT_DIFFERS')
        prompt,menu,ids=contexts[0]; tokens[state]=list(ids)
        value={'schema_id':'POLICY_SEMANTIC_TRAINING_ROW_V1','schema_version':1,
            'round_id':m['round_id'],'arm_id':'T2','source_state_sha256':state,
            'source_candidate_sha256':b['source_candidate_sha256'],'terminal_effect':sr['stable_effect'],
            'target_action':b['registered_repair_action'],
            'policy_visible_context':{'source_prompt_text':prompt,'source_prompt_bound':True,'admissible_commands':list(menu)},
            'diagnostic_only':True,'verified_positive':False,'promotion_eligible':False,
            'preview_only':True,'training_authorized':False}
        value['row_sha256']=domain_hash(value['schema_id'],value,excluded_field='row_sha256')
        adapter=rcore.build_t2_source_adapter_row(value,len(semantics))
        semantics.append(value);adapters.append(adapter)
        proofs.append({'source_state_sha256':state,'source_task_id':source.source_task_id,
            'source_gamefile_sha256':source.source_gamefile_sha256,'exact_gamefile':source.exact_gamefile,
            'candidate_file_sha256':b['candidate_artifact_file_sha256'],'replay_file_sha256':b['replay_source_file_sha256'],
            'state_result_sha256':sr['state_result_sha256'],'all_replicates':refs,
            'access_authorization_claimed':False})
        rh=b['runtime_binding_file_sha256']; rr=files['prepared_binding/runtime/'+rh+'.json']
        need(sha(rr)==rh,'RUNTIME_HASH_MISMATCH');runtimes[rh]=obj(rr)
    need(len(runtimes)==1,'RUNTIME_VARIATION')
    runtime=next(iter(runtimes.values()))
    need(runtime['continuation_request_contract']['profile_id']=='I1_EXECUTION_PROFILE_V1','I1_REQUIRED')
    return {'semantics':semantics,'renderer_sources':adapters,'source_prompt_tokens':tokens,'source_proofs':proofs,
        'manifest':m,'result':result,'runtime':runtime,
        'counts':{'unique_source_states':len(semantics),'repeated_f0_contexts_checked':calls_checked,
                  'state_repetition_used_as_extra_training_row':False,'preview_only':True}}

def inspect_registered_post(files: dict[str,bytes],post_module,prepared: dict) -> dict:
    human=obj(files['human/HUMAN_RESEARCHER_POST_V1.json'])
    draft=obj(files['HUMAN_POST_DRAFT.json']);need(human==draft,'HUMAN_POST_DIFFERENT_FROM_FROZEN_DRAFT')
    need(post_module.finalize_human_post(human)==human,'HUMAN_POST_HASH')
    approval=obj(files['HUMAN_APPROVAL.json']);need(approval['approved_post_record_sha256']==human['post_record_sha256'],'HUMAN_APPROVAL')
    intent=obj(files['SHADOW_CALL_INTENT.json']);receipt=obj(files['SHADOW_CALL_RECEIPT.json'])
    need(receipt['intent_sha256']==sha(cb(intent)),'SHADOW_INTENT_BINDING')
    response=receipt['result'];need(response['status']=='ACCEPTED','SHADOW_NOT_ACCEPTED')
    dirname=Path(response['call_dir']).name
    need(dirname not in ('','.','..'),'INVALID_CALL_DIR')
    shadow=obj(files['strong_calls/'+dirname+'/validated_artifact.json'])
    docs={'HUMAN_POST_DRAFT.json':draft,'POST_FACTS.json':obj(files['POST_FACTS.json'])}
    post_module.validate_shadow(shadow,docs)
    need(docs['POST_FACTS.json']['execution_manifest_sha256']==prepared['manifest']['execution_manifest_sha256'],'POST_EXECUTION_BINDING')
    need(docs['POST_FACTS.json']['result_package_sha256']==prepared['result']['result_package_sha256'],'POST_RESULT_BINDING')
    comparison=post_module.compare_posts(human,shadow)
    need(comparison==obj(files['POST_FIELD_COMPARISON.json']),'POST_COMPARISON_CHANGED')
    return {'human':human,'shadow':shadow,'comparison':comparison,'receipt':receipt,
            'field_adjudication_performed':False,'training_authorized':False}

def batch_proposal(count: int,epochs: int,accumulation: int,seed: int) -> dict:
    need(all(type(x) is int for x in (count,epochs,accumulation,seed)),'INTEGER_BUDGET_REQUIRED')
    need(count>0 and epochs>0 and accumulation>0 and seed>=0,'INVALID_BUDGET')
    need(count%accumulation==0,'ROWS_NOT_DIVISIBLE_NO_SILENT_PADDING')
    return {'training_seed':seed,'data_seed':seed,'epochs':epochs,'micro_batch_size':1,
            'gradient_accumulation_steps':accumulation,'effective_batch_size':accumulation,
            'optimizer_steps':count//accumulation*epochs,'partial_final_accumulation_group':False,
            'drop_last':False,'sample_padding_allowed':False,'approval_status':'PROPOSED_NOT_AUTHORIZED'}

def tokenize_preview(prepared: dict) -> tuple[list[dict],dict]:
    from transformers import AutoTokenizer
    rt=prepared['runtime']
    tokenizer=AutoTokenizer.from_pretrained(rt['base_model_local_path'],revision=rt['tokenizer_revision'],
        local_files_only=True,trust_remote_code=False)
    template=tokenizer.chat_template
    need(isinstance(template,str) and sha(template.encode())==rt['chat_template_sha256'],'TOKENIZER_CHAT_TEMPLATE_MISMATCH')
    renderer=renderer_module();native=[]
    for i,a in enumerate(prepared['renderer_sources']):
        messages=renderer.make_messages(a['input']['prompt_text'],a['target']['action_json'])
        prompt_ids=tokenizer.apply_chat_template(messages[:-1],tokenize=True,add_generation_prompt=True,continue_final_message=False)
        full=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=False)
        need(prompt_ids==prepared['source_prompt_tokens'][a['source_state_sha256']],'TOKENIZED_PROMPT_DIFFERS_FROM_LIVE_EVIDENCE')
        labels=renderer.mask_prompt_prefix(full,prompt_ids)
        need(len(full)<=rt['context_window_tokens'],'NO_TRUNCATION_CONTEXT_EXCEEDED')
        native.append(renderer.build_native_row(adapter_row=a,input_ids=full,labels=labels,ordinal=i))
    return native,{'local_tokenizer_only':True,'new_model_loaded':False,'sample_count':len(native),
        'sequence_lengths':[r['tokenization']['sequence_token_count'] for r in native],
        'one_pass_target_loss_token_count':sum(r['tokenization']['completion_loss_token_count'] for r in native),
        'prompt_token_ids_equal_live_evidence':True,'truncation':False,'training_authorized':False}

def collect_frozen_engineering_sources(template: dict) -> tuple[dict,dict[str,bytes]]:
    parent=template['parent'];p=Path(parent['formal_train_path'])
    record={'code_path':str(p),'expected_sha256':parent['formal_train_sha256'],
        'purpose':'REUSE_TRAINING_IMPLEMENTATION_ONLY_NOT_OLD_DATA_OR_WEIGHTS','available':False}
    if not p.exists():return record,{}
    raw=regular(p);need(sha(raw)==parent['formal_train_sha256'],'FROZEN_TRAINER_IMPLEMENTATION_CHANGED')
    record['available']=True
    return record,{'engineering_sources/formal_train.py':raw}

def publish(out: Path,files: dict[str,bytes]) -> Path:
    need(not out.is_symlink(),'OUTPUT_SYMLINK')
    if out.exists():
        for n,b in files.items():need(regular(out/n)==b,'EXISTING_OUTPUT_CHANGED:'+n)
    else:
        out.parent.mkdir(parents=True,exist_ok=True)
        tmp=Path(tempfile.mkdtemp(prefix='.prepare_',dir=out.parent))
        for n,b in files.items():
            p=tmp/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        os.rename(tmp,out)
    zip_path=out/'TRAINING_PREPARATION_REVIEW.zip'
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as z:need({n:z.read(n) for n in z.namelist()}==files,'EXISTING_REVIEW_CHANGED')
    else:
        temp=out/'.review.tmp'
        with zipfile.ZipFile(temp,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for n,b in sorted(files.items()):
                info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
        os.replace(temp,zip_path)
    return zip_path

def main(argv=None) -> int:
    global REPO
    ap=argparse.ArgumentParser();ap.add_argument('--config',default=str(HERE/'current_round.json'))
    a=ap.parse_args(argv);cfg=json.loads(Path(a.config).read_text());REPO=Path(cfg['repo'])
    sys.path.insert(0,str(REPO/'src'));verify_repository(REPO,cfg['fixed_head'])
    print('PHASE=REUSE_FIXED_CODE_AND_ACCEPTED_POST_NO_CALLS',flush=True)
    stage=Path(cfg['existing_post_package'])
    for rel,expected in cfg['existing_post_code_sha256'].items():need(sha(regular(stage/rel))==expected,'EXISTING_POST_CODE_CHANGED:'+rel)
    post_module=module_from(stage/'post_round.py','_reused_registered_post')
    files=load_zip(Path(cfg['f0f1_review']),cfg['f0f1_review_sha256'])
    data=materialize_source_previews(files)
    post_files=load_zip(Path(cfg['registered_post_review']),cfg['registered_post_review_sha256'])
    inspected=inspect_registered_post(post_files,post_module,data)
    print('ACCEPTED_STRONG_POST_READ=true',flush=True)
    print('STRONG_HYPOTHESIS_STATUS='+inspected['shadow']['hypothesis_status'],flush=True)
    print('STRONG_TRAINING_RECOMMENDATION='+json.dumps(inspected['shadow']['researcher_training_recommendation'],ensure_ascii=False),flush=True)
    template=obj(regular(REPO/TRAINER/'profiles/human_reference_t2/ROUND_LOCAL_TRAINING_CONTRACT_V1.json'))
    count=len(data['semantics']);proposal=cfg['diagnostic_proposal']
    budget=batch_proposal(count,proposal['epochs'],proposal['gradient_accumulation_steps'],proposal['training_seed'])
    output={
        'HUMAN_POST.json':cb(inspected['human']), 'STRONG_POST.json':cb(inspected['shadow']),
        'POST_FIELD_COMPARISON.json':cb(inspected['comparison']),
        'POST_CALL_RECEIPT.json':cb(inspected['receipt']),
        'T2_SEMANTIC_ROWS.preview.jsonl':b''.join(cb(r)+b'\n' for r in data['semantics']),
        'T2_RENDERER_SOURCE.preview.jsonl':b''.join(cb(r)+b'\n' for r in data['renderer_sources']),
        'T2_SOURCE_PROOFS.json':cb(data['source_proofs']),
        'INHERITED_TRAINING_API.json':cb(obj(regular(REPO/'docs/stage1/STAGE1_ACTUAL_RUNNER_PORT_ADJUDICATION_V1.json'))),
    }
    # Do not hide proposal/adapter blockers behind a successful tokenizer run.
    blockers=['POST_FIELD_ADJUDICATION_NOT_FROZEN', 'SEPARATE_T2_DIAGNOSTIC_PLAN_NOT_AUTHORIZED',
        'CLEAN_BASE_MODEL_INITIALIZATION_PROFILE_NOT_BOUND', 'TRAIN_UPDATE_ACCESS_AND_SELECT_SPLIT_BINDING_REQUIRED']
    token_info={'status':'NOT_STARTED'}
    try:
        print('PHASE=EXISTING_RENDERER_LOCAL_TOKENIZATION_NO_WEIGHTS',flush=True)
        native,token_info=tokenize_preview(data)
        output['T2_TRAINER_NATIVE.preview.jsonl']=b''.join(cb(r)+b'\n' for r in native)
        budget['target_loss_token_budget']=token_info['one_pass_target_loss_token_count']*budget['epochs']
    except (ImportError,ValueError,OSError,TypeError) as exc:
        token_info={'status':'BLOCKED','error_type':type(exc).__name__,'error':str(exc)}
        blockers.append('EXACT_TOKENIZER_PREFLIGHT_BLOCKED')
    capture,sources=collect_frozen_engineering_sources(template);output.update(sources)
    if not capture['available']:blockers.append('FROZEN_TRAINING_IMPLEMENTATION_NOT_LOCATED')
    proposal_doc={'schema_id':'TRAINING_PREPARATION_PROPOSAL_V1','status':'DRAFT_NOT_FROZEN_NOT_AUTHORIZED',
        'round_id':data['manifest']['round_id'],'parent_policy_id':data['manifest']['policy_version'],
        'candidate_policy_alias':'PI1_HUMAN_T2_DIAGNOSTIC_CANDIDATE','proposed_arm_ids':['T0','T2'],
        'source_scope':'ALL_REGISTERED_UNIQUE_SOURCE_STATE_ACTIONS_NO_EFFECT_BASED_RESELECTION',
        'scope_note':'Diagnostic selected-portfolio control, not the full Analyzer T2 universe or verified improvement.',
        'dataset_count':count,'source_counts':data['counts'],'budget':budget,
        'optimization_reference':template['optimization'],'peft_architecture_reference':template['peft'],
        'parent_model_binding':data['runtime'],
        'parent_initialization_requirement':'CLEAN_PI0_PLUS_NEW_SEEDED_LORA_NOT_PILOT_ADAPTER',
        'existing_generic_trainer_entrypoint':'round_training.stage_runner.run_training_stage',
        'existing_renderer_functions':['build_t2_source_adapter_row','make_messages','mask_prompt_prefix','build_native_row'],
        'old_wrapper_row_count':template['dataset']['row_count'],
        'old_wrapper_effective_batch':template['budget']['effective_batch_size'],
        'old_batch_supports_new_row_count':count%template['budget']['effective_batch_size']==0,
        'tokenizer_preflight':token_info,'training_implementation_capture':capture,
        'blockers':blockers,'diagnostic_only':True,'verified_positive':False,'promotion_eligible':False,
        'training_authorized':False,'adjudication_performed':False,'checkpoint_created':False,
        'original_human_post_preserved':True,'original_labels_preserved':True,
        'upstream_hashes':{'human_post':inspected['human']['post_record_sha256'],'strong_post':inspected['shadow']['shadow_record_sha256'],
                          'f0f1_result':data['result']['result_package_sha256']}}
    output['TRAINING_PLAN_PROPOSAL.json']=cb(proposal_doc)
    output['TOKENIZER_PREFLIGHT.json']=cb(token_info)
    output['PREPARATION_STATUS.json']=cb({'mechanical_previews_ready':True,'training_authorized':False,
        'core_repository_modified':False,'model_or_environment_called':False,'tokenizer_only':True,
        'training_executed':False,'next_gate':'POST_ADJUDICATION_AND_CLEAN_TRAINING_PLAN_APPROVAL','blockers':blockers})
    # Use the existing artifact-index schema rather than introduce another data plane.
    sys.path.insert(0,str(REPO/TRAINER))
    from round_training.receipts import build_input_artifact_index
    refs=[]
    for name,p,h in [('F0F1',Path(cfg['f0f1_review']),cfg['f0f1_review_sha256']),('REGISTERED_POST',Path(cfg['registered_post_review']),cfg['registered_post_review_sha256'])]:
        refs.append({'logical_name':name,'retention_class':'VALIDATED_SCIENTIFIC_ARTIFACT','path':str(p),'sha256':h,'size_bytes':p.stat().st_size,'schema_id':None})
    output['INPUT_ARTIFACT_INDEX.json']=cb(build_input_artifact_index(round_id=data['manifest']['round_id'],stage_id='TRAINING_PREPARATION_REVIEW',refs=refs))
    ident=sha(cb({n:sha(b) for n,b in output.items()}));root=Path(cfg['output_root'])/ident
    bundle=publish(root,output)
    print('SOURCE_PREVIEW_COUNT='+str(count));print('EXISTING_RENDERER_REUSED=true')
    print('HUMAN_POST_AND_STRONG_RESPONSE_UNCHANGED=true');print('TRAINING_AUTHORIZED=false')
    print('TRAINING_EXECUTION=false');print('CORE_REPOSITORY_MODIFIED=false')
    print('NEXT_GATE=POST_ADJUDICATION_AND_CLEAN_TRAINING_PLAN_APPROVAL')
    print('REVIEW_BUNDLE='+str(bundle));print('REVIEW_BUNDLE_SHA256='+sha(regular(bundle)))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print('STOP='+type(exc).__name__+':'+str(exc),file=sys.stderr);raise SystemExit(21)
