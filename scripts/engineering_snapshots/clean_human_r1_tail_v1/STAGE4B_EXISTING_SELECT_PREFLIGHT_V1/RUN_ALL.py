#!/usr/bin/env python3
"""Verify package and run the offline SELECT continuation; no shell options."""
from pathlib import Path
import json
import os
import subprocess
import sys
import hashlib
HERE=Path(__file__).resolve().parent


def main():
    for line in (HERE/'PACKAGE_FILES.sha256').read_text().splitlines():
        digest,name=line.split('  ',1);path=HERE/name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('DELIVERY_HASH:'+name)
    config=json.loads((HERE/'current_request.json').read_bytes())
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',
        SELECT_TEST_REPO=config['repo'],
        SELECT_TEST_ASSET_ROOT=str(Path(config['helpers']['handoff']['path']).parent.parent))
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(HERE/'tests'),'-v'],cwd=HERE,env=env)
    if tests.returncode:return tests.returncode
    return subprocess.run([sys.executable,'-B',str(HERE/'run_preflight.py')],cwd=HERE,env=env).returncode


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('STOP='+type(exc).__name__+':'+str(exc),file=sys.stderr);raise SystemExit(21)
