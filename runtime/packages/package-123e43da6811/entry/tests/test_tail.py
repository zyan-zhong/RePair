"""Fixture tests; no provider, training, server, or live promotion authority."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
NATIVE = ROOT/'work/v17/native_bba_full'


def test_actual_memory_producer_through_no_train_close_and_next_request(tmp_path):
    code = (
        'import sys, os, runpy\n'
        f'sys.path.insert(0, {str(ROOT / "work/v17")!r})\n'
        f'os.chdir({str(NATIVE)!r})\n'
        'from memory_binding.source_overlay import install_memory_overlay\n'
        f'install_memory_overlay({str(NATIVE)!r})\n'
        f'runpy.run_path({str(Path(__file__).with_name("native_tail_case.py"))!r}, '
        f'init_globals={{"case_root":{str(tmp_path)!r}}})\n'
    )
    result = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
