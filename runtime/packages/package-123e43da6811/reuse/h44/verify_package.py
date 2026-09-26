from __future__ import annotations
import ast
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/'PACKAGE_FILES.sha256'

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main()->int:
    expected={}
    for line in MANIFEST.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        d,rel=line.split('  ',1)
        if rel in expected: raise RuntimeError('PACKAGE_MANIFEST_DUPLICATE:'+rel)
        expected[rel]=d
    observed={
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob('*') if p.is_file() and p!=MANIFEST
        and '__pycache__' not in p.parts and p.suffix!='.pyc'
    }
    if set(expected)!=observed:
        raise RuntimeError('PACKAGE_MANIFEST_MEMBER_SET_MISMATCH:extra='+repr(sorted(observed-set(expected)))+':missing='+repr(sorted(set(expected)-observed)))
    for rel,d in expected.items():
        if digest(ROOT/rel)!=d: raise RuntimeError('PACKAGE_SHA256_MISMATCH:'+rel)
    print('PACKAGE_SHA256_VERIFY_PASS files='+str(len(expected)))
    for p in ROOT.rglob('*.py'):
        if '__pycache__' in p.parts: continue
        ast.parse(p.read_text(encoding='utf-8'), filename=str(p), feature_version=(3,12))
    print('PYTHON312_SYNTAX_PASS')
    for p in [ROOT/'RUN_CURRENT_ROUND.sh',ROOT/'STATUS_CURRENT_ROUND.sh',ROOT/'RUN_RECOVER_ZERO_PAIR_ROUND.sh',ROOT/'RUN_RESUME_VERIFIED_POST.sh',ROOT/'RUN_SETTLE_CURRENT_POST.sh',ROOT/'RUN_RECOVER_CONTEXT_OVERFLOW_POST.sh']:
        r=subprocess.run(['bash','-n',str(p)],check=False)
        if r.returncode: raise RuntimeError('BASH_SYNTAX_FAILED:'+p.name)
    print('BASH_SYNTAX_PASS')
    env=dict(__import__('os').environ);env['PYTHONDONTWRITEBYTECODE']='1'
    r=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--tb=short'],cwd=ROOT,env=env,check=False)
    if r.returncode: raise RuntimeError('PACKAGE_PYTEST_FAILED:'+str(r.returncode))
    print('PAPER_CRITICAL_CAUSAL_ROUND_PACKAGE_VERIFY_PASS')
    return 0

if __name__=='__main__': raise SystemExit(main())
