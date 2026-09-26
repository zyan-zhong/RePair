from pathlib import Path
import ast,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=ROOT/'PACKAGE_FILES.sha256'
rows=manifest.read_text().splitlines()
for line in rows:
    h,name=line.split('  ',1); p=ROOT/name
    if not p.is_file() or sha(p)!=h: raise SystemExit('PACKAGE_SHA256_MISMATCH:'+name)
print('PACKAGE_SHA256_VERIFY_PASS files='+str(len(rows)))
ast.parse((ROOT/'v1232u_driver.py').read_text()); ast.parse((ROOT/'source_context_equivalence.py').read_text())
cp=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(ROOT/'tests')])
if cp.returncode: raise SystemExit(cp.returncode)
print('T_G_TERMINAL_ADOPTION_NO_REEXECUTION_PASS')
print('GROUP_RECORD_STAGE_KEY_SCHEMA_RECOVERY_PASS')
print('HISTORICAL_STAGE6J_MISSINGNESS_GOVERNANCE_PASS')
print('CPX_DYNAMIC_PAIR_UNIVERSE_CONTINUATION_PASS')
print('V1232U_PACKAGE_VERIFY_PASS')
