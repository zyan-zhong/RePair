from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/evaluation/run_e1_evaluator.py"


def _isolated(code: str):
    environment = os.environ.copy()
    environment["E1_CLI_PATH"] = str(SCRIPT)
    return subprocess.run(
        [sys.executable, "-S", "-c", code],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=environment,
    )


def test_module_import_describe_and_validate_do_not_import_runtime_packages() -> None:
    code = r'''
import os, runpy, sys
module = runpy.run_path(os.environ["E1_CLI_PATH"], run_name="candidate_cli")
for forbidden in ("alfworld", "textworld", "gym", "vllm", "torch"):
    assert forbidden not in sys.modules, forbidden
assert module["main"](["--describe"]) == 0
for forbidden in ("alfworld", "textworld", "gym", "vllm", "torch"):
    assert forbidden not in sys.modules, forbidden
print("TASK13_SAFE_IMPORT_OK")
'''
    result = _isolated(code)
    assert result.returncode == 0, result.stderr
    assert "TASK13_SAFE_IMPORT_OK" in result.stdout


def test_module_import_describe_and_validate_do_not_open_socket_or_initialize_cuda() -> None:
    code = r'''
import os, runpy, socket
class ForbiddenSocket:
    def __init__(self, *args, **kwargs):
        raise AssertionError("socket opened")
socket.socket = ForbiddenSocket
module = runpy.run_path(os.environ["E1_CLI_PATH"], run_name="candidate_cli")
assert module["main"](["--describe"]) == 0
print("TASK13_NO_SOCKET_OR_CUDA_OK")
'''
    result = _isolated(code)
    assert result.returncode == 0, result.stderr
    assert "TASK13_NO_SOCKET_OR_CUDA_OK" in result.stdout
