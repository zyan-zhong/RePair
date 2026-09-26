from pathlib import Path
import subprocess,sys
def test_final_static_audit():
 subprocess.run([sys.executable,"scripts/analyzer/audit_outcome_aware_analyzer_v2.py",
  "--repo-root","."],check=True)
