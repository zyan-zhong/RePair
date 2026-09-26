from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pchsi.reference_loop.identity import ArtifactRegistrationV1, _artifact_digest
from pchsi.reference_loop.identity_review import _manifest_value_candidate


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return path


def test_manifest_value_artifact_uses_bundle_sha_not_manifest_file_sha(
    tmp_path: Path,
) -> None:
    manifest = _write_json(
        tmp_path / "model_artifact_manifest.json",
        {
            "weights_bundle_sha256": "a" * 64,
            "tokenizer_bundle_sha256": "b" * 64,
        },
    )
    base = ArtifactRegistrationV1(
        name="base_model_artifact",
        kind="MANIFEST_VALUE_SHA256",
        path=str(manifest),
        expected_sha256="a" * 64,
    )
    tok = ArtifactRegistrationV1(
        name="tokenizer_artifact",
        kind="MANIFEST_VALUE_SHA256",
        path=str(manifest),
        expected_sha256="b" * 64,
    )
    _, base_sha = _artifact_digest(base)
    _, tok_sha = _artifact_digest(tok)
    assert base_sha == "a" * 64
    assert tok_sha == "b" * 64
    assert base_sha != tok_sha
    assert base_sha != hashlib.sha256(manifest.read_bytes()).hexdigest()


def test_manifest_value_artifact_rejects_wrong_bundle_sha(
    tmp_path: Path,
) -> None:
    manifest = _write_json(
        tmp_path / "model_artifact_manifest.json",
        {
            "weights_bundle_sha256": "a" * 64,
            "tokenizer_bundle_sha256": "b" * 64,
        },
    )
    item = ArtifactRegistrationV1(
        name="base_model_artifact",
        kind="MANIFEST_VALUE_SHA256",
        path=str(manifest),
        expected_sha256="c" * 64,
    )
    with pytest.raises(ValueError, match="manifest bundle SHA mismatch"):
        _artifact_digest(item)


def test_review_manifest_value_candidate_preserves_semantic_bundle_sha(
    tmp_path: Path,
) -> None:
    manifest = _write_json(
        tmp_path / "model_artifact_manifest.json",
        {"weights_bundle_sha256": "a" * 64},
    )
    row = _manifest_value_candidate(
        slot="base_model_artifact",
        path=manifest,
        field_name="weights_bundle_sha256",
        source_authority_path=manifest,
        source_json_path="$.weights_bundle_sha256",
        reason="TEST",
    )
    assert row["kind"] == "MANIFEST_VALUE_SHA256"
    assert row["sha256"] == "a" * 64
