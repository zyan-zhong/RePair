from __future__ import annotations

from pathlib import Path

import pytest

from pchsi.reference_loop.bundle_reader import validate_attempt_bundle

from ._helpers import write_bundle


def test_bundle_reader_revalidates_exact_five_file_bundle(
    tmp_path: Path,
) -> None:
    root = write_bundle(tmp_path / "bundle")
    validated = validate_attempt_bundle(root)

    assert validated.alignment_census["status"] == "VALIDATED"
    assert validated.alignment_census["policy_call_count"] == 1
    assert validated.alignment_census["action_trace_count"] == 1
    assert validated.alignment_census["public_transition_count"] == 0
    assert len(validated.attempt_bundle_sha256) == 64


def test_bundle_reader_rejects_missing_policy_calls(tmp_path: Path) -> None:
    root = write_bundle(tmp_path / "bundle")
    (root / "policy_calls.jsonl").unlink()

    with pytest.raises(ValueError, match="exactly five files"):
        validate_attempt_bundle(root)


def test_bundle_reader_rejects_exact_byte_tampering(tmp_path: Path) -> None:
    root = write_bundle(tmp_path / "bundle")
    path = root / "action_traces.jsonl"
    path.write_bytes(path.read_bytes() + b" \n")

    with pytest.raises(ValueError):
        validate_attempt_bundle(root)


def test_bundle_reader_rejects_symlinked_source(tmp_path: Path) -> None:
    root = write_bundle(tmp_path / "bundle")
    path = root / "attempt.json"
    original = path.read_bytes()
    target = tmp_path / "attempt-copy.json"
    target.write_bytes(original)
    path.unlink()
    path.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        validate_attempt_bundle(root)
