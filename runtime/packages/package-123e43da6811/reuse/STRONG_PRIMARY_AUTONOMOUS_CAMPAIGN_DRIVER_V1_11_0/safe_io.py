from __future__ import annotations
import hashlib,json,os,tempfile
from pathlib import Path

def canonical_bytes(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def load_obj(p:Path,max_bytes:int=64*1024*1024):
    p=Path(p)
    if not p.is_file() or p.is_symlink(): raise ValueError('JSON_REGULAR_FILE_REQUIRED:'+str(p))
    if p.stat().st_size>max_bytes: raise ValueError('JSON_FILE_TOO_LARGE:'+str(p))
    def dup(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise ValueError('DUPLICATE_JSON_KEY:'+k)
            d[k]=v
        return d
    value=json.loads(p.read_text(encoding='utf-8'),object_pairs_hook=dup,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    if not isinstance(value,dict): raise ValueError('JSON_OBJECT_REQUIRED:'+str(p))
    return value
def write_once(p:Path,v):
    p=Path(p); b=canonical_bytes(v)+b'\n'; p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() or p.is_symlink():
        if p.is_symlink() or not p.is_file() or p.read_bytes()!=b: raise ValueError('IMMUTABLE_OUTPUT_CONFLICT:'+str(p))
        return
    fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.',dir=p.parent)
    try:
        os.write(fd,b); os.fsync(fd); os.close(fd); fd=-1; os.replace(tmp,p)
    finally:
        if fd>=0: os.close(fd)
        if os.path.exists(tmp): os.unlink(tmp)

def domain_hash(domain,v,field='receipt_sha256'):
    x=dict(v); x.pop(field,None)
    return hashlib.sha256(domain.encode()+b'\0'+canonical_bytes(x)).hexdigest()
