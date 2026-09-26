from pathlib import Path
import hashlib, subprocess, sys, os
P=Path(__file__).resolve().parent
lines=[x for x in (P/'PACKAGE_FILES.sha256').read_text().splitlines() if x.strip()]
for line in lines:
 h,n=line.split('  ',1); p=P/n
 if hashlib.sha256(p.read_bytes()).hexdigest()!=h: raise SystemExit('PACKAGE_SHA256_VERIFY_FAIL:'+n)
print('PACKAGE_SHA256_VERIFY_PASS files='+str(len(lines)))
env=dict(os.environ); env['PYTHONDONTWRITEBYTECODE']='1'
rc=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(P/'tests')],env=env).returncode
if rc: raise SystemExit(rc)
print('Q_TERMINAL_HARD_STOP_ISOLATION_PASS')
print('COMPLETE_PAIR_ADOPTION_NO_RETRY_NO_TOPUP_PASS')
print('CANONICAL_ACT3_GROUP_PREP_REUSE_PASS')
print('NO_STRONG_LOCAL_CALL_REEXECUTION_PASS')
print('V1232R1_PACKAGE_VERIFY_PASS')
