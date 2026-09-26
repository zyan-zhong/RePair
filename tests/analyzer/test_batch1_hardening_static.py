from pathlib import Path
import subprocess, sys


def test_static_hardening_audit_exists_and_passes() -> None:
    script=Path("scripts/analyzer/audit_analyzer_batch1_hardening_v1.py")
    assert script.is_file(), "audit_analyzer_batch1_hardening_v1.py"
    subprocess.run(
        [sys.executable,str(script),"--repo-root","."],check=True
    )
