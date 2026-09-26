from pathlib import Path
import argparse,json,subprocess,sys
from seed_recovery import verify_root,ref
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--registered-tests',action='store_true');args=p.parse_args()
verify_root(root,ref(root/'PACKAGE_FILES.sha256')['sha256'])
for name in ('RECOVER.py','seed_recovery.py'):compile((root/name).read_bytes(),name,'exec')
if args.registered_tests:
 a=json.loads((root/'RECOVERY_AUTHORITY.json').read_bytes());old=Path(a['promotion_package']['root'])
 verify_root(old,a['promotion_package']['manifest_sha256'])
 result=subprocess.run([sys.executable,'-B','-m','pytest','-q',str(old/'test_metric.py'),str(old/'test_integration.py'),str(old/'test_parent_cache.py'),'-p','no:cacheprovider'],cwd=old)
 if result.returncode:raise SystemExit(result.returncode)
print('SINGLE_SEED_RECOVERY_PACKAGE_SHA_PASS; NO_MODEL_EPISODES_OR_SUBMISSION')
