from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SPLIT_PATH = (
    REPO_ROOT / "configs/protocols/split_and_access_v1.json"
)
RAW_PATH = REPO_ROOT / "configs/protocols/raw_with_menu_v1.json"
MANIFEST_PATH = (
    REPO_ROOT
    / "data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl"
)


def test_split_and_access_v1_is_frozen_without_execution_approval() -> None:
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))

    assert split["protocol_id"] == "SPLIT_AND_ACCESS_V1"
    assert split["status"] == (
        "frozen_pending_evaluator_and_execution_approval"
    )
    assert split["access_mode"] == "TRUSTED_MANIFEST_DIRECT_V1"

    task_manifest = split["task_manifest"]
    assert task_manifest == {
        "deduplication_allowed": False,
        "manifest_id": "ALFWORLD_STRICT_VALID_UNSEEN_ALL134_V1",
        "path": (
            "data/manifests/"
            "alfworld_strict_valid_unseen_all134_v1.jsonl"
        ),
        "path_binding": (
            "server_local_absolute_gamefile_paths"
        ),
        "preserve_order": True,
        "records": 134,
        "relocation_requires_regeneration_and_refreeze": True,
        "sha256": (
            "6e480bb663a6f17207aa2c7a6e1b504a"
            "dad8448f6e8a2615c5e62fea0b64c0f4"
        ),
        "substitution_allowed": False,
        "unique_tasks": 134,
    }

    assert raw["task_manifest"] == {
        "controls_menu_exposure": False,
        "manifest_id": task_manifest["manifest_id"],
        "path": task_manifest["path"],
        "records": 134,
        "sha256": task_manifest["sha256"],
        "unique_tasks": 134,
    }

    governance = raw["governance"]
    assert raw["status"] == (
        "split_and_access_v1_frozen_pending_execution_approval"
    )
    assert governance["current_status"] == raw["status"]
    assert governance["current_facts"]["split_and_access_v1"] == "frozen"
    assert (
        governance["current_facts"]["split_and_access_v1_record"]
        == split
    )

    assert governance["current_facts"]["alfworld_evaluator"] == (
        "not_implemented"
    )
    assert governance["current_facts"]["e1_dev_execution"] == (
        "not_approved"
    )
    assert governance["current_facts"][
        "e1_confirmatory_execution"
    ] == "not_approved"

    s1 = governance["current_facts"]["s1_backend_probe"]
    assert s1["backend_probe_execution"] == "not_approved"
    assert s1["read_only_inventory_execution"] == "not_approved"


def test_frozen_manifest_has_exact_ordered_134_records() -> None:
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in MANIFEST_PATH.read_text(
            encoding="utf-8"
        ).splitlines()
        if line
    ]

    assert len(rows) == split["task_manifest"]["records"] == 134
    assert [row["index"] for row in rows] == list(range(134))
    assert [row["id"] for row in rows] == [
        f"alfworld_valid_unseen_all134_{index:04d}"
        for index in range(134)
    ]
    assert len({row["gamefile"] for row in rows}) == 134
    assert {row["split"] for row in rows} == {"valid_unseen"}


def test_portable_split_record_contains_no_absolute_paths() -> None:
    split_text = SPLIT_PATH.read_text(encoding="utf-8")

    assert "/data/" not in split_text
    assert "/home/" not in split_text
    assert "resolved_inode" not in split_text
    assert "resolved_mount_id" not in split_text
    assert "resolved_device" not in split_text


def test_frozen_manifest_hash_and_host_binding_are_explicit() -> None:
    import hashlib

    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    task_manifest = split["task_manifest"]
    rows = [
        json.loads(line)
        for line in MANIFEST_PATH.read_text(
            encoding="utf-8"
        ).splitlines()
        if line
    ]

    assert hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest() == (
        task_manifest["sha256"]
    )
    assert task_manifest["path_binding"] == (
        "server_local_absolute_gamefile_paths"
    )
    assert task_manifest[
        "relocation_requires_regeneration_and_refreeze"
    ] is True
    assert all(Path(row["gamefile"]).is_absolute() for row in rows)
