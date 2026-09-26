from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pchsi.reference_loop.identity import (
    ArtifactRegistrationV1,
    _artifact_digest,
)
from pchsi.reference_loop.identity_review import (
    _adapter_artifact_candidate_from_census,
)


ADAPTER_BUNDLE_SHA = (
    "b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace"
)


def _member_metadata(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def test_adapter_manifest_value_digest_matches_frozen_adapter_bundle(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "adapter_artifact_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_id": "P4_R1_Q2_BAD_ADAPTER_ARTIFACT_MANIFEST_V1",
                "schema_version": 1,
                "adapter_bundle_sha256": ADAPTER_BUNDLE_SHA,
                "required_files": [
                    "adapter_config.json",
                    "adapter_model.safetensors",
                ],
                "files": {},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    registration = ArtifactRegistrationV1(
        name="adapter_artifact",
        kind="MANIFEST_VALUE_SHA256",
        path=str(manifest),
        expected_sha256=ADAPTER_BUNDLE_SHA,
    )

    resolved, digest = _artifact_digest(registration)

    assert resolved == str(manifest.resolve())
    assert digest == ADAPTER_BUNDLE_SHA


def test_adapter_review_candidate_uses_bundle_sha_not_directory_digest(
    tmp_path: Path,
) -> None:
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()

    config = adapter_dir / "adapter_config.json"
    model = adapter_dir / "adapter_model.safetensors"
    config.write_text("{}\n", encoding="utf-8")
    model.write_bytes(b"weights")

    manifest = tmp_path / "adapter_artifact_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_id": "P4_R1_Q2_BAD_ADAPTER_ARTIFACT_MANIFEST_V1",
                "schema_version": 1,
                "adapter_bundle_sha256": ADAPTER_BUNDLE_SHA,
                "required_files": [
                    "adapter_config.json",
                    "adapter_model.safetensors",
                ],
                "files": {
                    "adapter_config.json": _member_metadata(config),
                    "adapter_model.safetensors": _member_metadata(model),
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    census = {
        "seed17_adapter_directory": str(adapter_dir),
        "frozen_checkpoint_files": [
            {
                "relative_path": "seed_17/adapter_artifact_manifest.json",
                "path": str(manifest),
            }
        ],
    }

    candidate = _adapter_artifact_candidate_from_census(census)

    assert candidate["kind"] == "MANIFEST_VALUE_SHA256"
    assert candidate["sha256"] == ADAPTER_BUNDLE_SHA
    assert candidate["path"] == str(manifest.resolve())
    assert candidate["manifest_value_field"] == "adapter_bundle_sha256"
