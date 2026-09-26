"""Small immutable I/O boundary for the execution wrapper."""
from __future__ import annotations
import hashlib, json, os, stat, zipfile
from pathlib import Path, PurePosixPath
from typing import Any


def canonical(value: object)->bytes:
    return (json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()


def sha(raw: bytes)->str:return hashlib.sha256(raw).hexdigest()


def digest_file(path: Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def strict_loads(raw: bytes|str)->Any:
    def pairs(rows):
        d={}
        for k,v in rows:
            if k in d:raise ValueError('duplicate JSON key: '+k)
            d[k]=v
        return d
    def bad(x):raise ValueError('non-finite JSON value: '+x)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)


def read_json(path: Path)->Any:return strict_loads(path.read_bytes())


def write_new_or_equal(path: Path,raw: bytes)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():raise ValueError('symlink output forbidden: '+str(path))
    try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:
        if path.read_bytes()!=raw:raise ValueError('immutable output differs: '+str(path))
        return
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())


def put_json(path:Path,value:object)->None:write_new_or_equal(path,canonical(value))


def verify_extract(archive:Path,expected_sha:str,destination:Path)->dict[str,Any]:
    if digest_file(archive)!=expected_sha:raise ValueError('input archive SHA mismatch')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('duplicate ZIP member')
        for info in z.infolist():
            p=PurePosixPath(info.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in info.filename or stat.S_ISLNK(info.external_attr>>16):
                raise ValueError('unsafe ZIP member: '+info.filename)
        index=strict_loads(z.read('CAPTURE_INDEX.json'))
        rows=index.get('files')
        if not isinstance(rows,list):raise ValueError('capture index absent')
        declared={r['member']:r for r in rows}
        if len(declared)!=len(rows) or set(declared)|{'CAPTURE_INDEX.json'}!=set(names):
            raise ValueError('capture member set mismatch')
        for name,r in declared.items():
            raw=z.read(name)
            if sha(raw)!=r['sha256'] or len(raw)!=r['bytes']:raise ValueError('capture member hash mismatch: '+name)
            write_new_or_equal(destination/name,raw)
        write_new_or_equal(destination/'CAPTURE_INDEX.json',z.read('CAPTURE_INDEX.json'))
    return index


def object_hash(domain:str,payload:dict,excluded:str|None=None)->str:
    p=dict(payload)
    if excluded:p.pop(excluded,None)
    # Existing reference_loop.domain_hash excludes final LF.
    return sha(domain.encode()+b'\0'+canonical(p).rstrip(b'\n'))
