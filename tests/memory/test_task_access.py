"""Synthetic tests for Failure Memory task-access pure core."""

from __future__ import annotations

from dataclasses import fields
import hashlib
from importlib import import_module
import inspect
import json

import pytest


def _task_access():
    return import_module(
        "pchsi.memory.task_access"
    )


def test_canonical_task_gamefile_group_id_binds_relative_path_and_bytes() -> None:
    task_access = _task_access()
    relative_gamefile = (
        "train/family-a/task-0001/"
        "game.tw-pddl"
    )
    gamefile_sha256 = "a" * 64

    observed = (
        task_access
        .canonical_task_gamefile_group_id(
            relative_gamefile=relative_gamefile,
            gamefile_sha256=gamefile_sha256,
        )
    )

    assert observed == (
        "5316a5b9606c055087b3f2d09cd7d808"
        "f03f8a739b98fa64bf4d72d9572f857c"
    )


@pytest.mark.parametrize(
    "invalid_sha256",
    [
        "",
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "A" * 64,
    ],
)
def test_canonical_task_gamefile_group_id_rejects_noncanonical_sha256(
    invalid_sha256: str,
) -> None:
    task_access = _task_access()

    with pytest.raises(
        ValueError,
        match="gamefile_sha256",
    ):
        task_access.canonical_task_gamefile_group_id(
            relative_gamefile=(
                "train/family-a/task-0001/"
                "game.tw-pddl"
            ),
            gamefile_sha256=invalid_sha256,
        )


@pytest.mark.parametrize(
    "invalid_relative_gamefile",
    [
        "",
        "/train/family-a/task-0001/game.tw-pddl",
        "train//family-a/task-0001/game.tw-pddl",
        "train/./family-a/task-0001/game.tw-pddl",
        "train/family-a/../task-0001/game.tw-pddl",
        r"train\family-a\task-0001\game.tw-pddl",
        "train/family-a/task-0001/game.tw-pddl/",
        "train/family-a/\x00task-0001/game.tw-pddl",
        "train/family-a/\ntask-0001/game.tw-pddl",
    ],
)
def test_canonical_task_gamefile_group_id_rejects_noncanonical_relative_path(
    invalid_relative_gamefile: str,
) -> None:
    task_access = _task_access()

    with pytest.raises(
        ValueError,
        match="relative_gamefile",
    ):
        task_access.canonical_task_gamefile_group_id(
            relative_gamefile=invalid_relative_gamefile,
            gamefile_sha256="a" * 64,
        )


def test_group_identity_api_has_no_absolute_dataset_root_input() -> None:
    task_access = _task_access()

    parameters = inspect.signature(
        task_access.canonical_task_gamefile_group_id
    ).parameters

    assert "dataset_root" not in parameters
    assert tuple(parameters) == (
        "relative_gamefile",
        "gamefile_sha256",
    )


def test_changed_gamefile_bytes_change_group_identity() -> None:
    task_access = _task_access()

    first = task_access.canonical_task_gamefile_group_id(
        relative_gamefile=(
            "train/family-a/task-0001/"
            "game.tw-pddl"
        ),
        gamefile_sha256="a" * 64,
    )
    second = task_access.canonical_task_gamefile_group_id(
        relative_gamefile=(
            "train/family-a/task-0001/"
            "game.tw-pddl"
        ),
        gamefile_sha256="b" * 64,
    )

    assert first != second


def test_train_partition_score_matches_approved_domain_hash() -> None:
    task_access = _task_access()

    group_id = (
        "5316a5b9606c055087b3f2d09cd7d808"
        "f03f8a739b98fa64bf4d72d9572f857c"
    )

    assert task_access.train_partition_score(
        group_id
    ) == (
        "bca3354f556e3d408f4890c861241d83"
        "ee5eacae87210b527f653c3c3d37b123"
    )


@pytest.mark.parametrize(
    "invalid_group_id",
    [
        "",
        "0" * 63,
        "0" * 65,
        "g" * 64,
        "A" * 64,
    ],
)
def test_train_partition_score_rejects_noncanonical_group_id(
    invalid_group_id: str,
) -> None:
    task_access = _task_access()

    with pytest.raises(
        ValueError,
        match="task_gamefile_group_id",
    ):
        task_access.train_partition_score(
            invalid_group_id
        )


def _synthetic_train_groups(task_access):
    return (
        task_access.TrainTaskGroupV1(
            task_type="family-a",
            task_gamefile_group_id="3" * 64,
        ),
        task_access.TrainTaskGroupV1(
            task_type="family-b",
            task_gamefile_group_id="5" * 64,
        ),
        task_access.TrainTaskGroupV1(
            task_type="family-a",
            task_gamefile_group_id="1" * 64,
        ),
        task_access.TrainTaskGroupV1(
            task_type="family-b",
            task_gamefile_group_id="6" * 64,
        ),
        task_access.TrainTaskGroupV1(
            task_type="family-a",
            task_gamefile_group_id="4" * 64,
        ),
        task_access.TrainTaskGroupV1(
            task_type="family-a",
            task_gamefile_group_id="2" * 64,
        ),
    )


def test_family_stratified_partition_matches_ceil_one_third_rule() -> None:
    task_access = _task_access()

    assignments = task_access.partition_train_task_groups(
        _synthetic_train_groups(
            task_access
        )
    )

    observed = {
        assignment.task_gamefile_group_id:
            assignment.access_class
        for assignment in assignments
    }

    assert observed == {
        "1" * 64:
            task_access.MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV,
        "4" * 64:
            task_access.MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV,
        "2" * 64:
            task_access.MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE,
        "3" * 64:
            task_access.MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE,
        "6" * 64:
            task_access.MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV,
        "5" * 64:
            task_access.MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE,
    }

    family_a = [
        assignment
        for assignment in assignments
        if assignment.task_type
        == "family-a"
    ]
    family_b = [
        assignment
        for assignment in assignments
        if assignment.task_type
        == "family-b"
    ]

    assert sum(
        item.access_class
        is task_access.MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV
        for item in family_a
    ) == (4 + 2) // 3

    assert sum(
        item.access_class
        is task_access.MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV
        for item in family_b
    ) == (2 + 2) // 3


def test_train_partition_is_deterministic_under_input_reordering() -> None:
    task_access = _task_access()

    groups = _synthetic_train_groups(
        task_access
    )

    first = (
        task_access
        .partition_train_task_groups(
            groups
        )
    )
    second = (
        task_access
        .partition_train_task_groups(
            tuple(
                reversed(groups)
            )
        )
    )

    assert first == second


def test_train_partition_rejects_duplicate_group_identity() -> None:
    task_access = _task_access()

    duplicate = (
        task_access.TrainTaskGroupV1(
            task_type="family-a",
            task_gamefile_group_id="1" * 64,
        ),
        task_access.TrainTaskGroupV1(
            task_type="family-b",
            task_gamefile_group_id="1" * 64,
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate task_gamefile_group_id",
    ):
        task_access.partition_train_task_groups(
            duplicate
        )


def test_train_partition_input_cannot_accept_outcome_fields() -> None:
    task_access = _task_access()

    with pytest.raises(
        TypeError,
    ):
        task_access.TrainTaskGroupV1(
            task_type="family-a",
            task_gamefile_group_id="1" * 64,
            success=True,
        )


def _record_kwargs(
    task_access,
    access_class,
):
    if (
        access_class
        is task_access.MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE
    ):
        return {
            "task_gamefile_group_id": "1" * 64,
            "gamefile_sha256": "a" * 64,
            "split": "train",
            "historical_exposure_class":
                "NO_REGISTERED_ROUND1_EXPOSURE",
            "historically_exposed": False,
            "access_class": access_class,
            "benchmark_role":
                "TRAIN_MEMORY_SOURCE",
            "allowed_prefreeze_uses":
                ("MEMORY_SOURCE_DEVELOPMENT",),
            "writeback_policy":
                "ACTIVE_MEMORY_SOURCE_ALLOWED",
            "method_selection_allowed": True,
            "formal_active_memory_source_allowed": True,
            "final_evaluation_allowed_after_method_freeze": False,
            "clean_confirmation": False,
            "fresh_ood_claim_allowed": False,
            "shadow_readback_during_formal_evaluation": False,
        }

    if (
        access_class
        is task_access.MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV
    ):
        return {
            "task_gamefile_group_id": "2" * 64,
            "gamefile_sha256": "b" * 64,
            "split": "train",
            "historical_exposure_class":
                "NO_REGISTERED_ROUND1_EXPOSURE",
            "historically_exposed": False,
            "access_class": access_class,
            "benchmark_role":
                "TRAIN_RETRIEVAL_DEVELOPMENT",
            "allowed_prefreeze_uses":
                ("RETRIEVAL_DEVELOPMENT",),
            "writeback_policy":
                "SHADOW_ONLY_NO_ACTIVE_BANK_WRITEBACK",
            "method_selection_allowed": True,
            "formal_active_memory_source_allowed": False,
            "final_evaluation_allowed_after_method_freeze": False,
            "clean_confirmation": False,
            "fresh_ood_claim_allowed": False,
            "shadow_readback_during_formal_evaluation": False,
        }

    if (
        access_class
        is task_access.MemoryTaskAccessClass
        .VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED
    ):
        return {
            "task_gamefile_group_id": "3" * 64,
            "gamefile_sha256": "c" * 64,
            "split": "valid_seen",
            "historical_exposure_class":
                "NO_REGISTERED_ROUND1_EXPOSURE",
            "historically_exposed": False,
            "access_class": access_class,
            "benchmark_role":
                "PROJECT_HELD_OUT_ID_CONFIRMATION",
            "allowed_prefreeze_uses": (),
            "writeback_policy":
                "FORMAL_EVALUATION_WRITEBACK_FORBIDDEN",
            "method_selection_allowed": False,
            "formal_active_memory_source_allowed": False,
            "final_evaluation_allowed_after_method_freeze": True,
            "clean_confirmation": True,
            "fresh_ood_claim_allowed": False,
            "shadow_readback_during_formal_evaluation": False,
        }

    if (
        access_class
        is task_access.MemoryTaskAccessClass
        .VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
    ):
        return {
            "task_gamefile_group_id": "4" * 64,
            "gamefile_sha256": "d" * 64,
            "split": "valid_unseen",
            "historical_exposure_class":
                "HISTORICALLY_EXPOSED",
            "historically_exposed": True,
            "access_class": access_class,
            "benchmark_role":
                "STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
            "allowed_prefreeze_uses":
                ("LABELED_MECHANISM_DEVELOPMENT_ONLY",),
            "writeback_policy":
                "FORMAL_EVALUATION_WRITEBACK_FORBIDDEN",
            "method_selection_allowed": False,
            "formal_active_memory_source_allowed": False,
            "final_evaluation_allowed_after_method_freeze": True,
            "clean_confirmation": False,
            "fresh_ood_claim_allowed": False,
            "shadow_readback_during_formal_evaluation": False,
        }

    raise AssertionError("unknown synthetic access class")


def _record(
    task_access,
    access_class,
    **overrides,
):
    payload = _record_kwargs(
        task_access,
        access_class,
    )
    payload.update(
        overrides
    )
    return task_access.MemoryTaskAccessRecordV1(
        **payload
    )


def test_sanitized_record_has_no_semantic_path_or_task_family_fields() -> None:
    task_access = _task_access()

    record = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED,
    )

    field_names = {
        item.name
        for item in fields(
            type(record)
        )
    }
    payload_names = set(
        record.to_dict()
    )

    forbidden = {
        "trial_id",
        "task_type",
        "dataset_relative_gamefile",
        "gamefile",
        "traj_file",
        "task_goal",
    }

    assert not (
        field_names
        & forbidden
    )
    assert not (
        payload_names
        & forbidden
    )


def test_protected_record_strips_semantics_when_sanitized() -> None:
    task_access = _task_access()

    relative_gamefile = (
        "train/family-a/task-0001/"
        "game.tw-pddl"
    )
    gamefile_sha256 = "a" * 64
    group_id = (
        task_access
        .canonical_task_gamefile_group_id(
            relative_gamefile=relative_gamefile,
            gamefile_sha256=gamefile_sha256,
        )
    )

    protected = (
        task_access
        .MemoryTaskAccessRegenerationRecordV1(
            trial_id="trial-0001",
            task_type="family-a",
            split="train",
            dataset_relative_gamefile=(
                relative_gamefile
            ),
            gamefile_sha256=(
                gamefile_sha256
            ),
            task_gamefile_group_id=(
                group_id
            ),
            historical_exposure_class=(
                "NO_REGISTERED_ROUND1_EXPOSURE"
            ),
            historically_exposed=False,
            access_class=(
                task_access
                .MemoryTaskAccessClass
                .TRAIN_MEMORY_SOURCE
            ),
            benchmark_role=(
                "TRAIN_MEMORY_SOURCE"
            ),
            allowed_prefreeze_uses=(
                "MEMORY_SOURCE_DEVELOPMENT",
            ),
            writeback_policy=(
                "ACTIVE_MEMORY_SOURCE_ALLOWED"
            ),
            method_selection_allowed=True,
            formal_active_memory_source_allowed=True,
            final_evaluation_allowed_after_method_freeze=False,
            clean_confirmation=False,
            fresh_ood_claim_allowed=False,
            shadow_readback_during_formal_evaluation=False,
        )
    )

    protected_payload = (
        protected.to_dict()
    )
    sanitized_payload = (
        protected
        .to_sanitized()
        .to_dict()
    )

    assert (
        protected_payload[
            "dataset_relative_gamefile"
        ]
        == relative_gamefile
    )
    assert (
        protected_payload["task_type"]
        == "family-a"
    )

    assert (
        "dataset_relative_gamefile"
        not in sanitized_payload
    )
    assert (
        "task_type"
        not in sanitized_payload
    )
    assert (
        "trial_id"
        not in sanitized_payload
    )


def test_protected_record_rejects_group_identity_mismatch() -> None:
    task_access = _task_access()

    with pytest.raises(
        ValueError,
        match="task_gamefile_group_id",
    ):
        task_access.MemoryTaskAccessRegenerationRecordV1(
            trial_id="trial-0001",
            task_type="family-a",
            split="train",
            dataset_relative_gamefile=(
                "train/family-a/task-0001/"
                "game.tw-pddl"
            ),
            gamefile_sha256="a" * 64,
            task_gamefile_group_id="f" * 64,
            historical_exposure_class=(
                "NO_REGISTERED_ROUND1_EXPOSURE"
            ),
            historically_exposed=False,
            access_class=(
                task_access
                .MemoryTaskAccessClass
                .TRAIN_MEMORY_SOURCE
            ),
            benchmark_role=(
                "TRAIN_MEMORY_SOURCE"
            ),
            allowed_prefreeze_uses=(
                "MEMORY_SOURCE_DEVELOPMENT",
            ),
            writeback_policy=(
                "ACTIVE_MEMORY_SOURCE_ALLOWED"
            ),
            method_selection_allowed=True,
            formal_active_memory_source_allowed=True,
            final_evaluation_allowed_after_method_freeze=False,
            clean_confirmation=False,
            fresh_ood_claim_allowed=False,
            shadow_readback_during_formal_evaluation=False,
        )


def test_train_memory_source_is_only_role_with_active_bank_writeback() -> None:
    task_access = _task_access()

    source = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .TRAIN_MEMORY_SOURCE,
    )
    retrieval = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .TRAIN_RETRIEVAL_DEV,
    )
    seen = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED,
    )
    unseen = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED,
    )

    assert (
        source.active_bank_writeback_allowed
        is True
    )
    assert (
        retrieval.active_bank_writeback_allowed
        is False
    )
    assert (
        seen.active_bank_writeback_allowed
        is False
    )
    assert (
        unseen.active_bank_writeback_allowed
        is False
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "method_selection_allowed":
                True,
        },
        {
            "formal_active_memory_source_allowed":
                True,
        },
        {
            "historically_exposed":
                True,
        },
        {
            "clean_confirmation":
                False,
        },
        {
            "shadow_readback_during_formal_evaluation":
                True,
        },
    ],
)
def test_valid_seen_role_rejects_forbidden_permissions(
    overrides: dict[str, object],
) -> None:
    task_access = _task_access()

    with pytest.raises(
        ValueError,
    ):
        _record(
            task_access,
            task_access.MemoryTaskAccessClass
            .VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED,
            **overrides,
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "method_selection_allowed":
                True,
        },
        {
            "formal_active_memory_source_allowed":
                True,
        },
        {
            "historically_exposed":
                False,
        },
        {
            "clean_confirmation":
                True,
        },
        {
            "fresh_ood_claim_allowed":
                True,
        },
        {
            "shadow_readback_during_formal_evaluation":
                True,
        },
    ],
)
def test_valid_unseen_role_rejects_fresh_or_method_permissions(
    overrides: dict[str, object],
) -> None:
    task_access = _task_access()

    with pytest.raises(
        ValueError,
    ):
        _record(
            task_access,
            task_access.MemoryTaskAccessClass
            .VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED,
            **overrides,
        )


def test_sanitized_manifest_serialization_is_canonical_and_sorted() -> None:
    task_access = _task_access()

    seen = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED,
    )
    retrieval = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .TRAIN_RETRIEVAL_DEV,
    )

    observed = (
        task_access
        .canonical_task_access_jsonl(
            (
                seen,
                retrieval,
            )
        )
    )

    expected_records = (
        retrieval.to_dict(),
        seen.to_dict(),
    )
    expected = b"".join(
        (
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for payload in expected_records
    )

    assert observed == expected
    assert observed.endswith(
        b"\n"
    )
    assert (
        b"dataset_relative_gamefile"
        not in observed
    )
    assert b'"task_type"' not in observed


def test_sanitized_manifest_rejects_duplicate_group_identity() -> None:
    task_access = _task_access()

    first = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .TRAIN_MEMORY_SOURCE,
    )
    second = _record(
        task_access,
        task_access.MemoryTaskAccessClass
        .TRAIN_MEMORY_SOURCE,
        gamefile_sha256="b" * 64,
    )

    with pytest.raises(
        ValueError,
        match="duplicate task_gamefile_group_id",
    ):
        task_access.canonical_task_access_jsonl(
            (
                first,
                second,
            )
        )


def test_sanitized_manifest_hash_binds_exact_canonical_bytes() -> None:
    task_access = _task_access()

    records = (
        _record(
            task_access,
            task_access.MemoryTaskAccessClass
            .TRAIN_RETRIEVAL_DEV,
        ),
        _record(
            task_access,
            task_access.MemoryTaskAccessClass
            .VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED,
        ),
    )

    payload = (
        task_access
        .canonical_task_access_jsonl(
            records
        )
    )

    assert (
        task_access
        .sha256_task_access_manifest(
            records
        )
        ==
        hashlib.sha256(
            payload
        ).hexdigest()
    )


def test_protected_serialization_retains_required_semantics_only_in_protected_view() -> None:
    task_access = _task_access()

    records = []

    for trial_id, task_type, path, sha, group_char in (
        (
            "trial-b",
            "family-b",
            "train/family-b/task-b/game.tw-pddl",
            "b" * 64,
            None,
        ),
        (
            "trial-a",
            "family-a",
            "train/family-a/task-a/game.tw-pddl",
            "a" * 64,
            None,
        ),
    ):
        group_id = (
            task_access
            .canonical_task_gamefile_group_id(
                relative_gamefile=path,
                gamefile_sha256=sha,
            )
        )
        records.append(
            task_access
            .MemoryTaskAccessRegenerationRecordV1(
                trial_id=trial_id,
                task_type=task_type,
                split="train",
                dataset_relative_gamefile=path,
                gamefile_sha256=sha,
                task_gamefile_group_id=group_id,
                historical_exposure_class=(
                    "NO_REGISTERED_ROUND1_EXPOSURE"
                ),
                historically_exposed=False,
                access_class=(
                    task_access
                    .MemoryTaskAccessClass
                    .TRAIN_MEMORY_SOURCE
                ),
                benchmark_role=(
                    "TRAIN_MEMORY_SOURCE"
                ),
                allowed_prefreeze_uses=(
                    "MEMORY_SOURCE_DEVELOPMENT",
                ),
                writeback_policy=(
                    "ACTIVE_MEMORY_SOURCE_ALLOWED"
                ),
                method_selection_allowed=True,
                formal_active_memory_source_allowed=True,
                final_evaluation_allowed_after_method_freeze=False,
                clean_confirmation=False,
                fresh_ood_claim_allowed=False,
                shadow_readback_during_formal_evaluation=False,
            )
        )

    protected = (
        task_access
        .canonical_protected_task_access_jsonl(
            tuple(
                reversed(records)
            )
        )
    )

    text = protected.decode(
        "utf-8"
    )

    assert (
        '"dataset_relative_gamefile":'
        in text
    )
    assert '"task_type":' in text

    lines = text.splitlines()
    assert len(lines) == 2

    parsed = [
        json.loads(line)
        for line in lines
    ]

    assert [
        item["task_type"]
        for item in parsed
    ] == [
        "family-a",
        "family-b",
    ]


@pytest.mark.parametrize(
    ("access_class_name", "field_name", "bad_value"),
    [
        ("TRAIN_MEMORY_SOURCE", "benchmark_role", "WRONG_ROLE"),
        (
            "TRAIN_MEMORY_SOURCE",
            "writeback_policy",
            "SHADOW_ONLY_NO_ACTIVE_BANK_WRITEBACK",
        ),
        (
            "TRAIN_MEMORY_SOURCE",
            "allowed_prefreeze_uses",
            ("WRONG_USE",),
        ),
        (
            "TRAIN_RETRIEVAL_DEV",
            "method_selection_allowed",
            False,
        ),
        (
            "TRAIN_RETRIEVAL_DEV",
            "writeback_policy",
            "ACTIVE_MEMORY_SOURCE_ALLOWED",
        ),
        (
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED",
            "historical_exposure_class",
            "HISTORICALLY_EXPOSED",
        ),
        (
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED",
            "writeback_policy",
            "ACTIVE_MEMORY_SOURCE_ALLOWED",
        ),
        (
            "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
            "allowed_prefreeze_uses",
            (),
        ),
        (
            "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
            "historical_exposure_class",
            "NO_REGISTERED_ROUND1_EXPOSURE",
        ),
    ],
)
def test_review_hardening_access_role_semantics_are_exact(
    access_class_name: str,
    field_name: str,
    bad_value: object,
) -> None:
    task_access = _task_access()
    access_class = getattr(
        task_access.MemoryTaskAccessClass,
        access_class_name,
    )
    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        _record(
            task_access,
            access_class,
            **{field_name: bad_value},
        )
