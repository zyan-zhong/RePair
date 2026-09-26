"""Execution-context equivalence reused from the durable pair-universe V1.2 asset.

This package-local copy preserves the already-staged semantics used by
integration/strong-primary-pair-universe-v1-2. It separates execution identity
from provenance wrappers and fails closed on execution-relevant conflicts.
"""
from __future__ import annotations
from collections.abc import Iterable, Mapping
import hashlib, json
from typing import Any
_HEX=frozenset('0123456789abcdef')
def _is_sha256(value:object)->bool:
    return isinstance(value,str) and len(value)==64 and set(value)<=_HEX
def _canonical_bytes(value:Mapping[str,object])->bytes:
    return (json.dumps(dict(value),ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
def _sha256_object(value:Mapping[str,object])->str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()
def execution_context_projection(row:Mapping[str,object])->dict[str,object]:
    state=row.get('source_state_sha256'); menu=row.get('menu_sha256'); commands=row.get('admissible_commands')
    if not _is_sha256(state): raise ValueError('source_state_sha256 missing/invalid')
    if not _is_sha256(menu): raise ValueError('menu_sha256 missing/invalid')
    if not isinstance(commands,list) or any(not isinstance(x,str) or not x for x in commands):
        raise ValueError('admissible_commands missing/invalid')
    return {'source_state_sha256':state,'menu_sha256':menu,'admissible_commands':list(commands)}
def index_source_contexts(rows:Iterable[Mapping[str,object]])->dict[str,dict[str,Any]]:
    by_state={}
    for raw in rows:
        row=dict(raw)
        try: execution=execution_context_projection(row)
        except ValueError: continue
        state=str(execution['source_state_sha256']); execution_sha=_sha256_object(execution); provenance_sha=_sha256_object(row)
        entry=by_state.get(state)
        if entry is None:
            by_state[state]={'execution_context':execution,'execution_context_sha256':execution_sha,'provenance_variants':[row],'provenance_variant_sha256s':[provenance_sha],'execution_context_conflict':False}
            continue
        if entry['execution_context_sha256']!=execution_sha:
            prev=entry['execution_context']; diff={k:{'existing':prev.get(k),'observed':execution.get(k)} for k in ('source_state_sha256','menu_sha256','admissible_commands') if prev.get(k)!=execution.get(k)}
            raise ValueError('EXECUTION_CONTEXT_CONFLICT:'+state+':'+json.dumps(diff,sort_keys=True,separators=(',',':')))
        if provenance_sha not in set(entry['provenance_variant_sha256s']):
            entry['provenance_variants'].append(row); entry['provenance_variant_sha256s'].append(provenance_sha)
    for entry in by_state.values():
        paired=sorted(zip(entry['provenance_variant_sha256s'],entry['provenance_variants'],strict=True),key=lambda x:x[0])
        entry['provenance_variant_sha256s']=[x for x,_ in paired]; entry['provenance_variants']=[x for _,x in paired]
    return by_state
def source_context_for_candidate_projection(entry:Mapping[str,object])->dict[str,object]:
    context=entry.get('execution_context')
    if not isinstance(context,dict): raise ValueError('source-context entry lacks execution_context')
    return dict(context)
def source_context_audit_summary(entry:Mapping[str,object])->dict[str,object]:
    shas=entry.get('provenance_variant_sha256s')
    if not isinstance(shas,list): raise ValueError('source-context entry lacks provenance SHA list')
    return {'execution_context_sha256':entry.get('execution_context_sha256'),'provenance_variant_count':len(shas),'provenance_variant_sha256s':list(shas),'execution_context_conflict':bool(entry.get('execution_context_conflict',False))}
