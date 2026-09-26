from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE = REPO_ROOT / "native" / "s1_backend_probe"
BINARY = NATIVE / "build" / "pchsi-s1-backend-probe"


def _build_digest() -> str:
    result = subprocess.run(
        ["make", "-C", str(NATIVE), "clean", "all"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        env={
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
            "SOURCE_DATE_EPOCH": "1700000000",
        },
    )
    assert result.returncode == 0, result.stderr
    return hashlib.sha256(BINARY.read_bytes()).hexdigest()


def test_two_clean_native_builds_are_identical() -> None:
    assert _build_digest() == _build_digest()
