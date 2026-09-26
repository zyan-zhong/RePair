"""Native PRE integration fixture: no provider, GPU, environment or training."""
from pathlib import Path
import subprocess
import sys

WORK = Path(__file__).resolve().parents[3]


def test_live_pre_uses_native_renderer_finalizer_and_one_logical_call(tmp_path):
    script = Path(__file__).with_name('live_pre_fixture.py')
    result = subprocess.run([sys.executable, '-B', str(script), str(WORK), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'NATIVE_PRE_SAME_CALL_CAPTURE_PASS' in result.stdout
