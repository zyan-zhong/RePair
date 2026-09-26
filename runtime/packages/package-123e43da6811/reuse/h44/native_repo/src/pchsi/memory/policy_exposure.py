"""Immutable Policy-exposure evidence for Failure Memory Package B."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    strict_json_loads,
)


EXPOSURE_SCHEMA_V1 = "FAILURE_MEMORY_POLICY_EXPOSURE_V1"
EXPOSURE_DOMAIN_V1 = "FAILURE_MEMORY_POLICY_EXPOSURE_ID_V1"
INSERTION_ANCHOR_V1 = (
    "AFTER_EXECUTED_TRANSITIONS_BEFORE_VISIBLE_ADMISSIBLE_COMMANDS"
)


@dataclass(frozen=True, slots=True)
class MemoryPolicyExposureV1:
    schema_id: str
    schema_version: int
    snapshot_sha256: str
    token_budget_contract_sha256: str
    retrieval_mode: str
    branch_role: str
    representation_class: str
    memory_lineage_id: str | None
    record_version: int | None
    projection_artifact_sha256: str | None
    packed_token_count: int
    insertion_anchor: str
    final_prompt_sha256: str
    exposure_sha256: str | None = None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "snapshot_sha256",
            "token_budget_contract_sha256",
            "retrieval_mode",
            "branch_role",
            "representation_class",
            "memory_lineage_id",
            "record_version",
            "projection_artifact_sha256",
            "packed_token_count",
            "insertion_anchor",
            "final_prompt_sha256",
            "exposure_sha256",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != EXPOSURE_SCHEMA_V1 or self.schema_version != 1:
            raise ValueError("exposure schema mismatch")
        require_lower_sha256(
            "snapshot_sha256",
            self.snapshot_sha256,
        )
        require_lower_sha256(
            "token_budget_contract_sha256",
            self.token_budget_contract_sha256,
        )
        require_lower_sha256(
            "final_prompt_sha256",
            self.final_prompt_sha256,
        )
        if self.projection_artifact_sha256 is not None:
            require_lower_sha256(
                "projection_artifact_sha256",
                self.projection_artifact_sha256,
            )
        if (
            not isinstance(self.retrieval_mode, str)
            or not self.retrieval_mode
            or not isinstance(self.branch_role, str)
            or not self.branch_role
            or not isinstance(self.representation_class, str)
            or not self.representation_class
        ):
            raise ValueError("exposure role/mode/class fields invalid")
        if (
            type(self.packed_token_count) is not int
            or self.packed_token_count < 0
        ):
            raise ValueError("packed_token_count invalid")
        if self.insertion_anchor != INSERTION_ANCHOR_V1:
            raise ValueError("Memory insertion anchor mismatch")

        if self.representation_class == "M0":
            if (
                self.memory_lineage_id is not None
                or self.record_version is not None
                or self.projection_artifact_sha256 is not None
                or self.packed_token_count != 0
            ):
                raise ValueError("M0 exposure must carry no Memory record")
        else:
            require_lower_sha256(
                "memory_lineage_id",
                self.memory_lineage_id,
            )
            if (
                type(self.record_version) is not int
                or self.record_version < 1
            ):
                raise ValueError("record_version invalid")
            if self.projection_artifact_sha256 is None:
                raise ValueError("Memory exposure requires projection SHA")

        expected = sha256_bytes(
            EXPOSURE_DOMAIN_V1.encode("utf-8")
            + b"\0"
            + canonical_json_bytes(
                self._payload_without_sha()
            )
        )
        if self.exposure_sha256 is None:
            object.__setattr__(
                self,
                "exposure_sha256",
                expected,
            )
        elif self.exposure_sha256 != expected:
            raise ValueError("exposure SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "snapshot_sha256": self.snapshot_sha256,
            "token_budget_contract_sha256": (
                self.token_budget_contract_sha256
            ),
            "retrieval_mode": self.retrieval_mode,
            "branch_role": self.branch_role,
            "representation_class": self.representation_class,
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "projection_artifact_sha256": (
                self.projection_artifact_sha256
            ),
            "packed_token_count": self.packed_token_count,
            "insertion_anchor": self.insertion_anchor,
            "final_prompt_sha256": self.final_prompt_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "exposure_sha256": self.exposure_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryPolicyExposureV1":
        if not isinstance(value, dict) or frozenset(value) != cls._KEYS:
            raise ValueError("exposure fields mismatch")
        return cls(**value)

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "MemoryPolicyExposureV1":
        return cls.from_dict(strict_json_loads(value))
