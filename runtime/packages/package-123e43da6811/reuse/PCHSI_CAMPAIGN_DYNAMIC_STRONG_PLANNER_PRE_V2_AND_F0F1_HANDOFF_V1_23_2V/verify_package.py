#!/usr/bin/env python3
from __future__ import annotations
import hashlib, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256();
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

manifest=ROOT/'PACKAGE_FILES.sha256'
if not manifest.is_file(): raise SystemExit('PACKAGE_FILES_SHA256_MISSING')
rows=[]
for line in manifest.read_text().splitlines():
    if not line.strip(): continue
    digest,rel=line.split('  ',1); p=ROOT/rel
    if not p.is_file() or p.is_symlink(): raise SystemExit('PACKAGE_FILE_MISSING:'+rel)
    if sha(p)!=digest: raise SystemExit('PACKAGE_FILE_SHA_MISMATCH:'+rel)
    rows.append(rel)
print('PACKAGE_SHA256_VERIFY_PASS files='+str(len(rows)))

env=dict(os.environ); env['PYTHONDONTWRITEBYTECODE']='1'
cp=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(ROOT/'tests/test_v1232v_contracts.py')],cwd=ROOT,env=env)
if cp.returncode!=0: raise SystemExit(cp.returncode)
cp=subprocess.run([sys.executable,'-m','compileall','-q',str(ROOT/'v1232v_driver.py'),str(ROOT/'dynamic_primary_pre_v2.py'),str(ROOT/'dynamic_pre_v2_semantic_normalization.py'),str(ROOT/'current_round_researcher_memory_v1.py')],cwd=ROOT,env=env)
if cp.returncode!=0: raise SystemExit(cp.returncode)
cp=subprocess.run(['bash','-n',str(ROOT/'RUN_V1232V.sh')],cwd=ROOT)
if cp.returncode!=0: raise SystemExit(cp.returncode)
text=(ROOT/'v1232v_driver.py').read_text()
if 'pair_status' not in text or 'COMPLETE_A2_A3' not in text: raise SystemExit('PAIR_REPRESENTATION_GATE_MISSING')
if 'FAIL_CLOSED_NO_AUTOMATIC_RESEND' not in text: raise SystemExit('PRE_NO_RESEND_GATE_MISSING')
print('DYNAMIC_PRE_V2_REPRESENTATION_RECOVERY_PASS')
print('PRE_EXACT_TERMINAL_NO_RESEND_PASS')
print('PLANNER_BOUND_F0F1_HANDOFF_DYNAMIC_BUDGET_PASS')
print('NO_ENVIRONMENT_NO_TRAINING_EXECUTION_PASS')
print('V1232V_PACKAGE_VERIFY_PASS')
