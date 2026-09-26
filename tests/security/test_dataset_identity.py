from __future__ import annotations

from dataclasses import FrozenInstanceError
import pytest

from pchsi.security.dataset_identity import (
    DatasetIdentity,
    validate_dataset_identity,
)


def _identity(**overrides: object) -> DatasetIdentity:
    values: dict[str, object] = {
        "dataset_version": "json_2.1.1",
        "logical_root_id": "ALFWORLD_DATASET_LOGICAL_ROOT_V1",
        "train_present": True,
        "valid_seen_present": True,
        "valid_unseen_present": True,
        "legacy_manifest_exact_file_sha256": "a" * 64,
        "input_contract_sha256": "b" * 64,
        "resolved_device": 101,
        "resolved_inode": 202,
        "resolved_mount_id": 303,
        "filesystem_type": "ceph",
    }
    values.update(overrides)
    return DatasetIdentity(**values)  # type: ignore[arg-type]


def test_dataset_identity_is_frozen_and_serializable() -> None:
    identity = _identity()

    assert identity.to_dict()["dataset_version"] == "json_2.1.1"

    with pytest.raises(FrozenInstanceError):
        identity.dataset_version = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset_version", "json_2.1.0"),
        ("logical_root_id", "/absolute/path"),
        ("train_present", False),
        ("valid_seen_present", False),
        ("valid_unseen_present", False),
        ("legacy_manifest_exact_file_sha256", "A" * 64),
        ("input_contract_sha256", "short"),
        ("resolved_device", -1),
        ("resolved_inode", -1),
        ("resolved_mount_id", -1),
        ("filesystem_type", ""),
    ],
)
def test_invalid_dataset_identity_is_rejected(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValueError):
        _identity(**{field: value})


def test_dataset_identity_requires_exact_match() -> None:
    expected = _identity()
    validate_dataset_identity(expected, expected)

    with pytest.raises(ValueError, match="does not match"):
        validate_dataset_identity(
            _identity(resolved_inode=999),
            expected,
        )
