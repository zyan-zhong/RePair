from __future__ import annotations
from pathlib import Path
from safe_io import load_obj

def unique_json_by_schema(root,schema,max_files=4096):
    root=Path(root); hits=[]; n=0
    for p in ([root] if root.is_file() else sorted(root.rglob('*.json'))):
        if not p.is_file() or p.is_symlink(): continue
        n+=1
        if n>max_files: raise ValueError('SCAN_BUDGET_EXCEEDED')
        try:o=load_obj(p)
        except Exception:continue
        if isinstance(o,dict) and o.get('schema_id')==schema:hits.append((p,o))
    if not hits:return {'present':False,'path':None,'value':None}
    if len(hits)!=1:raise ValueError('AMBIGUOUS_SCHEMA:'+schema)
    return {'present':True,'path':str(hits[0][0]),'value':hits[0][1]}

def unique_existing_path(values,label):
    hits=sorted({str(Path(x).resolve()) for x in values if isinstance(x,str) and Path(x).exists()})
    if len(hits)!=1: raise ValueError(label+('_NOT_BOUND' if not hits else '_AMBIGUOUS'))
    return hits[0]
