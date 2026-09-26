from pathlib import Path
import subprocess,sys

def test_fixed_head_hardening_static_audit():
    script=Path("scripts/analyzer/audit_analyzer_v2_fixed_head_hardening_v1.py")
    assert script.is_file()
    subprocess.run([sys.executable,str(script),"--repo-root","."],check=True)
