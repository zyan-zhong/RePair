#!/usr/bin/env python3
from pathlib import Path
import json, os, subprocess, sys
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
from run_freeze import verify_delivery,dependencies
try:
    verify_delivery()
    cfg=json.loads((HERE/'current_request.json').read_bytes())
    dependencies(cfg)
    env=dict(os.environ,PYTHONPATH=str(Path(cfg['repo'])/'src'),PYTHONDONTWRITEBYTECODE='1')
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(HERE/'tests'),'-v'],cwd=HERE,env=env,check=False)
    if tests.returncode:raise SystemExit(tests.returncode)
    result=subprocess.run([sys.executable,'-B',str(HERE/'run_freeze.py'),*sys.argv[1:]],cwd=HERE,env=env,check=False)
    raise SystemExit(result.returncode)
except Exception as exc:
    print('STOP='+type(exc).__name__+':'+str(exc));raise SystemExit(21)
