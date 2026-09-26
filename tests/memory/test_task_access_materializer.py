"""Synthetic RED/GREEN tests for the task-access filesystem materializer."""

from __future__ import annotations

import hashlib
from importlib import import_module, util
import json
import os
from pathlib import Path
import stat
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/memory/materialize_task_access_v1.py"


def _task_access():
    return import_module("pchsi.memory.task_access")


def _materializer():
    assert SCRIPT_PATH.is_file(), "materializer script missing"
    spec = util.spec_from_file_location(
        "pchsi_task_access_materializer_test_target",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


def _write_game(
    root: Path,
    *,
    split: str,
    task_directory: str,
    trial_id: str,
    payload: bytes,
) -> Path:
    trial = root / split / task_directory / trial_id
    trial.mkdir(parents=True, exist_ok=True)
    game = trial / "game.tw-pddl"
    game.write_bytes(payload)
    # This file deliberately contains semantic-looking content that the
    # materializer must never read.
    trajectory = trial / "traj_data.json"
    trajectory.write_text(
        '{"task_desc":"DO_NOT_READ_SECRET_GOAL"}',
        encoding="utf-8",
    )
    return game


def _synthetic_dataset(root: Path) -> Path:
    for split in ("train", "valid_seen", "valid_unseen"):
        (root / split).mkdir(parents=True, exist_ok=True)

    train_specs = (
        (
            "pick_and_place_simple-Apple-None-Fridge-1",
            "trial_train_a1",
            b"TRAIN-A1\xff",
        ),
        (
            "pick_and_place_simple-Mug-None-Cabinet-2",
            "trial_train_a2",
            b"TRAIN-A2\xfe",
        ),
        (
            "pick_and_place_simple-Book-None-Desk-3",
            "trial_train_a3",
            b"TRAIN-A3\xfd",
        ),
        (
            "look_at_obj_in_light-KeyChain-None-DeskLamp-4",
            "trial_train_b1",
            b"TRAIN-B1\xfc",
        ),
        (
            "look_at_obj_in_light-Box-None-FloorLamp-5",
            "trial_train_b2",
            b"TRAIN-B2\xfb",
        ),
        (
            "look_at_obj_in_light-AlarmClock-None-DeskLamp-6",
            "trial_train_b3",
            b"TRAIN-B3\xfa",
        ),
    )
    for task_directory, trial_id, payload in train_specs:
        _write_game(
            root,
            split="train",
            task_directory=task_directory,
            trial_id=trial_id,
            payload=payload,
        )

    _write_game(
        root,
        split="valid_seen",
        task_directory=(
            "pick_cool_then_place_in_recep-"
            "Tomato-None-GarbageCan-7"
        ),
        trial_id="trial_seen_secret",
        payload=b"SEEN-SECRET\x80",
    )
    _write_game(
        root,
        split="valid_unseen",
        task_directory=(
            "pick_two_obj_and_place-"
            "Spatula-None-Drawer-8"
        ),
        trial_id="trial_unseen_secret",
        payload=b"UNSEEN-SECRET\x81",
    )
    return root


def _task_type_from_directory(name: str) -> str:
    for prefix in (
        "pick_and_place_simple",
        "look_at_obj_in_light",
        "pick_clean_then_place_in_recep",
        "pick_heat_then_place_in_recep",
        "pick_cool_then_place_in_recep",
        "pick_two_obj_and_place",
    ):
        if name.startswith(prefix + "-"):
            return prefix
    raise AssertionError(name)


def _role_payload(task_access, access_class):
    if access_class is task_access.MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE:
        return dict(
            historical_exposure_class="NO_REGISTERED_ROUND1_EXPOSURE",
            historically_exposed=False,
            benchmark_role="TRAIN_MEMORY_SOURCE",
            allowed_prefreeze_uses=("MEMORY_SOURCE_DEVELOPMENT",),
            writeback_policy="ACTIVE_MEMORY_SOURCE_ALLOWED",
            method_selection_allowed=True,
            formal_active_memory_source_allowed=True,
            final_evaluation_allowed_after_method_freeze=False,
            clean_confirmation=False,
            fresh_ood_claim_allowed=False,
            shadow_readback_during_formal_evaluation=False,
        )
    if access_class is task_access.MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV:
        return dict(
            historical_exposure_class="NO_REGISTERED_ROUND1_EXPOSURE",
            historically_exposed=False,
            benchmark_role="TRAIN_RETRIEVAL_DEVELOPMENT",
            allowed_prefreeze_uses=("RETRIEVAL_DEVELOPMENT",),
            writeback_policy="SHADOW_ONLY_NO_ACTIVE_BANK_WRITEBACK",
            method_selection_allowed=True,
            formal_active_memory_source_allowed=False,
            final_evaluation_allowed_after_method_freeze=False,
            clean_confirmation=False,
            fresh_ood_claim_allowed=False,
            shadow_readback_during_formal_evaluation=False,
        )
    if (
        access_class
        is task_access.MemoryTaskAccessClass.VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED
    ):
        return dict(
            historical_exposure_class="NO_REGISTERED_ROUND1_EXPOSURE",
            historically_exposed=False,
            benchmark_role="PROJECT_HELD_OUT_ID_CONFIRMATION",
            allowed_prefreeze_uses=(),
            writeback_policy="FORMAL_EVALUATION_WRITEBACK_FORBIDDEN",
            method_selection_allowed=False,
            formal_active_memory_source_allowed=False,
            final_evaluation_allowed_after_method_freeze=True,
            clean_confirmation=True,
            fresh_ood_claim_allowed=False,
            shadow_readback_during_formal_evaluation=False,
        )
    if (
        access_class
        is task_access.MemoryTaskAccessClass
        .VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
    ):
        return dict(
            historical_exposure_class="HISTORICALLY_EXPOSED",
            historically_exposed=True,
            benchmark_role="STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
            allowed_prefreeze_uses=("LABELED_MECHANISM_DEVELOPMENT_ONLY",),
            writeback_policy="FORMAL_EVALUATION_WRITEBACK_FORBIDDEN",
            method_selection_allowed=False,
            formal_active_memory_source_allowed=False,
            final_evaluation_allowed_after_method_freeze=True,
            clean_confirmation=False,
            fresh_ood_claim_allowed=False,
            shadow_readback_during_formal_evaluation=False,
        )
    raise AssertionError(access_class)


def _expected_records(root: Path):
    task_access = _task_access()
    identities = []
    for split in ("train", "valid_seen", "valid_unseen"):
        for game in sorted((root / split).glob("*/trial_*/game.tw-pddl")):
            relative = game.relative_to(root).as_posix()
            game_sha = hashlib.sha256(game.read_bytes()).hexdigest()
            task_type = _task_type_from_directory(game.parents[1].name)
            group_id = task_access.canonical_task_gamefile_group_id(
                relative_gamefile=relative,
                gamefile_sha256=game_sha,
            )
            identities.append(
                (
                    split,
                    task_type,
                    game.parent.name,
                    relative,
                    game_sha,
                    group_id,
                )
            )

    train_assignments = task_access.partition_train_task_groups(
        tuple(
            task_access.TrainTaskGroupV1(
                task_type=item[1],
                task_gamefile_group_id=item[5],
            )
            for item in identities
            if item[0] == "train"
        )
    )
    assignment_by_id = {
        item.task_gamefile_group_id: item.access_class
        for item in train_assignments
    }

    records = []
    for split, task_type, trial_id, relative, game_sha, group_id in identities:
        if split == "train":
            access_class = assignment_by_id[group_id]
        elif split == "valid_seen":
            access_class = (
                task_access.MemoryTaskAccessClass
                .VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED
            )
        else:
            access_class = (
                task_access.MemoryTaskAccessClass
                .VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
            )
        records.append(
            task_access.MemoryTaskAccessRegenerationRecordV1(
                trial_id=trial_id,
                task_type=task_type,
                split=split,
                dataset_relative_gamefile=relative,
                gamefile_sha256=game_sha,
                task_gamefile_group_id=group_id,
                access_class=access_class,
                **_role_payload(task_access, access_class),
            )
        )
    return tuple(records)


def _synthetic_authority(module, root: Path):
    task_access = _task_access()
    records = _expected_records(root)
    protected = task_access.canonical_protected_task_access_jsonl(records)
    counts = {
        key: 0
        for key in (
            "TRAIN_MEMORY_SOURCE",
            "TRAIN_RETRIEVAL_DEV",
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED",
            "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
        )
    }
    for record in records:
        counts[record.access_class.value] += 1
    return module.TaskAccessMaterializationAuthorityV2(
        original_failure_memory_design_commit=(
            module.ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT
        ),
        sha_authority_correction_design_commit=(
            module.SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT
        ),
        historical_design_candidate_sha256=(
            module.HISTORICAL_DESIGN_CANDIDATE_SHA256
        ),
        approved_exact_contract_protected_sha256=(
            hashlib.sha256(protected).hexdigest()
        ),
        expected_populations=tuple(sorted(counts.items())),
    )


def _output_paths(tmp_path: Path):
    staging = tmp_path / "staging"
    staging.mkdir(exist_ok=True)
    return (
        staging / "protected.jsonl",
        staging / "sanitized.jsonl",
        staging / "receipt.json",
    )


def _run_success(module, tmp_path: Path):
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=tmp_path / "fake_repo",
    )
    return dataset, protected, sanitized, receipt, result


def test_materializer_matches_independent_protected_and_sanitized_bytes(tmp_path: Path) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)

    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )

    task_access = _task_access()
    expected_records = _expected_records(dataset)
    expected_protected = task_access.canonical_protected_task_access_jsonl(
        expected_records
    )
    expected_sanitized = task_access.canonical_task_access_jsonl(
        tuple(record.to_sanitized() for record in expected_records)
    )

    assert protected.read_bytes() == expected_protected
    assert sanitized.read_bytes() == expected_sanitized
    assert result.protected_record_count == 8
    assert result.sanitized_record_count == 8
    assert dict(result.role_counts) == {
        "TRAIN_MEMORY_SOURCE": 4,
        "TRAIN_RETRIEVAL_DEV": 2,
        "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 1,
        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 1,
    }


def test_sanitized_and_receipt_do_not_disclose_heldout_path_semantics(tmp_path: Path) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)

    module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )

    safe_bytes = sanitized.read_bytes() + receipt.read_bytes()
    for forbidden in (
        b"dataset_relative_gamefile",
        b'"task_type"',
        b"Tomato",
        b"GarbageCan",
        b"Spatula",
        b"Drawer",
        b"trial_seen_secret",
        b"trial_unseen_secret",
    ):
        assert forbidden not in safe_bytes
    assert b"dataset_relative_gamefile" in protected.read_bytes()


def test_report_contains_only_counts_and_hashes_not_heldout_semantics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )
    module.report_materialization_result(result)
    captured = capsys.readouterr()
    text = captured.out + captured.err
    for forbidden in (
        "Tomato",
        "GarbageCan",
        "Spatula",
        "Drawer",
        "trial_seen_secret",
        "trial_unseen_secret",
        "dataset_relative_gamefile",
    ):
        assert forbidden not in text
    assert "protected_record_count=8" in text
    assert "sanitized_record_count=8" in text


def test_materializer_is_deterministic_across_distinct_outputs(tmp_path: Path) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    authority = _synthetic_authority(module, dataset)

    outputs = []
    for name in ("first", "second"):
        stage = tmp_path / name
        stage.mkdir()
        protected = stage / "protected.jsonl"
        sanitized = stage / "sanitized.jsonl"
        receipt = stage / "receipt.json"
        result = module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )
        outputs.append(
            (
                protected.read_bytes(),
                sanitized.read_bytes(),
                receipt.read_bytes(),
                result,
            )
        )
    assert outputs[0] == outputs[1]


def test_materializer_rejects_missing_required_split(tmp_path: Path) -> None:
    module = _materializer()
    root = tmp_path / "dataset"
    (root / "train").mkdir(parents=True)
    (root / "valid_seen").mkdir()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = module.TaskAccessMaterializationAuthorityV2(
        original_failure_memory_design_commit=module.ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT,
        approved_exact_contract_protected_sha256="0" * 64,
        expected_populations=tuple(
            sorted(
                {
                    "TRAIN_MEMORY_SOURCE": 0,
                    "TRAIN_RETRIEVAL_DEV": 0,
                    "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 0,
                    "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 0,
                }.items()
            )
        ),
    )
    with pytest.raises(module.TaskAccessMaterializationError, match="MISSING_REQUIRED_SPLIT"):
        module.materialize_task_access(
            dataset_root=root,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )


def test_enumerator_rejects_unsupported_split(tmp_path: Path) -> None:
    module = _materializer()
    root = tmp_path / "dataset"
    root.mkdir()
    with pytest.raises(module.TaskAccessMaterializationError, match="UNSUPPORTED_SPLIT"):
        module._enumerate_split(root, "valid_train")


def test_enumeration_fix_v1_missing_formerly_registered_game_fails_final_identity_gate(
    tmp_path: Path,
) -> None:
    module = _materializer()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    target = (
        next((dataset / "valid_seen").glob("*/trial_*"))
        / "game.tw-pddl"
    )
    target.unlink()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(
        module,
        _synthetic_dataset(tmp_path / "authority_dataset"),
    )

    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="PROTECTED_REGENERATION_SHA256_MISMATCH",
    ):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )

    assert not protected.exists()
    assert not sanitized.exists()
    assert not receipt.exists()


def test_materializer_rejects_non_regular_gamefile(tmp_path: Path) -> None:
    module = _materializer()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    target = next((dataset / "valid_seen").glob("*/trial_*")) / "game.tw-pddl"
    target.unlink()
    target.mkdir()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, _synthetic_dataset(tmp_path / "authority_dataset"))
    with pytest.raises(module.TaskAccessMaterializationError, match="NON_REGULAR_GAMEFILE"):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )


@pytest.mark.parametrize("broken", [False, True])
def test_materializer_rejects_symlink_gamefile(tmp_path: Path, broken: bool) -> None:
    module = _materializer()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    target = next((dataset / "valid_seen").glob("*/trial_*")) / "game.tw-pddl"
    original = target.read_bytes()
    target.unlink()
    link_target = tmp_path / "outside_game.tw-pddl"
    if not broken:
        link_target.write_bytes(original)
    target.symlink_to(link_target)
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, _synthetic_dataset(tmp_path / "authority_dataset"))
    with pytest.raises(module.TaskAccessMaterializationError, match="SYMLINK_GAMEFILE"):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )


def test_materializer_rejects_lexical_in_root_path_resolving_outside(tmp_path: Path) -> None:
    module = _materializer()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    seen_task = next((dataset / "valid_seen").iterdir())
    original_trial = next(seen_task.glob("trial_*"))
    for child in original_trial.iterdir():
        child.unlink()
    original_trial.rmdir()
    outside_trial = tmp_path / "outside" / "trial_seen_secret"
    outside_trial.mkdir(parents=True)
    (outside_trial / "game.tw-pddl").write_bytes(b"OUTSIDE")
    original_trial.symlink_to(outside_trial, target_is_directory=True)
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, _synthetic_dataset(tmp_path / "authority_dataset"))
    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="RESOLVED_PATH_OUTSIDE_DATASET_ROOT",
    ):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )


def test_duplicate_group_identity_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    monkeypatch.setattr(
        module.task_access,
        "canonical_task_gamefile_group_id",
        lambda **_: "f" * 64,
    )
    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="DUPLICATE_TASK_GAMEFILE_GROUP_ID",
    ):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )


@pytest.mark.parametrize("which", ["protected", "sanitized", "receipt"])
def test_materializer_refuses_any_existing_output(tmp_path: Path, which: str) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    selected = {
        "protected": protected,
        "sanitized": sanitized,
        "receipt": receipt,
    }[which]
    selected.write_bytes(b"PREEXISTING")
    authority = _synthetic_authority(module, dataset)
    with pytest.raises(module.TaskAccessMaterializationError, match="OUTPUT_ALREADY_EXISTS"):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )
    assert selected.read_bytes() == b"PREEXISTING"


def test_protected_output_inside_repository_is_rejected(tmp_path: Path) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    staging = tmp_path / "staging"
    staging.mkdir()
    protected = fake_repo / "protected.jsonl"
    sanitized = staging / "sanitized.jsonl"
    receipt = staging / "receipt.json"
    authority = _synthetic_authority(module, dataset)
    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="PROTECTED_OUTPUT_INSIDE_REPOSITORY",
    ):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )
    assert not protected.exists()


def test_protected_hash_mismatch_fails_before_any_output(tmp_path: Path) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    bad = module.TaskAccessMaterializationAuthorityV2(
        original_failure_memory_design_commit=authority.original_failure_memory_design_commit,
        approved_exact_contract_protected_sha256="0" * 64,
        expected_populations=authority.expected_populations,
    )
    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="PROTECTED_REGENERATION_SHA256_MISMATCH",
    ):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=bad,
            repository_root=fake_repo,
        )
    assert not protected.exists()
    assert not sanitized.exists()
    assert not receipt.exists()


def test_role_population_mismatch_fails_before_any_output(tmp_path: Path) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    counts = dict(authority.expected_populations)
    counts["TRAIN_MEMORY_SOURCE"] += 1
    bad = module.TaskAccessMaterializationAuthorityV2(
        original_failure_memory_design_commit=authority.original_failure_memory_design_commit,
        approved_exact_contract_protected_sha256=authority.approved_exact_contract_protected_sha256,
        expected_populations=tuple(sorted(counts.items())),
    )
    with pytest.raises(module.TaskAccessMaterializationError, match="ROLE_POPULATION_MISMATCH"):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=bad,
            repository_root=fake_repo,
        )
    assert not protected.exists()
    assert not sanitized.exists()
    assert not receipt.exists()


def test_invalid_utf8_gamefile_is_hashed_as_bytes_not_parsed(tmp_path: Path) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )
    assert result.protected_record_count == 8


def test_trajectory_contents_are_not_read(tmp_path: Path) -> None:
    module = _materializer()
    if os.name != "posix":
        pytest.skip("permission-based read guard is POSIX-specific")
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    trajectories = tuple(dataset.glob("*/*/trial_*/traj_data.json"))
    assert trajectories
    for path in trajectories:
        path.chmod(0)
    try:
        protected, sanitized, receipt = _output_paths(tmp_path)
        authority = _synthetic_authority(module, dataset)
        result = module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )
        assert result.protected_record_count == 8
    finally:
        for path in trajectories:
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_outputs_use_restrictive_permissions_on_posix(tmp_path: Path) -> None:
    module = _materializer()
    if os.name != "posix":
        pytest.skip("mode assertion is POSIX-specific")
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )
    for path in (protected, sanitized, receipt):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_real_authority_config_requires_exact_registered_constants(
    tmp_path: Path,
) -> None:
    module = _materializer()
    path = tmp_path / "authority.json"
    payload = {
        "schema": module.CONFIG_SCHEMA,
        "access_policy_id": module.ACCESS_POLICY_ID,
        "disclosure_policy_id": module.DISCLOSURE_POLICY_ID,
        "original_failure_memory_design_commit": (
            module.ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT
        ),
        "sha_authority_correction_design_commit": (
            module.SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT
        ),
        "historical_design_candidate_sha256": (
            module.HISTORICAL_DESIGN_CANDIDATE_SHA256
        ),
        "approved_exact_contract_protected_sha256": (
            module.APPROVED_EXACT_CONTRACT_PROTECTED_SHA256
        ),
        "expected_populations": {
            "TRAIN_MEMORY_SOURCE": 2367,
            "TRAIN_RETRIEVAL_DEV": 1186,
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
            "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 134,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    authority = module.load_real_authority_config(path)
    assert (
        authority.original_failure_memory_design_commit
        == module.ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT
    )
    assert (
        authority.sha_authority_correction_design_commit
        == module.SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT
    )
    assert (
        authority.historical_design_candidate_sha256
        == module.HISTORICAL_DESIGN_CANDIDATE_SHA256
    )
    assert (
        authority.approved_exact_contract_protected_sha256
        == module.APPROVED_EXACT_CONTRACT_PROTECTED_SHA256
    )


def test_real_authority_config_rejects_wrong_design_commit(
    tmp_path: Path,
) -> None:
    module = _materializer()
    path = tmp_path / "authority.json"
    payload = {
        "schema": module.CONFIG_SCHEMA,
        "access_policy_id": module.ACCESS_POLICY_ID,
        "disclosure_policy_id": module.DISCLOSURE_POLICY_ID,
        "original_failure_memory_design_commit": "0" * 40,
        "sha_authority_correction_design_commit": (
            module.SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT
        ),
        "historical_design_candidate_sha256": (
            module.HISTORICAL_DESIGN_CANDIDATE_SHA256
        ),
        "approved_exact_contract_protected_sha256": (
            module.APPROVED_EXACT_CONTRACT_PROTECTED_SHA256
        ),
        "expected_populations": {
            "TRAIN_MEMORY_SOURCE": 2367,
            "TRAIN_RETRIEVAL_DEV": 1186,
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
            "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 134,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT_MISMATCH",
    ):
        module.load_real_authority_config(path)


def test_materializer_source_has_no_trajectory_or_environment_semantic_reader() -> None:
    _materializer()
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "traj_data.json",
        "task_desc",
        "turk_annotations",
        "get_environment",
        "AlfredTWEnv",
        "textworld",
        "import alfworld",
        "from alfworld",
    ):
        assert forbidden not in source


def test_noncanonical_filesystem_identity_is_wrapped_without_path_disclosure(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root = tmp_path / "dataset"
    for split in ("train", "valid_seen", "valid_unseen"):
        (root / split).mkdir(parents=True, exist_ok=True)
    # Backslash is legal in a POSIX filename but forbidden by the canonical
    # dataset-relative identity contract.  The materializer must not leak the
    # raw path when it fails closed.
    _write_game(
        root,
        split="valid_seen",
        task_directory=(
            "pick_and_place_simple-Secret\\Object-None-Fridge-9"
        ),
        trial_id="trial_secret_path",
        payload=b"SECRET",
    )
    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="TASK_IDENTITY_CONTRACT_REJECTED",
    ) as captured:
        module._enumerate_split(root.resolve(strict=True), "valid_seen")
    assert "Secret" not in str(captured.value)
    assert "trial_secret_path" not in str(captured.value)


@pytest.mark.parametrize(
    "which",
    ["protected", "sanitized", "receipt"],
)
def test_review_hardening_task_outputs_cannot_write_into_dataset_root(
    tmp_path: Path,
    which: str,
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    outside = tmp_path / "outside"
    outside.mkdir()
    paths = {
        "protected": outside / "protected.jsonl",
        "sanitized": outside / "sanitized.jsonl",
        "receipt": outside / "receipt.json",
    }
    paths[which] = dataset / f"{which}.out"
    authority = _synthetic_authority(module, dataset)

    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="OUTPUT_INSIDE_DATASET_ROOT",
    ):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=paths["protected"],
            sanitized_output=paths["sanitized"],
            receipt_output=paths["receipt"],
            authority=authority,
            repository_root=fake_repo,
        )

    assert not paths[which].exists()


def test_review_hardening_task_output_failure_cleans_earlier_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)

    original = module._exclusive_write

    def fail_second(path: Path, payload: bytes) -> None:
        if path == sanitized:
            raise OSError("synthetic second-output failure")
        original(path, payload)

    monkeypatch.setattr(
        module,
        "_exclusive_write",
        fail_second,
    )

    with pytest.raises(OSError):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=authority,
            repository_root=fake_repo,
        )

    assert not protected.exists()
    assert not sanitized.exists()
    assert not receipt.exists()



def test_enumeration_fix_v1_raw_trial_without_gamefile_is_skipped(
    tmp_path: Path,
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")

    task_dir = next((dataset / "train").iterdir())
    raw_trial = task_dir / "trial_raw_without_gamefile"
    raw_trial.mkdir()
    (raw_trial / "traj_data.json").write_text(
        '{"task_desc":"RAW_TRIAL_ONLY"}',
        encoding="utf-8",
    )

    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )

    assert result.protected_record_count == 8
    assert result.sanitized_record_count == 8


def test_enumeration_fix_v1_unsupported_raw_family_without_gamefile_is_skipped(
    tmp_path: Path,
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")

    raw_trial = (
        dataset
        / "train"
        / "unsupported_family-Secret-None-Place-999"
        / "trial_raw_without_gamefile"
    )
    raw_trial.mkdir(parents=True)
    (raw_trial / "traj_data.json").write_text(
        '{"task_desc":"RAW_UNSUPPORTED_ONLY"}',
        encoding="utf-8",
    )

    protected, sanitized, receipt = _output_paths(tmp_path)
    authority = _synthetic_authority(module, dataset)
    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )

    assert result.protected_record_count == 8
    assert result.sanitized_record_count == 8


def test_enumeration_fix_v1_regular_game_in_unsupported_family_still_stops(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root = tmp_path / "dataset"
    (root / "train").mkdir(parents=True)

    _write_game(
        root,
        split="train",
        task_directory="unsupported_family-Secret-None-Place-999",
        trial_id="trial_regular_game",
        payload=b"REGISTERED-GAME-CANDIDATE",
    )

    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="UNSUPPORTED_TASK_TYPE",
    ):
        module._enumerate_split(
            root.resolve(strict=True),
            "train",
        )

# ===== TASK 2 SHA AUTHORITY V2 RED CONTRACT =====

_TASK2_TASK1_COMMIT = "08aa577a299012aa59b03d75a4a0654ae0d74d69"
_TASK2_ORIGINAL_DESIGN_COMMIT = "b3cb816e2e727600f79f1947a77c73ce87d4a97c"
_TASK2_HISTORICAL_SHA = (
    "6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a"
)
_TASK2_EXACT_SHA = (
    "260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea"
)
_TASK2_CONFIG_V1_PATH = (
    REPO_ROOT / "configs/memory/task_access_regeneration_v1.json"
)
_TASK2_CONFIG_V2_PATH = (
    REPO_ROOT / "configs/memory/task_access_regeneration_v2.json"
)


def _task2_real_populations() -> dict[str, int]:
    return {
        "TRAIN_MEMORY_SOURCE": 2367,
        "TRAIN_RETRIEVAL_DEV": 1186,
        "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 134,
    }


def _task2_v2_payload(
    *,
    exact_sha: str = _TASK2_EXACT_SHA,
    historical_sha: str = _TASK2_HISTORICAL_SHA,
) -> dict[str, object]:
    return {
        "schema": "TASK_ACCESS_REGENERATION_CONFIG_V2",
        "access_policy_id": "MEMORY_TASK_ACCESS_V2_1",
        "disclosure_policy_id": "HELDOUT_IDENTITY_DISCLOSURE_POLICY_V1",
        "original_failure_memory_design_commit": _TASK2_ORIGINAL_DESIGN_COMMIT,
        "sha_authority_correction_design_commit": _TASK2_TASK1_COMMIT,
        "historical_design_candidate_sha256": historical_sha,
        "approved_exact_contract_protected_sha256": exact_sha,
        "expected_populations": _task2_real_populations(),
    }


def _task2_write_payload(
    tmp_path: Path,
    payload: dict[str, object],
) -> Path:
    path = tmp_path / "task_access_regeneration_v2.json"
    path.write_text(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _task2_expect_loader_error(
    module,
    tmp_path: Path,
    payload: dict[str, object],
    expected_code: str,
) -> None:
    path = _task2_write_payload(tmp_path, payload)
    try:
        module.load_real_authority_config(path)
    except module.TaskAccessMaterializationError as exc:
        assert str(exc) == expected_code
        return
    pytest.fail(f"TASK2_RED_MISSING={expected_code}")


def _task2_require_v2_class(module):
    if not hasattr(module, "TaskAccessMaterializationAuthorityV2"):
        pytest.fail("TASK2_RED_MISSING_AUTHORITY_V2")
    return module.TaskAccessMaterializationAuthorityV2


def _task2_synthetic_v2_authority(
    module,
    dataset: Path,
):
    authority_type = _task2_require_v2_class(module)
    task_access = _task_access()
    records = _expected_records(dataset)
    protected = task_access.canonical_protected_task_access_jsonl(records)

    counts = {
        "TRAIN_MEMORY_SOURCE": 0,
        "TRAIN_RETRIEVAL_DEV": 0,
        "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 0,
        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 0,
    }
    for record in records:
        counts[record.access_class.value] += 1

    return authority_type(
        original_failure_memory_design_commit=_TASK2_ORIGINAL_DESIGN_COMMIT,
        sha_authority_correction_design_commit=_TASK2_TASK1_COMMIT,
        historical_design_candidate_sha256=_TASK2_HISTORICAL_SHA,
        approved_exact_contract_protected_sha256=hashlib.sha256(
            protected
        ).hexdigest(),
        expected_populations=tuple(sorted(counts.items())),
    )


def test_execution_loader_rejects_v1_authority_config() -> None:
    module = _materializer()
    assert _TASK2_CONFIG_V1_PATH.is_file()

    try:
        module.load_real_authority_config(_TASK2_CONFIG_V1_PATH)
    except module.TaskAccessMaterializationError as exc:
        assert str(exc) == "AUTHORITY_CONFIG_V1_REJECTED"
        return

    pytest.fail("TASK2_RED_MISSING=AUTHORITY_CONFIG_V1_REJECTED")


def test_v2_authority_requires_correction_design_commit(
    tmp_path: Path,
) -> None:
    module = _materializer()
    payload = _task2_v2_payload()
    del payload["sha_authority_correction_design_commit"]

    _task2_expect_loader_error(
        module,
        tmp_path,
        payload,
        "SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT_MISSING",
    )


def test_v2_authority_preserves_historical_candidate(
    tmp_path: Path,
) -> None:
    module = _materializer()
    path = _task2_write_payload(
        tmp_path,
        _task2_v2_payload(),
    )

    try:
        authority = module.load_real_authority_config(path)
    except module.TaskAccessMaterializationError as exc:
        pytest.fail(f"TASK2_RED_V2_CONFIG_NOT_SUPPORTED={exc}")

    assert (
        authority.historical_design_candidate_sha256
        == _TASK2_HISTORICAL_SHA
    )
    assert (
        authority.approved_exact_contract_protected_sha256
        == _TASK2_EXACT_SHA
    )
    assert (
        authority.sha_authority_correction_design_commit
        == _TASK2_TASK1_COMMIT
    )


def test_v2_authority_uses_exact_contract_sha_as_only_execution_gate(
    tmp_path: Path,
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)

    authority = _task2_synthetic_v2_authority(
        module,
        dataset,
    )

    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )

    assert (
        result.protected_regeneration_sha256
        == authority.approved_exact_contract_protected_sha256
    )
    assert (
        authority.historical_design_candidate_sha256
        != result.protected_regeneration_sha256
    )


def test_v2_authority_rejects_missing_exact_contract_sha(
    tmp_path: Path,
) -> None:
    module = _materializer()
    payload = _task2_v2_payload()
    del payload["approved_exact_contract_protected_sha256"]

    _task2_expect_loader_error(
        module,
        tmp_path,
        payload,
        "APPROVED_EXACT_CONTRACT_SHA256_MISSING",
    )


def test_v2_authority_rejects_wrong_exact_contract_sha(
    tmp_path: Path,
) -> None:
    module = _materializer()
    payload = _task2_v2_payload(
        exact_sha="0" * 64,
    )

    _task2_expect_loader_error(
        module,
        tmp_path,
        payload,
        "APPROVED_EXACT_CONTRACT_SHA256_MISMATCH",
    )


def test_v2_receipt_separates_historical_and_execution_digests(
    tmp_path: Path,
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)

    authority = _task2_synthetic_v2_authority(
        module,
        dataset,
    )

    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )

    payload = json.loads(
        receipt.read_text(encoding="utf-8")
    )

    assert payload["schema"] == "MEMORY_TASK_ACCESS_REGENERATION_RECEIPT_V2"
    assert (
        payload["original_failure_memory_design_commit"]
        == _TASK2_ORIGINAL_DESIGN_COMMIT
    )
    assert (
        payload["sha_authority_correction_design_commit"]
        == _TASK2_TASK1_COMMIT
    )
    assert (
        payload["historical_design_candidate_sha256"]
        == _TASK2_HISTORICAL_SHA
    )
    assert (
        payload["approved_exact_contract_protected_sha256"]
        == authority.approved_exact_contract_protected_sha256
    )
    assert (
        payload["protected_regeneration_sha256"]
        == authority.approved_exact_contract_protected_sha256
    )
    assert (
        payload["historical_design_candidate_sha256"]
        != payload["protected_regeneration_sha256"]
    )
    assert result.receipt_sha256 == hashlib.sha256(
        receipt.read_bytes()
    ).hexdigest()


def test_v2_config_binds_task1_correction_design_commit() -> None:
    assert _TASK2_CONFIG_V2_PATH.is_file(), (
        "TASK2_RED_MISSING_CONFIG_V2"
    )
    payload = json.loads(
        _TASK2_CONFIG_V2_PATH.read_text(
            encoding="utf-8"
        )
    )

    assert payload == _task2_v2_payload()


def test_task_access_core_file_remains_byte_identical() -> None:
    import subprocess

    current = (
        REPO_ROOT
        / "src/pchsi/memory/task_access.py"
    ).read_bytes()

    baseline = subprocess.check_output(
        [
            "git",
            "show",
            (
                _TASK2_TASK1_COMMIT
                + ":src/pchsi/memory/task_access.py"
            ),
        ],
        cwd=REPO_ROOT,
    )

    assert current == baseline

# ===== TASK 3 BEHAVIORAL NO-FALLBACK RED CONTRACT =====

_TASK3_AUDIT_PATH = (
    REPO_ROOT
    / "scripts/memory/audit_task_access_sha_authority_no_fallback_v1.py"
)


def test_historical_candidate_is_accepted_only_as_provenance(
    tmp_path: Path,
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)

    authority = _task2_synthetic_v2_authority(module, dataset)

    result = module.materialize_task_access(
        dataset_root=dataset,
        protected_output=protected,
        sanitized_output=sanitized,
        receipt_output=receipt,
        authority=authority,
        repository_root=fake_repo,
    )

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert (
        payload["historical_design_candidate_sha256"]
        == _TASK2_HISTORICAL_SHA
    )
    assert (
        payload["approved_exact_contract_protected_sha256"]
        == result.protected_regeneration_sha256
    )
    assert (
        payload["historical_design_candidate_sha256"]
        != result.protected_regeneration_sha256
    )


def test_historical_candidate_in_execution_field_is_rejected(
    tmp_path: Path,
) -> None:
    module = _materializer()
    payload = _task2_v2_payload(
        exact_sha=_TASK2_HISTORICAL_SHA,
    )
    _task2_expect_loader_error(
        module,
        tmp_path,
        payload,
        "APPROVED_EXACT_CONTRACT_SHA256_MISMATCH",
    )


def test_missing_exact_contract_authority_is_rejected(
    tmp_path: Path,
) -> None:
    module = _materializer()
    payload = _task2_v2_payload()
    del payload["approved_exact_contract_protected_sha256"]
    _task2_expect_loader_error(
        module,
        tmp_path,
        payload,
        "APPROVED_EXACT_CONTRACT_SHA256_MISSING",
    )


def test_exact_contract_mismatch_does_not_fallback_to_historical(
    tmp_path: Path,
) -> None:
    module = _materializer()
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dataset = _synthetic_dataset(tmp_path / "dataset")
    protected, sanitized, receipt = _output_paths(tmp_path)

    good = _task2_synthetic_v2_authority(module, dataset)
    bad = module.TaskAccessMaterializationAuthorityV2(
        original_failure_memory_design_commit=(
            good.original_failure_memory_design_commit
        ),
        sha_authority_correction_design_commit=(
            good.sha_authority_correction_design_commit
        ),
        historical_design_candidate_sha256=_TASK2_HISTORICAL_SHA,
        approved_exact_contract_protected_sha256="0" * 64,
        expected_populations=good.expected_populations,
    )

    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="PROTECTED_REGENERATION_SHA256_MISMATCH",
    ):
        module.materialize_task_access(
            dataset_root=dataset,
            protected_output=protected,
            sanitized_output=sanitized,
            receipt_output=receipt,
            authority=bad,
            repository_root=fake_repo,
        )

    assert not protected.exists()
    assert not sanitized.exists()
    assert not receipt.exists()


def test_v1_config_cannot_reenable_historical_execution_gate() -> None:
    module = _materializer()
    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="AUTHORITY_CONFIG_V1_REJECTED",
    ):
        module.load_real_authority_config(
            _TASK2_CONFIG_V1_PATH
        )


def test_correction_v1_instance_requires_distinct_digest_values() -> None:
    module = _materializer()
    with pytest.raises(
        module.TaskAccessMaterializationError,
        match="CORRECTION_V1_DIGESTS_MUST_DIFFER",
    ):
        module.TaskAccessMaterializationAuthorityV2(
            original_failure_memory_design_commit=(
                _TASK2_ORIGINAL_DESIGN_COMMIT
            ),
            sha_authority_correction_design_commit=(
                _TASK2_TASK1_COMMIT
            ),
            historical_design_candidate_sha256=(
                _TASK2_HISTORICAL_SHA
            ),
            approved_exact_contract_protected_sha256=(
                _TASK2_HISTORICAL_SHA
            ),
            expected_populations=tuple(
                sorted(_task2_real_populations().items())
            ),
        )


def _task3_run_static_audit(
    tmp_path: Path,
    source: str,
):
    if not _TASK3_AUDIT_PATH.is_file():
        pytest.fail(
            "TASK3_RED_MISSING_NO_FALLBACK_AUDIT"
        )

    candidate = tmp_path / "materializer.py"
    candidate.write_text(
        source,
        encoding="utf-8",
    )

    import subprocess

    return subprocess.run(
        [
            sys.executable,
            str(_TASK3_AUDIT_PATH),
            "--materializer",
            str(candidate),
        ],
        check=False,
        text=True,
        capture_output=True,
    )


def test_task_access_no_fallback_static_audit_is_registered(
    tmp_path: Path,
) -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    result = _task3_run_static_audit(
        tmp_path,
        source,
    )

    assert result.returncode == 0, (
        result.stdout + result.stderr
    )
    assert (
        "TASK_ACCESS_SHA_AUTHORITY_NO_FALLBACK_AUDIT_PASS"
        in result.stdout
    )


def test_task_access_no_fallback_static_audit_rejects_historical_execution_gate(
    tmp_path: Path,
) -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    old_gate = (
        "        != authority."
        "approved_exact_contract_protected_sha256\n"
    )
    new_gate = (
        "        != authority."
        "historical_design_candidate_sha256\n"
    )
    assert source.count(old_gate) == 1
    mutated = source.replace(
        old_gate,
        new_gate,
        1,
    )

    result = _task3_run_static_audit(
        tmp_path,
        mutated,
    )

    assert result.returncode == 2
    assert (
        "HISTORICAL_FIELD_IN_ADMISSION_COMPARISON"
        in result.stderr
    )


def test_task_access_no_fallback_static_audit_rejects_or_fallback(
    tmp_path: Path,
) -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    old_gate = (
        "        != authority."
        "approved_exact_contract_protected_sha256\n"
    )
    new_gate = (
        "        != (\n"
        "            authority."
        "approved_exact_contract_protected_sha256\n"
        "            or authority."
        "historical_design_candidate_sha256\n"
        "        )\n"
    )
    assert source.count(old_gate) == 1
    mutated = source.replace(
        old_gate,
        new_gate,
        1,
    )

    result = _task3_run_static_audit(
        tmp_path,
        mutated,
    )

    assert result.returncode == 2
    assert (
        "AUTHORITY_FALLBACK_OR_FORBIDDEN"
        in result.stderr
    )


def test_task_access_no_fallback_static_audit_rejects_receipt_substitution(
    tmp_path: Path,
) -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    old_binding = (
        '        "protected_regeneration_sha256": '
        "protected_sha256,\n"
    )
    new_binding = (
        '        "protected_regeneration_sha256": (\n'
        "            authority."
        "historical_design_candidate_sha256\n"
        "        ),\n"
    )
    assert source.count(old_binding) == 1
    mutated = source.replace(
        old_binding,
        new_binding,
        1,
    )

    result = _task3_run_static_audit(
        tmp_path,
        mutated,
    )

    assert result.returncode == 2
    assert (
        "HISTORICAL_FIELD_OUTSIDE_PROVENANCE_RECEIPT"
        in result.stderr
        or "RECEIPT_PROTECTED_DIGEST_NOT_GENERATED_DIGEST"
        in result.stderr
    )


def test_task_access_no_fallback_static_audit_rejects_v1_compatibility_reenable(
    tmp_path: Path,
) -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    old_code = '"AUTHORITY_CONFIG_V1_REJECTED"'
    new_code = '"AUTHORITY_CONFIG_V1_ACCEPTED"'
    assert source.count(old_code) == 1
    mutated = source.replace(
        old_code,
        new_code,
        1,
    )

    result = _task3_run_static_audit(
        tmp_path,
        mutated,
    )

    assert result.returncode == 2
    assert (
        "V1_CONFIG_REJECTION_MISSING"
        in result.stderr
    )
