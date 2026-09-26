
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

import os
import stat

import pytest

from pchsi.evaluation.gamefile_identity import (
    GamefileIdentityManifestV1,
    build_gamefile_identity_manifest,
)
from pchsi.evaluation.task_manifest import (
    FrozenTaskRecord,
    load_frozen_task_manifest,
)


def _records(tmp_path: Path) -> tuple[FrozenTaskRecord, ...]:
    manifest, digest, _ = write_manifest_fixture(tmp_path)
    return load_frozen_task_manifest(
        manifest_path=manifest,
        expected_sha256=digest,
        expected_record_count=2,
    )


def test_gamefile_identity_rejects_missing_symlink_and_sha1_mismatch(
    tmp_path: Path,
) -> None:
    records = _records(tmp_path / "missing")
    Path(records[0].gamefile).unlink()

    with pytest.raises(ValueError, match="regular file"):
        build_gamefile_identity_manifest(
            records=records,
            output_path=tmp_path / "missing.json",
        )

    records = _records(tmp_path / "mismatch")
    Path(records[0].gamefile).write_bytes(b"mutated\n")

    with pytest.raises(ValueError, match="SHA-1"):
        build_gamefile_identity_manifest(
            records=records,
            output_path=tmp_path / "mismatch.json",
        )

    records = _records(tmp_path / "symlink")
    original = Path(records[0].gamefile)
    target = original.with_name("real-game.tw-pddl")
    original.rename(target)
    original.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        build_gamefile_identity_manifest(
            records=records,
            output_path=tmp_path / "symlink.json",
        )


def test_fixture_builder_writes_exact_closed_manifest_no_clobber(
    tmp_path: Path,
) -> None:
    records = _records(tmp_path / "input")
    output = tmp_path / "out" / "identity.json"

    manifest = build_gamefile_identity_manifest(
        records=records,
        output_path=output,
    )

    assert isinstance(manifest, GamefileIdentityManifestV1)
    assert manifest.record_count == 2
    assert [item.index for item in manifest.records] == [0, 1]
    assert [item.task_id for item in manifest.records] == [
        record.task_id for record in records
    ]
    assert output.read_text(encoding="utf-8") == manifest.to_json()
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert GamefileIdentityManifestV1.from_json(
        output.read_bytes()
    ) == manifest

    with pytest.raises(FileExistsError):
        build_gamefile_identity_manifest(
            records=records,
            output_path=output,
        )
