"""Dataset-bound identity contracts for the S1 backend probe."""

from __future__ import annotations

from dataclasses import dataclass
import re


__all__ = [
    "DatasetIdentity",
    "validate_dataset_identity",
]


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_DATASET_VERSION = "json_2.1.1"


def _require_nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    if "\x00" in value:
        raise ValueError(f"{name} must not contain NUL")


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256")


def _require_bool(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a bool")


def _require_nonnegative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class DatasetIdentity:
    dataset_version: str
    logical_root_id: str
    train_present: bool
    valid_seen_present: bool
    valid_unseen_present: bool
    legacy_manifest_exact_file_sha256: str
    input_contract_sha256: str
    resolved_device: int
    resolved_inode: int
    resolved_mount_id: int
    filesystem_type: str

    def __post_init__(self) -> None:
        if self.dataset_version != REQUIRED_DATASET_VERSION:
            raise ValueError(
                f"dataset_version must be {REQUIRED_DATASET_VERSION}"
            )

        _require_nonempty("logical_root_id", self.logical_root_id)
        _require_nonempty("filesystem_type", self.filesystem_type)

        if self.logical_root_id.startswith("/"):
            raise ValueError("logical_root_id must not be an absolute path")

        for name in (
            "train_present",
            "valid_seen_present",
            "valid_unseen_present",
        ):
            _require_bool(name, getattr(self, name))

        if not (
            self.train_present
            and self.valid_seen_present
            and self.valid_unseen_present
        ):
            raise ValueError(
                "train, valid_seen and valid_unseen must all be present"
            )

        _require_sha256(
            "legacy_manifest_exact_file_sha256",
            self.legacy_manifest_exact_file_sha256,
        )
        _require_sha256(
            "input_contract_sha256",
            self.input_contract_sha256,
        )

        for name in (
            "resolved_device",
            "resolved_inode",
            "resolved_mount_id",
        ):
            _require_nonnegative_int(name, getattr(self, name))

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_version": self.dataset_version,
            "logical_root_id": self.logical_root_id,
            "train_present": self.train_present,
            "valid_seen_present": self.valid_seen_present,
            "valid_unseen_present": self.valid_unseen_present,
            "legacy_manifest_exact_file_sha256": (
                self.legacy_manifest_exact_file_sha256
            ),
            "input_contract_sha256": self.input_contract_sha256,
            "resolved_device": self.resolved_device,
            "resolved_inode": self.resolved_inode,
            "resolved_mount_id": self.resolved_mount_id,
            "filesystem_type": self.filesystem_type,
        }


def validate_dataset_identity(
    observed: DatasetIdentity,
    expected: DatasetIdentity,
) -> None:
    if not isinstance(observed, DatasetIdentity):
        raise TypeError("observed must be DatasetIdentity")
    if not isinstance(expected, DatasetIdentity):
        raise TypeError("expected must be DatasetIdentity")
    if observed != expected:
        raise ValueError("dataset identity does not match frozen contract")
