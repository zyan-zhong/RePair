from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pchsi.reference_loop.historical_bridge import (
    _validate_replay_qualification_context,
)


def test_replay_context_accepts_exact_authority_without_direct_bundle_sha(
    tmp_path: Path,
) -> None:
    path = tmp_path / "REPLAY_QUALIFICATION_MANIFEST.json"
    path.write_text(
        '{"schema_id":"REPLAY_QUALIFICATION_MANIFEST_V1",'
        '"schema_version":1,'
        '"registered_replay_sources":["source-a","source-b","source-c"]}\n',
        encoding="utf-8",
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    observed = _validate_replay_qualification_context(
        path,
        expected_sha256=digest,
    )

    assert observed["sha256"] == digest
    assert observed["role"] == (
        "DOWNSTREAM_REPLAY_QUALIFICATION_CONTEXT_NOT_DIRECT_SOURCE_LINEAGE"
    )


def test_replay_context_rejects_wrong_authority_sha(
    tmp_path: Path,
) -> None:
    path = tmp_path / "REPLAY_QUALIFICATION_MANIFEST.json"
    path.write_text('{"schema_id":"x"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="SHA mismatch"):
        _validate_replay_qualification_context(
            path,
            expected_sha256="0" * 64,
        )
