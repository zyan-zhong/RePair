from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pchsi.round_control.clean_execution_binding import (
    bind_stage2c_official_schedule,
    build_clean_train_schedule,
    load_clean_train_pool_records,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_clean_train_pool_uses_global_task_indices_and_existing_scheduled_cell(tmp_path: Path) -> None:
    train = tmp_path / "train"
    root = train / "family" / "trial"
    root.mkdir(parents=True)
    game = root / "game.tw-pddl"
    traj = root / "traj_data.json"
    init = root / "initial_state.pddl"
    game.write_text("game\n", encoding="utf-8")
    traj.write_text("{}\n", encoding="utf-8")
    init.write_text("init\n", encoding="utf-8")
    row = {
        "schema_id": "ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1",
        "index": 17,
        "id": "alfworld_train_all3553_0017",
        "split": "train",
        "train_pool": "TRAIN_UPDATE",
        "task_type": "pick_and_place_simple",
        "gamefile_relpath": "family/trial/game.tw-pddl",
        "traj_file_relpath": "family/trial/traj_data.json",
        "initial_state_relpath": "family/trial/initial_state.pddl",
        "gamefile_sha1": hashlib.sha1(game.read_bytes()).hexdigest(),
        "gamefile_sha256": _sha(game),
        "traj_sha256": _sha(traj),
        "initial_state_sha256": _sha(init),
    }
    manifest = tmp_path / "update.jsonl"
    manifest.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
    records = load_clean_train_pool_records(
        manifest_path=manifest,
        expected_manifest_sha256=_sha(manifest),
        train_root=train,
        expected_pool="TRAIN_UPDATE",
        expected_count=1,
    )
    assert records[0].index == 17
    assert records[0].split == "train"
    schedule = build_clean_train_schedule(records=records, train_pool="TRAIN_UPDATE", seed=17)
    assert schedule[0].cell.scheduled_cell_id == "e1-t0017-s0000000017"
    assert schedule[0].scientific_cell_id == "clean-train-update-t0017-s0000000017"


def test_clean_train_pool_rejects_path_escape(tmp_path: Path) -> None:
    train = tmp_path / "train"
    train.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "game.tw-pddl").write_text("x")
    row = {
        "schema_id": "ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1",
        "index": 1,
        "id": "x",
        "split": "train",
        "train_pool": "TRAIN_UPDATE",
        "task_type": "x",
        "gamefile_relpath": "../outside/game.tw-pddl",
        "traj_file_relpath": "../outside/traj_data.json",
        "initial_state_relpath": "../outside/initial_state.pddl",
        "gamefile_sha1": "0" * 40,
        "gamefile_sha256": "0" * 64,
        "traj_sha256": "0" * 64,
        "initial_state_sha256": "0" * 64,
    }
    manifest = tmp_path / "bad.jsonl"
    manifest.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="escapes"):
        load_clean_train_pool_records(
            manifest_path=manifest,
            expected_manifest_sha256=_sha(manifest),
            train_root=train,
            expected_pool="TRAIN_UPDATE",
            expected_count=1,
        )


def test_stage2c_official_schedule_binds_existing_scheduled_cell(tmp_path: Path) -> None:
    from pchsi.evaluation.task_manifest import FrozenTaskRecord

    task = FrozenTaskRecord(
        index=0,
        task_id="seen-0",
        split="valid_seen",
        task_type="x",
        gamefile="/tmp/game",
        gamefile_sha1="1" * 40,
        root="/tmp",
        traj_file="/tmp/traj",
    )
    schedule = {
        "schema_id": "PI0_CLEAN_OFFICIAL_BENCHMARK_SCHEDULE_V1",
        "cells": [
            {
                "scientific_cell_id": "pi0-clean-valid-seen-t0000-s0000000017",
                "runtime_scheduled_cell_id": "e1-t0000-s0000000017",
                "execution_attempt_id": "e1-t0000-s0000000017-a000",
                "split": "valid_seen",
                "task_index": 0,
                "task_id": "seen-0",
                "seed": 17,
                "attempt_ordinal": 0,
            }
        ],
    }
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps(schedule, sort_keys=True) + "\n")
    bound = bind_stage2c_official_schedule(
        schedule_path=path,
        expected_schedule_sha256=_sha(path),
        records=(task,),
    )
    assert bound[0].split == "valid_seen"
    assert bound[0].cell.task_id == "seen-0"
