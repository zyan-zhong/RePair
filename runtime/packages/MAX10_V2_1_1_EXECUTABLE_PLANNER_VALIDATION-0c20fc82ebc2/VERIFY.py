from pathlib import Path
import subprocess,sys
from entry_v208 import verify
identity=verify()
r=subprocess.run([sys.executable,'-m','pytest','tests','-q','-p','no:cacheprovider','--rootdir=.'],cwd=Path(__file__).resolve().parent)
print('PACKAGE_MANIFEST_SHA256='+identity,flush=True)
print('SCIENTIFIC_EXECUTION_STARTED=false',flush=True)
raise SystemExit(r.returncode)
