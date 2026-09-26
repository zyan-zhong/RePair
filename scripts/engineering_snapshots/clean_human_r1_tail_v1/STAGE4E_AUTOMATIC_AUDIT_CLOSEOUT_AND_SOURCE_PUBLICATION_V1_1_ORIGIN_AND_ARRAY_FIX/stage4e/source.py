"""Isolated source integration, exhaustive static index, and FF-only publication."""
from __future__ import annotations
import ast
import os
from pathlib import Path
import re
import subprocess
from typing import Any
from . import GateError, canonical, file_sha, regular, safe_child, semantic_sha, write_exact, write_bytes_exact

SNAPSHOT_PREFIX = 'scripts/engineering_snapshots/clean_human_r1_tail_v1'
DOC_PREFIX = 'docs/project/clean_human_r1_tail_v1'

def run(args: list[str], *, cwd: Path | None=None, env: dict | None=None, timeout: int=600) -> str:
    if args and args[0]=='git':
        env=dict(os.environ if env is None else env,GIT_TERMINAL_PROMPT='0')
    p=subprocess.run(args,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode:
        raise GateError(f'COMMAND_FAILED:{args[0]}:rc={p.returncode}\n'+p.stderr[-8000:])
    return p.stdout.strip()

def git(repo: Path, *args: str) -> str:
    env=os.environ.copy();env['GIT_OPTIONAL_LOCKS']='0';env['GIT_TERMINAL_PROMPT']='0'
    return run(['git','-C',str(repo),*args],env=env)

def require_ancestor(repo: Path, ancestor: str, target: str) -> None:
    p=subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',ancestor,target],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode != 0:raise GateError(f'NON_FAST_FORWARD_REFUSED:{ancestor}:{target}')

def is_snapshot_source(name: str) -> bool:
    p=Path(name)
    if any(x in {'__pycache__','.git','verification','runtime','execution','reviewed_inputs','payload'} for x in p.parts):
        return False
    # Only code/tests and explanatory documentation; real JSON artifacts are never swept into Git.
    return p.suffix in {'.py','.sh','.md','.patch'}

def reject_secret(raw: bytes, name: str) -> None:
    expressions=(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}',rb'\bgh[pousr]_[A-Za-z0-9]{24,}',
                 rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                 rb'https?://[^\s/"\']+:[^\s/@"\']+@')
    if any(re.search(p,raw) for p in expressions):
        raise GateError('POSSIBLE_LITERAL_SECRET_NOT_PUBLISHED:'+name)

def inspect_python(path: Path) -> dict:
    raw=regular(path).read_text(encoding='utf-8');tree=ast.parse(raw,filename=str(path))
    symbols=[]
    def visit(node, prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                name=prefix+child.name
                symbols.append({'name':name,'kind':type(child).__name__,'line':child.lineno,
                                'end_line':child.end_lineno,
                                'signature':ast.unparse(child.args) if hasattr(child,'args') else None})
                visit(child,name+'.')
            else:visit(child,prefix)
    visit(tree)
    imports=[];calls=[]
    for n in ast.walk(tree):
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            imports.append({'line':n.lineno,'statement':ast.unparse(n)})
        elif isinstance(n,ast.Call):
            calls.append({'line':n.lineno,'expression':ast.unparse(n.func)})
    return {'symbols':symbols,'imports':sorted(imports,key=lambda x:x['line']),
            'calls':sorted(calls,key=lambda x:x['line']),
            'dynamic_call_resolution_complete':False}

def source_inventory(repo: Path, names: list[str]) -> dict:
    return {n:file_sha(safe_child(repo,n)) for n in sorted(set(names))}

def verify_active_repo(repo: Path, cfg: dict) -> None:
    if git(repo,'rev-parse','HEAD') != cfg['fixed_head'] or git(repo,'rev-parse','HEAD^{tree}') != cfg['fixed_tree']:
        raise GateError('ACTIVE_FIXED_SOURCE_CHANGED')
    if git(repo,'status','--porcelain'):
        raise GateError('ACTIVE_FIXED_SOURCE_DIRTY')

def approved_origin_pair(repo: Path, approved_urls: list[str]) -> tuple[str, str]:
    """Validate both effective fetch and push destinations, including Git rewrites."""
    fetch = git(repo, 'remote', 'get-url', '--all', 'origin').splitlines()
    push = git(repo, 'remote', 'get-url', '--push', '--all', 'origin').splitlines()
    if len(fetch) != 1 or len(push) != 1:
        raise GateError('ORIGIN_MULTIPLE_DESTINATIONS_NOT_APPROVED')
    if fetch[0] not in approved_urls or push[0] not in approved_urls:
        # Do not echo arbitrary URLs which might contain embedded credentials.
        raise GateError('ORIGIN_NOT_EXPLICITLY_APPROVED:fetch_or_push_destination')
    return fetch[0], push[0]


def optional_git_config(repo: Path, key: str) -> str | None:
    p = subprocess.run(['git', '-C', str(repo), 'config', '--get', key],
                       capture_output=True, text=True)
    if p.returncode == 1:
        return None
    if p.returncode:
        raise GateError('GIT_CONFIG_READ_FAILED:' + key)
    return p.stdout.strip()


def ensure_isolated_repo(*, active: Path, dest: Path, cfg: dict) -> None:
    verify_active_repo(active,cfg)
    # Check before clone: a transport mismatch must not leave a half-initialized tree.
    fetch_url, push_url = approved_origin_pair(active, cfg['allowed_origin_urls'])
    if dest.is_symlink() or (dest / '.git').is_symlink():
        raise GateError('INTEGRATION_SYMLINK_FORBIDDEN')
    created = not dest.exists()
    if created:
        dest.parent.mkdir(parents=True,exist_ok=True)
        run(['git','clone','--no-hardlinks','--no-checkout',str(active),str(dest)])
        git(dest,'checkout','-b',cfg['publication_branch'],cfg['fixed_head'])
    anchor = optional_git_config(dest, 'stage4e.anchor')
    role = optional_git_config(dest, 'stage4e.role')
    if anchor is None:
        # Only recover the exact clean clone left by V1's origin check failure.
        # Never reset, delete, adopt unrelated files, or overwrite an arbitrary checkout.
        verify_active_repo(dest,cfg)
        if git(dest,'branch','--show-current') != cfg['publication_branch']:
            raise GateError('PARTIAL_INTEGRATION_BRANCH_CHANGED')
        if role not in (None, 'ISOLATED_SOURCE_INTEGRATION'):
            raise GateError('PARTIAL_INTEGRATION_ROLE_CHANGED')
        old = git(dest,'remote','get-url','origin')
        if old not in (str(active), str(active.resolve()), fetch_url):
            raise GateError('PARTIAL_INTEGRATION_NOT_ORIGINAL_LOCAL_CLONE')
        # A clone normally has no pushurl; reject any unrelated pre-existing override.
        old_push = git(dest,'remote','get-url','--push','--all','origin').splitlines()
        if len(old_push) != 1 or old_push[0] not in (old, push_url):
            raise GateError('PARTIAL_INTEGRATION_PUSH_DESTINATION_CHANGED')
        git(dest,'remote','set-url','origin',fetch_url)
        git(dest,'remote','set-url','--push','origin',push_url)
        git(dest,'config','stage4e.anchor',cfg['fixed_head'])
        git(dest,'config','stage4e.role','ISOLATED_SOURCE_INTEGRATION')
        for key,fallback in [('user.name','Stage4E automation'),('user.email','stage4e-automation@example.invalid')]:
            value = optional_git_config(active, key) or fallback
            git(dest,'config',key,value)
        if not created:
            print('STAGE4E_EXACT_PARTIAL_CLONE_RECOVERED_NO_RESET', flush=True)
    if optional_git_config(dest,'stage4e.anchor') != cfg['fixed_head']:
        raise GateError('INTEGRATION_CHECKOUT_ANCHOR_CHANGED')
    if optional_git_config(dest,'stage4e.role') != 'ISOLATED_SOURCE_INTEGRATION':
        raise GateError('INTEGRATION_CHECKOUT_ROLE_CHANGED')
    if git(dest,'branch','--show-current') != cfg['publication_branch']:
        raise GateError('INTEGRATION_CHECKOUT_BRANCH_CHANGED')
    if approved_origin_pair(dest, cfg['allowed_origin_urls']) != (fetch_url, push_url):
        raise GateError('INTEGRATION_ORIGIN_DIFFERS_FROM_APPROVED_ACTIVE')
    require_ancestor(dest,cfg['fixed_head'],'HEAD')
    verify_active_repo(active,cfg)

def stage_explicit(repo: Path, names: list[str]) -> None:
    for name in names:
        path=safe_child(repo,name)
        reject_secret(regular(path).read_bytes(),name)
    if names:git(repo,'add','--',*names)
    staged=git(repo,'diff','--cached','--name-only').splitlines()
    if not set(staged).issubset(set(names)):
        raise GateError('UNEXPECTED_PREEXISTING_STAGED_FILES')
    git(repo,'diff','--cached','--check')

def commit_staged(repo: Path, message: str) -> str:
    if git(repo,'diff','--cached','--name-only'):
        git(repo,'commit','-m',message)
    return git(repo,'rev-parse','HEAD')

def publish_atomic(*, repo: Path, branch: str, include_main: bool, approved_urls: list[str]) -> dict:
    approved_origin_pair(repo, approved_urls)
    if git(repo,'status','--porcelain'):
        raise GateError('PUBLISH_CHECKOUT_NOT_CLEAN')
    target=git(repo,'rev-parse','HEAD')
    # A fresh read, not a cached origin/main or a remembered remote SHA.
    run(['git','-C',str(repo),'fetch','--no-tags','origin','main'])
    remote_main=git(repo,'rev-parse','FETCH_HEAD')
    if include_main:require_ancestor(repo,remote_main,target)
    refs=[f'{target}:refs/heads/{branch}']
    if include_main:refs.append(f'{target}:refs/heads/main')
    run(['git','-C',str(repo),'push','--atomic','origin',*refs])
    observed=git(repo,'ls-remote',approved_origin_pair(repo, approved_urls)[1],f'refs/heads/{branch}',*(['refs/heads/main'] if include_main else []))
    values={row.split()[1]:row.split()[0] for row in observed.splitlines() if row}
    required=[f'refs/heads/{branch}']+(['refs/heads/main'] if include_main else [])
    if any(values.get(k)!=target for k in required):
        raise GateError('REMOTE_PUBLICATION_EQUALITY_FAILED')
    return {'schema_id':'CLEAN_ROUND_SOURCE_PUBLICATION_RECEIPT_V1','status':'REMOTE_VERIFIED',
            'commit':target,'branch':branch,'main_updated':include_main,'previous_main':remote_main,
            'atomic_push':True,'force_push':False,'verified_refs':values}

def build_source_map(*, repo: Path, cfg: dict, additional_names: list[str], route: dict) -> tuple[dict,str]:
    # Index the exact historical tree and explicit new source snapshots, never scan runtime outputs.
    base_names=git(repo,'ls-tree','-r','--name-only',cfg['fixed_head']).splitlines()
    names=sorted(set(base_names+additional_names))
    records=[]
    for name in names:
        path=safe_child(repo,name)
        if not path.is_file():
            raise GateError('SOURCE_MAP_FILE_MISSING:'+name)
        record={'path':name,'file_sha256':file_sha(path),'size_bytes':path.stat().st_size,
                'kind':'NATIVE_FIXED_TREE' if name in base_names else 'EXPLICIT_EXECUTION_SNAPSHOT'}
        if path.suffix=='.py':record.update(inspect_python(path))
        records.append(record)
    indexed={x['path']:x for x in records}
    for step in route['steps']:
        for name in step['source_paths']:
            if name not in indexed:raise GateError('CODE_ROUTE_PATH_UNRESOLVED:'+name)
    result={'schema_id':'CLEAN_ROUND_FULL_SOURCE_CHAIN_MAP_V1','schema_version':1,
            'fixed_head':cfg['fixed_head'],'fixed_tree':cfg['fixed_tree'],
            'round_id':cfg['round_id'],'routes':route['steps'],'files':records,
            'source_file_count':len(records),'python_symbol_count':sum(len(x.get('symbols',[])) for x in records),
            'evidence_scope':'STATIC_SOURCE_INDEX_AND_REVIEWED_PRIMARY_CALL_ROUTES_NOT_DYNAMIC_EXECUTION_PROOF',
            'unresolved_future_execution_requirements':route['unresolved_future_execution_requirements']}
    md=['# Clean Human Reference Round: complete code and data handoff map','',
        f"Fixed source: `{cfg['fixed_head']}` / tree `{cfg['fixed_tree']}`.",
        f"Round: `{cfg['round_id']}`. Parent: `PI0_CLEAN`. Candidate remains diagnostic-only.",'',
        '## Scope and authority','',
        '- This index preserves existing modules, historical snapshots and exact external execution drivers.',
        '- Native module existence, live execution, result approval and autonomous takeover are distinct states.',
        '- The older project baseline JSON contains historical pilot `current_round` metadata. Current execution authority is the frozen clean-round protocol/binding, not that historical label.',
        '- No current SELECT task-level observations, actions or outcomes may be fed to Analyzer/Planner; only the audited aggregate projection may be consumed.',
        '- The companion JSON lists every file hash, Python class/function signature, source lines, imports and syntactic call sites. Dynamic targets are not claimed to be fully resolved.','',
        '## Primary end-to-end route','']
    for i,step in enumerate(route['steps'],1):
        md.extend([f"### {i}. {step['component']}",'',f"Input: {step['input']}",f"Output: {step['output']}",
                   f"Authority / boundary: {step['boundary']}",''])
        for name in step['source_paths']:
            r=indexed[name];md.append(f"- [`{name}`](../../../{name}) — SHA-256 `{r['file_sha256']}`")
            selected=r.get('symbols',[])
            if selected:md.append('  Symbols: '+', '.join(f"`{s['name']}` L{s['line']}–L{s['end_line']}" for s in selected)+'.')
        md.append('')
    md.extend(['## Machine-stopped future dependencies',''])
    md.extend('- '+x for x in route['unresolved_future_execution_requirements'])
    md.extend(['','## Exact runtime locations',''])
    for key in ['round_root','binding_root','execution_root','protocol','candidate','full_package','readiness_package']:
        v=cfg[key];md.append(f'- `{key}`: `{v["path"] if isinstance(v,dict) else v}`')
    md.extend(['','## Status','',
        'This is an engineering source map, not evidence that the active four-GPU run has finished. Final disposition is emitted only after every registered cell passes the existing attempt and SELECT audits.',
        'The current diagnostic candidate cannot be promoted by a positive observed SELECT delta. The automatic disposition retains the parent, while preserving the measured delta.',''])
    return result,'\n'.join(md)
