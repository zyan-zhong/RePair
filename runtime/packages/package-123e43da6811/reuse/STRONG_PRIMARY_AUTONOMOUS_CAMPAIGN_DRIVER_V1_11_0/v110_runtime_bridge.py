from __future__ import annotations
import json,subprocess,sys
from pathlib import Path

RESULT='CLEAN_REFERENCE_F0F1_RESULT_PACKAGE_V1.json'
TERMINAL='FINAL_TERMINAL_V2.json'
BINDING='ACCEPTED_PRE_BINDING_V3.json'


def verifier_files_ready(upstream_root:Path)->bool:
    root=Path(upstream_root)/'verifier'
    return all((root/x).is_file() and not (root/x).is_symlink() for x in (RESULT,TERMINAL,BINDING))


def load_verifier_gate(*,v110_package_root:Path,upstream_root:Path)->dict[str,object]:
    pkg=Path(v110_package_root).resolve(); up=Path(upstream_root).resolve(); root=up/'verifier'
    if not (pkg/'receipt_gate.py').is_file(): raise ValueError('V110_RECEIPT_GATE_MISSING')
    if not verifier_files_ready(up): raise ValueError('VERIFIER_RECEIPTS_NOT_READY')
    code='''import json,sys\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom receipt_gate import validate_verifier_receipts\nx=validate_verifier_receipts(Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4]))\nprint(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")))\n'''
    cp=subprocess.run([sys.executable,'-c',code,str(pkg),str(root/RESULT),str(root/TERMINAL),str(root/BINDING)],cwd=str(pkg),capture_output=True,text=True,check=False,shell=False)
    if cp.returncode!=0: raise ValueError('V110_VERIFIER_GATE_REJECTED:'+cp.stderr.strip()[-2000:])
    lines=[x for x in cp.stdout.splitlines() if x.strip()]
    if len(lines)!=1: raise ValueError('V110_VERIFIER_GATE_OUTPUT_INVALID')
    value=json.loads(lines[0])
    if not isinstance(value,dict) or value.get('schema_id')!='STRONG_PRIMARY_R1_VERIFIER_RECEIPT_GATE_V1':
        raise ValueError('V110_VERIFIER_GATE_SCHEMA_MISMATCH')
    return value


def run_v110_post_once(*,v110_package_root:Path,upstream_root:Path,closure_root:Path,prepared_root:Path,repo:Path)->int:
    worker=Path(v110_package_root).resolve()/'post_worker.sh'
    if not worker.is_file() or worker.is_symlink(): raise ValueError('V110_POST_WORKER_MISSING')
    cp=subprocess.run([str(worker),'--upstream-root',str(Path(upstream_root).resolve()),'--closure-root',str(Path(closure_root).resolve()),'--prepared-root',str(Path(prepared_root).resolve()),'--repo',str(Path(repo).resolve())],check=False,shell=False)
    return int(cp.returncode)
