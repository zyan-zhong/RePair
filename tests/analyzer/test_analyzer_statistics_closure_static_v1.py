from pathlib import Path
import subprocess,sys
def test_statistics_static_audit():
 script=Path("scripts/analyzer/audit_analyzer_statistics_closure_v1.py"); assert script.is_file(); subprocess.run([sys.executable,str(script),"--repo-root","."],check=True)
