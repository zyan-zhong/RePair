import subprocess,sys
from resume_entry import verify,ROOT
verify()
raise SystemExit(subprocess.run([sys.executable,'-B','-m','pytest',str(ROOT/'test_transport_scope.py'),str(ROOT/'test_group_recovery.py'),'-q','-p','no:cacheprovider']).returncode)
