from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
from typing import Mapping

REQ=('round_id','parent_policy_id','memory_snapshot_path','round_root')


def validate_round_entry_binding(value: Mapping[str,object]) -> dict[str,object]:
    if value.get('schema_id')!='NEXT_ROUND_UPSTREAM_LAUNCH_BINDING_V1' or value.get('schema_version')!=1:
        raise ValueError('ROUND_ENTRY_BINDING_SCHEMA_MISMATCH')
    if value.get('shell') is not False: raise ValueError('ROUND_ENTRY_SHELL_MUST_BE_FALSE')
    if value.get('human_decision_required') is not False: raise ValueError('ROUND_ENTRY_HUMAN_DECISION_FORBIDDEN')
    argv=value.get('argv_template')
    if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x for x in argv): raise ValueError('ROUND_ENTRY_ARGV_TEMPLATE_INVALID')
    placeholders=value.get('required_placeholders')
    if not isinstance(placeholders,list) or sorted(placeholders)!=sorted(REQ): raise ValueError('ROUND_ENTRY_REQUIRED_PLACEHOLDERS_CHANGED')
    joined='\0'.join(argv)
    for key in REQ:
        if '{'+key+'}' not in joined: raise ValueError('ROUND_ENTRY_PLACEHOLDER_MISSING:'+key)
    for key in ('started_receipt_relative_path','terminal_receipt_relative_path'):
        p=value.get(key)
        if not isinstance(p,str) or not p or Path(p).is_absolute() or '..' in Path(p).parts: raise ValueError('ROUND_ENTRY_RECEIPT_PATH_INVALID:'+key)
    head=value.get('fixed_head')
    if not isinstance(head,str) or len(head)!=40: raise ValueError('ROUND_ENTRY_FIXED_HEAD_INVALID')
    return dict(value)


def render_round_entry_argv(value: Mapping[str,object], **bindings: str) -> list[str]:
    value=validate_round_entry_binding(value)
    if set(bindings)!=set(REQ): raise ValueError('ROUND_ENTRY_RENDER_BINDINGS_CHANGED')
    for key,val in bindings.items():
        if not isinstance(val,str) or not val: raise ValueError('ROUND_ENTRY_RENDER_VALUE_INVALID:'+key)
    return [part.format(**bindings) for part in value['argv_template']]


def launch_round_entry(value: Mapping[str,object], *, cwd:Path|None=None, **bindings:str) -> dict[str,object]:
    argv=render_round_entry_argv(value,**bindings)
    round_root=Path(bindings['round_root']).resolve()
    started=round_root/str(value['started_receipt_relative_path']); terminal=round_root/str(value['terminal_receipt_relative_path'])
    if terminal.is_file():
        return {'launched':False,'reused_terminal':True,'terminal_receipt_path':str(terminal),'argv':argv}
    if started.is_file():
        raise ValueError('ROUND_ENTRY_STARTED_WITHOUT_TERMINAL_NO_BLIND_RESEND')
    cp=subprocess.run(argv,cwd=str(cwd) if cwd else None,check=False,shell=False)
    if cp.returncode!=0: raise ValueError('ROUND_ENTRY_COMMAND_FAILED:'+str(cp.returncode))
    if not terminal.is_file(): raise ValueError('ROUND_ENTRY_COMMAND_RETURNED_WITHOUT_TERMINAL_RECEIPT')
    return {'launched':True,'reused_terminal':False,'terminal_receipt_path':str(terminal),'argv':argv}
