from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT
    / "scripts/evaluation/build_e1_gamefile_sha256_manifest.py"
)


def test_builder_has_no_formal_manifest_default() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "alfworld_strict_valid_unseen_all134_v1.jsonl" not in text

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "--task-manifest" in result.stdout
    assert "--expected-manifest-sha256" in result.stdout
    assert "--output" in result.stdout
