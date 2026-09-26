
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def write_manifest_fixture(
    tmp_path: Path,
    *,
    count: int = 2,
) -> tuple[Path, str, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []

    for index in range(count):
        source_task_id = f"trial_fixture_{index:04d}"
        task_root = (
            tmp_path
            / "valid_unseen"
            / "pick_and_place_simple-fixture"
            / source_task_id
        )
        task_root.mkdir(parents=True)

        gamefile = task_root / "game.tw-pddl"
        gamefile.write_bytes(
            f"fixture-game-{index}\n".encode("utf-8")
        )
        traj_file = task_root / "traj_data.json"
        traj_file.write_text("{}\n", encoding="utf-8")

        rows.append(
            {
                "gamefile": str(gamefile.resolve()),
                "gamefile_sha1": hashlib.sha1(
                    gamefile.read_bytes()
                ).hexdigest(),
                "id": (
                    "alfworld_valid_unseen_all134_"
                    f"{index:04d}"
                ),
                "index": index,
                "root": str(task_root.resolve()),
                "split": "valid_unseen",
                "task_id": source_task_id,
                "task_type": "pick_and_place_simple",
                "traj_file": str(traj_file.resolve()),
            }
        )

    manifest = tmp_path / "manifest.jsonl"
    payload = "".join(
        json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for row in rows
    ).encode("utf-8")
    manifest.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    return manifest, digest, rows

import pytest

from pchsi.evaluation.task_manifest import (
    FrozenTaskRecord,
    load_frozen_task_manifest,
)


def test_manifest_loader_preserves_exact_order_and_134_identity(
    tmp_path: Path,
) -> None:
    manifest, digest, rows = write_manifest_fixture(tmp_path)

    records = load_frozen_task_manifest(
        manifest_path=manifest,
        expected_sha256=digest,
        expected_record_count=2,
    )

    assert isinstance(records, tuple)
    assert [record.index for record in records] == [0, 1]
    assert [record.task_id for record in records] == [
        "alfworld_valid_unseen_all134_0000",
        "alfworld_valid_unseen_all134_0001",
    ]
    assert [record.gamefile for record in records] == [
        row["gamefile"] for row in rows
    ]
    assert all(
        isinstance(record, FrozenTaskRecord)
        for record in records
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("index", "index"),
        ("id", "ID"),
        ("split", "valid_unseen"),
        ("duplicate_gamefile", "duplicate"),
        ("unknown", "fields"),
    ],
)
def test_manifest_loader_rejects_hash_count_index_id_split_and_duplicate_errors(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    manifest, _, rows = write_manifest_fixture(tmp_path)

    if mutation == "index":
        rows[1]["index"] = 7
    elif mutation == "id":
        rows[1]["id"] = "wrong"
    elif mutation == "split":
        rows[1]["split"] = "valid_seen"
    elif mutation == "duplicate_gamefile":
        rows[1]["gamefile"] = rows[0]["gamefile"]
    elif mutation == "unknown":
        rows[1]["unknown"] = True
    else:
        raise AssertionError(mutation)

    payload = "".join(
        json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for row in rows
    ).encode("utf-8")
    manifest.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()

    with pytest.raises(ValueError, match=message):
        load_frozen_task_manifest(
            manifest_path=manifest,
            expected_sha256=digest,
            expected_record_count=2,
        )

    with pytest.raises(ValueError, match="SHA-256"):
        load_frozen_task_manifest(
            manifest_path=manifest,
            expected_sha256="0" * 64,
            expected_record_count=2,
        )

    with pytest.raises(ValueError, match="record count"):
        load_frozen_task_manifest(
            manifest_path=manifest,
            expected_sha256=digest,
            expected_record_count=3,
        )


def test_manifest_loader_rejects_symlinked_manifest(
    tmp_path: Path,
) -> None:
    manifest, digest, _ = write_manifest_fixture(tmp_path)
    link = tmp_path / "manifest-link.jsonl"
    link.symlink_to(manifest)

    with pytest.raises(ValueError, match="symlink"):
        load_frozen_task_manifest(
            manifest_path=link,
            expected_sha256=digest,
            expected_record_count=2,
        )
