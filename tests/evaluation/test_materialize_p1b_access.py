from importlib.util import (
    module_from_spec,
    spec_from_file_location,
)
import json
from pathlib import Path

import pytest


def _load_materializer_module():
    path = Path(
        "scripts/evaluation/materialize_p1b_access.py"
    )
    spec = spec_from_file_location(
        "materialize_p1b_access_under_test",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_materializer_rejects_legacy_result_fields(
    tmp_path,
):
    module = _load_materializer_module()
    payload_path = tmp_path / "legacy_identities.json"
    payload_path.write_text(
        json.dumps(
            [
                {
                    "legacy_source": "legacy-repo",
                    "legacy_task_id": "task-0",
                    "legacy_gamefile": None,
                    "legacy_gamefile_sha1": None,
                    "current_manifest_index": 0,
                    "evidence_source": "legacy:0",
                    "manual_same_gamefile_confirmed": False,
                    "success": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="forbidden result fields",
    ):
        module._strict_object_list(payload_path)


def test_materializer_is_offline_by_static_contract():
    text = Path(
        "scripts/evaluation/materialize_p1b_access.py"
    ).read_text(encoding="utf-8")

    for token in (
        "alfworld",
        "vllm",
        "requests",
        "httpx",
        "anthropic",
        "openai",
    ):
        assert f"import {token}" not in text
        assert f"from {token}" not in text


def test_materializer_rejects_nonfrozen_manifest_hash():
    module = _load_materializer_module()
    manifest_path = Path(
        "data/manifests/"
        "alfworld_strict_valid_unseen_all134_v1.jsonl"
    )

    with pytest.raises(
        ValueError,
        match="frozen strict-134 identity",
    ):
        module._validate_frozen_manifest_input(
            manifest_path=manifest_path,
            manifest_sha256="0" * 64,
        )


def test_materializer_rejects_nonfrozen_manifest_path(
    tmp_path,
):
    module = _load_materializer_module()
    other = tmp_path / "other.jsonl"
    other.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="frozen strict-134 manifest",
    ):
        module._validate_frozen_manifest_input(
            manifest_path=other,
            manifest_sha256=(
                module._FROZEN_TASK_MANIFEST_SHA256
            ),
        )
