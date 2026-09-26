"""Resolve only previously registered data/Memory locators against current authority."""
from __future__ import annotations
import os
from collections.abc import Mapping
from pathlib import Path
from io_utils import read_json, strict_loads, digest_file, sha, canonical


def resolve_memory(*, request, locators):
    expected=request['round_memory_runtime_authority_sha256']
    explicit=os.environ.get(locators['memory_runtime_environment_variable'])
    paths=[Path(explicit)] if explicit else list(Path(locators['scripts_root']).glob(locators['bootstrap_memory_relative_glob']))
    matched={}; diagnostics=[]
    for path in paths:
        if path.is_symlink() or not path.is_file():
            diagnostics.append({'path':str(path),'reason':'not_regular'});continue
        file_sha=digest_file(path)
        if file_sha!=expected:
            diagnostics.append({'path':str(path),'reason':'different_file_identity'});continue
        value=read_json(path)
        if value.get('schema_id')!='FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1':
            raise ValueError('matched Memory bytes have wrong schema')
        for key,reqkey in [('active_snapshot_sha256','round_start_memory_snapshot_sha256'),
                           ('token_budget_contract_sha256','token_budget_contract_sha256')]:
            if value.get(key)!=request[reqkey]:raise ValueError('Memory current authority mismatch: '+key)
        matched[file_sha]={'path':str(path.resolve()),'file_sha256':file_sha,'value':value}
    if len(matched)!=1:
        raise ValueError('EXACT_CURRENT_MEMORY_RUNTIME_UNRESOLVED:'+str(diagnostics))
    return next(iter(matched.values()))


def resolve_gamefiles(*, request, source_rows, locators):
    manifest=Path(locators['train_update_manifest_path'])
    if manifest.is_symlink() or not manifest.is_file():raise ValueError('registered TRAIN_UPDATE manifest missing')
    if digest_file(manifest)!=request['train_update_manifest_sha256']:
        raise ValueError('registered TRAIN_UPDATE manifest raw SHA mismatch')
    all_rows=[strict_loads(line) for line in manifest.read_bytes().splitlines()]
    by_id={};indices=set()
    for value in all_rows:
        if not isinstance(value,dict) or value.get('schema_id')!='ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1' or value.get('split')!='train' or value.get('train_pool')!='TRAIN_UPDATE':
            raise ValueError('untrusted TRAIN_UPDATE row')
        tid=value.get('id');idx=value.get('index')
        if not isinstance(tid,str) or type(idx) is not int or tid in by_id or idx in indices:
            raise ValueError('TRAIN_UPDATE task identity is not unique')
        by_id[tid]=value;indices.add(idx)
    root=Path(locators['train_root']).resolve();out={}
    if root.name!='train' or not root.is_dir():raise ValueError('exact TRAIN root unavailable')
    for row in source_rows:
        fp=row['fingerprint'];episode=row['bundle'].episode_artifact
        if isinstance(fp, Mapping):
            task_id=fp['source_task_id'];gamefile_sha=fp['source_gamefile_sha256']
        else:
            task_id=fp.source_task_id;gamefile_sha=fp.source_gamefile_sha256
        task=by_id.get(task_id)
        if task is None or task.get('index')!=episode.task_index or task.get('gamefile_sha256')!=gamefile_sha:
            raise ValueError('selected source does not match frozen TRAIN_UPDATE record')
        verified={}
        for relkey,shakey in [('gamefile_relpath','gamefile_sha256'),('traj_file_relpath','traj_sha256'),('initial_state_relpath','initial_state_sha256')]:
            rel=Path(task[relkey])
            if rel.is_absolute() or '..' in rel.parts:raise ValueError('task asset escapes TRAIN root')
            path=root/rel
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
                raise ValueError('bound TRAIN asset is not regular or escapes root')
            if digest_file(path)!=task[shakey]:raise ValueError('selected TRAIN asset hash mismatch: '+relkey)
            verified[relkey]=str(path.resolve())
        if len({str(Path(x).parent) for x in verified.values()})!=1:
            raise ValueError('selected game/traj/initial state parents differ')
        out[task_id]={'gamefile':verified['gamefile_relpath'],'record':task,
                                'source_manifest_file_sha256':request['train_update_manifest_sha256']}
    return out
