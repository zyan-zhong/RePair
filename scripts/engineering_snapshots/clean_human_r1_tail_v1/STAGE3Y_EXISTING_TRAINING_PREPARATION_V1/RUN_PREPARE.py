#!/usr/bin/env python3
"""Subprocess-only launcher; never modifies the caller's shell options."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
HERE=Path(__file__).resolve().parent

def main():
    for line in (HERE/'PACKAGE_FILES.sha256').read_text().splitlines():
        h,n=line.split('  ',1);r=Path(n)
        if r.is_absolute() or '..' in r.parts:raise ValueError('INVALID_PACKAGE_MEMBER')
        p=HERE/r
        if any(x.is_symlink() for x in (p,*p.parents)) or hashlib.sha256(p.read_bytes()).hexdigest()!=h:
            raise ValueError('PACKAGE_MEMBER_CHANGED:'+n)
    cfg=json.loads((HERE/'current_round.json').read_text())
    env=dict(os.environ,PYTHONPATH=str(Path(cfg['repo'])/'src'),PYTHONDONTWRITEBYTECODE='1')
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(HERE/'tests'),'-v'],cwd=HERE,env=env,check=False)
    if tests.returncode:return tests.returncode
    return subprocess.run([sys.executable,'-B',str(HERE/'prepare.py')],cwd=HERE,env=env,check=False).returncode

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('STOP='+type(exc).__name__+':'+str(exc),file=sys.stderr);raise SystemExit(21)
