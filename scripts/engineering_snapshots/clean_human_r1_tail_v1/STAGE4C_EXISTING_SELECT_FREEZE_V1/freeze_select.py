"""Consume an existing SELECT preflight. No evaluator, trainer or model transport.

The approved protocol is separate from scientific execution permission. The
existing four-file I1 overlay is verified, regression-tested and committed,
never reapplied. All prior artifacts remain immutable.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import zipfile
from typing import Any


def need(ok: bool, reason: str) -> None:
    if not ok: raise ValueError(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def cb(value: object) -> bytes:
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes
    return canonical_json_bytes(value)


def domain_hash(domain: str, value: dict, field: str) -> str:
    from pchsi.reference_loop.canonical import domain_hash as original_domain_hash
    return original_domain_hash(domain, value, excluded_field=field)


def obj(raw: bytes) -> dict:
    from pchsi.evaluation.canonical_evidence import strict_json_loads
    value=strict_json_loads(raw)
    need(isinstance(value,dict),'JSON_OBJECT_REQUIRED');return value


def regular(path: Path) -> Path:
    path=Path(path)
    need(not any(x.is_symlink() for x in (path,*path.parents)),'SYMLINK:'+str(path))
    need(path.is_file(),'REGULAR_FILE_REQUIRED:'+str(path));return path


def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with regular(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def write_once(path: Path, raw: bytes) -> None:
    path=Path(path);need(not any(x.is_symlink() for x in (path,*path.parents)),'SYMLINK:'+str(path))
    if path.exists():need(regular(path).read_bytes()==raw,'OUTPUT_CONFLICT:'+str(path));return
    path.parent.mkdir(parents=True,exist_ok=True)
    # Atomic create-only publication: no partially written authority record.
    fd,name=tempfile.mkstemp(prefix='.writing-',dir=path.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        try:os.link(temp,path)
        except FileExistsError:need(regular(path).read_bytes()==raw,'OUTPUT_CONFLICT:'+str(path))
    finally:temp.unlink(missing_ok=True)


def command(args: list[str], cwd: Path, *, env: dict | None=None, check: bool=True) -> subprocess.CompletedProcess:
    p=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if check:need(p.returncode==0,'COMMAND_FAILED:'+repr(args)+'\n'+p.stdout.decode(errors='replace'))
    return p


def git(repo: Path,*args: str) -> bytes:
    return command(['git',*args],repo).stdout


def read_review(path: Path, expected_sha: str) -> dict[str,bytes]:
    need(file_sha(path)==expected_sha,'SOURCE_REVIEW_SHA_MISMATCH')
    files={}
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None,'ARCHIVE_CRC')
        for i in z.infolist():
            p=PurePosixPath(i.filename)
            need(not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename and not stat.S_ISLNK(i.external_attr>>16),'ARCHIVE_PATH')
            if i.is_dir():continue
            need(i.filename not in files,'ARCHIVE_DUPLICATE_MEMBER')
            files[i.filename]=z.read(i)
    index=obj(files['FILES.sha256.json'])
    need(set(index)==set(files)-{'FILES.sha256.json'},'ARCHIVE_INDEX_SET')
    for n,h in index.items():need(sha(files[n])==h,'ARCHIVE_MEMBER_HASH:'+n)
    return files


def validate_grid(g: dict) -> dict:
    rows=g['index_crosswalk'];seeds=g['replicate_seeds']
    need(isinstance(rows,list) and rows and isinstance(seeds,list) and seeds,'GRID_EMPTY')
    need(len(seeds)==len(set(seeds)) and all(type(s)is int and s>=0 for s in seeds),'GRID_SEEDS')
    need([r['select_local_index'] for r in rows]==list(range(len(rows))),'GRID_INDICES')
    need(len({r['source_index'] for r in rows})==len(rows) and len({r['task_id'] for r in rows})==len(rows),'GRID_DUPLICATE_TASK')
    expected=[{'task_id':r['task_id'],'select_local_index':r['select_local_index'],'source_index':r['source_index'],'seed':s} for s in seeds for r in rows]
    need(g['pairs']==expected,'GRID_PAIR_PRODUCT_OR_ORDER')
    need(g['task_count']==len(rows) and g['paired_cells']==len(expected) and g['condition_episodes']==2*len(expected),'GRID_COUNTS')
    need(g['primary_statistical_unit']=='unique_task','GRID_STATISTICAL_UNIT')
    need(g['select_detail_visibility']=='SELECT_SUMMARY_ONLY' and g['benchmark_feedback_forbidden'] is True,'GRID_ACCESS_BOUNDARY')
    for k in ('max_environment_steps','max_policy_attempts','max_consecutive_nonexecuted_attempts'):
        need(type(g['episode_budget'][k]) is int and g['episode_budget'][k]>0,'GRID_BUDGET:'+k)
    need(g['execution_authorized'] is False and g['protocol_frozen'] is False,'SOURCE_IS_NOT_UNEXECUTED_PROPOSAL')
    return g


def validate_review(files: dict[str,bytes]) -> dict:
    r=obj(files['SELECT_PREFLIGHT_RECEIPT.json']);g=validate_grid(obj(files['SELECT_GRID_PROPOSAL.json']))
    m=obj(files['MODEL_BINDING_PROPOSAL.json']);a=obj(files['TRAINING_EVIDENCE_AUDIT.json']);refs=obj(files['BOUND_POOL_REFERENCES.json']);scope=obj(files['PATCH_SCOPE.json'])
    for k in ('original_worktree_unchanged','candidate_files_verified','evaluation_tests_passed'):need(r[k] is True,'PREFLIGHT_NOT_PASSED:'+k)
    for k in ('protocol_frozen','live_driver_bound','model_environment_training_execution','promotion_eligible'):need(r[k] is False,'PREFLIGHT_SCOPE:'+k)
    need(m['candidate_adapter_bundle_sha256']==a['adapter_bundle_sha256']==a['candidate']['run_manifest']['adapter_bundle_sha256'],'CANDIDATE_ADAPTER_IDENTITY')
    need(m['candidate_adapter_path']==a['candidate']['adapter_path'] and m['candidate_alias']==a['candidate']['candidate_alias'],'CANDIDATE_PATH_OR_ALIAS')
    need(r['training_plan_sha256']==a['training_plan_sha256']==a['plan']['training_plan_sha256'],'TRAINING_PLAN_IDENTITY')
    need(r['training_receipt_sha256']==a['stage_receipt_sha256'],'TRAINING_RECEIPT_IDENTITY')
    need(r['training_review_sha256']==m['source_training_review_sha256'],'TRAINING_REVIEW_IDENTITY')
    need(m['parent_policy_id']==a['plan']['parent_policy_id'],'PARENT_IDENTITY')
    need(m['interface_contract']['profile_id']=='I1_EXECUTION_PROFILE_V1' and m['interface_contract']['request_kind']=='I1','I1_REQUIRED')
    need(sha(cb(m['interface_contract']))==m['policy_request_schema_sha256'],'I1_CONTRACT_HASH')
    need(m['memory']==m['harness']=='OFF' and m['dynamic_lora_updates'] is False and m['promotion_eligible'] is False,'MODEL_CONDITION_BOUNDARY')
    need(g['source_metadata_ref']==refs['TRAIN_SELECT'],'SELECT_METADATA_REFERENCE')
    need(refs['TRAIN_SELECT']['expected_count']==g['task_count']==r['task_count'],'SELECT_COUNTS')
    need(g['paired_cells']==r['paired_task_seed_cells'] and g['condition_episodes']==r['condition_episodes'],'PREFLIGHT_GRID_COUNTS')
    need(set(refs)=={'TRAIN_UPDATE','TRAIN_SELECT','TRAIN_AUDIT'},'POOL_SET')
    need({k:v['expected_count'] for k,v in refs.items()}==r['pool_counts'],'POOL_COUNTS')
    need(a['promotion_eligible'] is False and a['candidate']['evaluation_executed'] is False,'CANDIDATE_ALREADY_EVALUATED_OR_PROMOTABLE')
    return {'receipt':r,'grid':g,'model':m,'audit':a,'refs':refs,'scope':scope}


def approve_decision(raw: bytes, approval: str, source_sha: str, files: dict) -> dict:
    need(sha(raw)==approval,'DECISION_APPROVAL_MISMATCH')
    d=obj(raw);need(d['source_review_sha256']==source_sha,'DECISION_SOURCE')
    need(d['approval_scope']=='CODE_AND_PROTOCOL_ONLY_NOT_LIVE_EXECUTION','DECISION_APPROVAL_SCOPE')
    for n,h in d['approved_source_file_sha256s'].items():need(n in files and sha(files[n])==h,'DECISION_BOUND_FILE:'+n)
    need(set(d['approved_source_file_sha256s'])=={'PATCH_SCOPE.json','SELECT_I1_EXTENSION.patch','SELECT_GRID_PROPOSAL.json','MODEL_BINDING_PROPOSAL.json'},'DECISION_FILE_SET')
    return d


def make_protocol(data: dict,d: dict,source_sha: str,head: str,tree: str,code_sha: str) -> dict:
    g=validate_grid(data['grid']);m=data['model'];a=data['audit']
    need(d['interface_profile_id']==m['interface_contract']['profile_id']=='I1_EXECUTION_PROFILE_V1','DECISION_INTERFACE')
    need(d['task_selection']=='ALL_BOUND_POOL_IN_METADATA_ORDER' and d['reselection_allowed'] is False,'DECISION_RESELECTION')
    need(d['model_execution_authorized'] is False and d['promotion_eligible'] is False,'DECISION_EXECUTION_OR_PROMOTION')
    need(d['primary_statistical_unit']==g['primary_statistical_unit'],'DECISION_UNIT')
    measurement=d['measurement'];missing=d['missingness_policy']
    need(measurement['seed_replicates_are_not_independent_tasks'] is True and measurement['no_posthoc_seed_or_task_selection'] is True and measurement['confirmatory_claim_authorized'] is False,'MEASUREMENT_BOUNDARY')
    need(missing['complete_grid_required_for_complete_result'] is True and missing['missing_infrastructure_cells_must_not_be_scored_as_failure'] is True and missing['partial_status_preserved'] is True and missing['automatic_policy_change_or_retry_authorized'] is False,'MISSINGNESS_BOUNDARY')
    value={'schema_id':'CLEAN_SELECT_EVALUATION_PROTOCOL_V1','schema_version':1,
      'round_id':a['round_id'],'source_review_sha256':source_sha,'decision_sha256':sha(cb(d)),
      'source_head':data['receipt']['source_head'],'fixed_head':head,'fixed_tree':tree,'code_closure_sha256':code_sha,
      'training_plan_sha256':a['training_plan_sha256'],'training_receipt_sha256':a['stage_receipt_sha256'],
      'grid':g,'model_binding':m,'pool_references':data['refs'],'measurement':d['measurement'],
      'grid_is_exact_approved_proposal':True,'protocol_frozen':True,'evaluation_execution_authorized':False,
      'parent_candidate_interface_equal':True,'primary_actor':d['decision_actor'],'authority_phase':d['authority_phase'],
      'budget_ceiling':{'policy_attempts':g['condition_episodes']*g['episode_budget']['max_policy_attempts'],
                       'environment_steps':g['condition_episodes']*g['episode_budget']['max_environment_steps']},
      'missingness_policy':d['missingness_policy'],'promotion_eligible':False,
      'archive_provenance_complete':a['archive_provenance_complete'],'training_execution_authorized':False,
      'upstream_proposals_are_retained_unchanged':True,'protocol_sha256':'0'*64}
    value['protocol_sha256']=domain_hash(value['schema_id'],value,'protocol_sha256')
    return value


def tree_entries(repo: Path,ref: str) -> dict:
    records=git(repo,'ls-tree','-rz','--full-tree',ref).split(b'\0');result={}
    for record in records:
        if not record:continue
        meta,name=record.split(b'\t',1);mode,kind,oid=meta.decode().split()
        need(kind=='blob' and mode in ('100644','100755'),'UNSUPPORTED_GIT_ENTRY')
        result[os.fsdecode(name)]={'mode':mode,'blob':oid}
    return result


def expected_tree(repo: Path,base: str,scope: dict) -> dict:
    entries=tree_entries(repo,base);oids=list(dict.fromkeys(x['blob'] for x in entries.values()))
    raw=subprocess.run(['git','cat-file','--batch'],cwd=repo,input=('\n'.join(oids)+'\n').encode(),stdout=subprocess.PIPE,check=True).stdout
    cursor=0;hashes={}
    for oid in oids:
        end=raw.index(b'\n',cursor);header=raw[cursor:end].decode().split();need(header[0]==oid and header[1]=='blob','GIT_BATCH_HEADER')
        count=int(header[2]);value=raw[end+1:end+1+count];need(len(value)==count,'GIT_BATCH_LENGTH')
        hashes[oid]=sha(value);cursor=end+1+count+1
    result={n:{'mode':x['mode'],'sha256':hashes[x['blob']]} for n,x in entries.items()}
    for n,s in scope.items():
        need((result.get(n) or {}).get('sha256')==s['before_file_sha256'],'PATCH_BASE_MISMATCH:'+n)
        result[n]={'mode':result.get(n,{}).get('mode','100644'),'sha256':s['after_file_sha256']}
    return result


def check_tree(repo: Path,expected: dict,base: str) -> None:
    for n,s in expected.items():
        p=repo/n;need(file_sha(p)==s['sha256'],'WORKTREE_BYTES:'+n)
        need(bool(p.stat().st_mode & 0o111)==(s['mode']=='100755'),'WORKTREE_MODE:'+n)
    known=set(tree_entries(repo,base))
    untracked={os.fsdecode(x) for x in git(repo,'ls-files','--others','--exclude-standard','-z').split(b'\0') if x}
    need(untracked <= set(expected)-known,'WORKTREE_EXTRA:'+repr(sorted(untracked-(set(expected)-known))))
    # Explicitly reject index flags even if bytes happen to match now.
    flags=git(repo,'ls-files','-v','-z').split(b'\0')
    need(all(not f or f[:1]==b'H' for f in flags),'INDEX_FLAGS_NOT_NORMAL')


def freeze_ref(expected: dict) -> str:
    return 'refs/heads/review/clean-select-i1-'+sha(cb(expected))[:12]


def freeze_code(repo: Path,base: str,expected: dict,scope: dict,out: Path) -> dict:
    check_tree(repo,expected,base);head=git(repo,'rev-parse','HEAD').decode().strip();ref=freeze_ref(expected)
    oldref=command(['git','show-ref','--verify','--hash',ref],repo,check=False)
    if head==base:
        need(oldref.returncode!=0,'FREEZE_REF_CONFLICT')
        need(command(['git','symbolic-ref','-q','HEAD'],repo,check=False).returncode!=0,'EXPECTED_DETACHED_CODE_WORKTREE')
        staged={os.fsdecode(x) for x in git(repo,'diff','--cached','--name-only','-z').split(b'\0') if x}
        need(staged <= set(scope),'STAGED_SCOPE')
        git(repo,'add','--',*sorted(scope))
        staged={os.fsdecode(x) for x in git(repo,'diff','--cached','--name-only','-z').split(b'\0') if x}
        need(staged==set(scope),'STAGED_SCOPE')
        git(repo,'commit','-m','Add explicit I1 binding to existing SELECT evaluation')
        head=git(repo,'rev-parse','HEAD').decode().strip()
    else:
        need(git(repo,'rev-parse',head+'^').decode().strip()==base,'FIXED_PARENT_MISMATCH')
        need(git(repo,'show','-s','--format=%s',head).decode().strip()=='Add explicit I1 binding to existing SELECT evaluation','FIXED_COMMIT_MESSAGE')
    check_tree(repo,expected,base)
    changed={os.fsdecode(x) for x in git(repo,'diff','--name-only','-z',base,head).split(b'\0') if x}
    need(changed==set(scope),'FIXED_COMMIT_SCOPE')
    need(not git(repo,'status','--porcelain=v1','-z','--untracked-files=all'),'FIXED_WORKTREE_NOT_CLEAN')
    oldref=command(['git','show-ref','--verify','--hash',ref],repo,check=False)
    if oldref.returncode==0:need(oldref.stdout.decode().strip()==head,'FREEZE_REF_CONFLICT')
    else:git(repo,'update-ref',ref,head,'0'*40)
    tree=git(repo,'rev-parse',head+'^{tree}').decode().strip()
    value={'schema_id':'SELECT_FIXED_CODE_RECEIPT_V1','head':head,'tree':tree,'parent':base,'ref':ref,
           'code_closure_sha256':sha(cb(expected)),'changed_paths':sorted(scope),'main_updated':False,'remote_published':False}
    write_once(out/'FIXED_CODE.json',cb(value))
    bundle=out/'SELECT_CODE_HISTORY.bundle'
    if not bundle.exists():git(repo,'bundle','create',str(bundle),ref)
    git(repo,'bundle','verify',str(bundle))
    heads=git(repo,'bundle','list-heads',str(bundle),ref).decode().split()
    need(heads==[head,ref],'BUNDLE_REF_IDENTITY')
    write_once(out/'FIXED_CODE.patch',git(repo,'diff','--binary',base,head))
    return value


def publish_review(out: Path,files: dict[str,bytes]) -> Path:
    encoded=dict(files);encoded['FILES.sha256.json']=cb({n:sha(b) for n,b in files.items()})
    for n,b in encoded.items():write_once(out/n,b)
    bundle=out/'SELECT_CODE_PROTOCOL_REVIEW.zip'
    if bundle.exists():
        with zipfile.ZipFile(bundle) as z:old={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
        need(old==encoded,'REVIEW_BUNDLE_CONFLICT')
    else:
        fd,tmp=tempfile.mkstemp(dir=out,prefix='.archive-');os.close(fd);temp=Path(tmp)
        try:
            with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for n,b in sorted(encoded.items()):
                    i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b)
            os.link(temp,bundle)
        finally:temp.unlink(missing_ok=True)
    return bundle
