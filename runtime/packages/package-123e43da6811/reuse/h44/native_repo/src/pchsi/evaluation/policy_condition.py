"""Immutable policy-condition identity for distillation experiments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import ClassVar, Self

from .canonical_evidence import (
    canonical_json_text,
    require_lower_sha256,
    strict_json_loads,
)
from .schema_contract import validate_payload_against_schema


_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_CONDITION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PI0_CONDITION_ID = "P4-R0-PI0"
_PI0_POLICY_VERSION = "pi0"
_PI0_MEMORY_VERSION = "MEMORY_M0_V1"
_PI0_SERVED_NAME = "Qwen2.5-3B-Instruct-E1"


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("wire value must be a JSON object")
    return value


def _expect_keys(payload: dict[str, object], expected: set[str]) -> None:
    missing = sorted(expected - set(payload))
    unknown = sorted(set(payload) - expected)
    if missing:
        raise ValueError(f"wire object is missing required fields: {missing}")
    if unknown:
        raise ValueError(f"wire object contains unknown fields: {unknown}")


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains a forbidden character")
    return value


def _optional_text(name: str, value: object) -> str | None:
    return None if value is None else _text(name, value)


def _commit(name: str, value: object) -> str:
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        raise ValueError(
            f"{name} must be a 40-character lowercase commit SHA"
        )
    return value


class CheckpointKind(str, Enum):
    BASE_MODEL = "BASE_MODEL"
    LORA_ADAPTER = "LORA_ADAPTER"
    FULL_CHECKPOINT = "FULL_CHECKPOINT"


class TrainingMethod(str, Enum):
    NONE = "NONE"
    SFT = "SFT"


@dataclass(frozen=True, slots=True)
class PolicyConditionManifestV1:
    SCHEMA_ID: ClassVar[str] = "POLICY_CONDITION_MANIFEST_V1"
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    policy_condition_id: str
    base_model_repository: str
    base_model_revision: str
    checkpoint_kind: CheckpointKind
    checkpoint_path: str | None
    checkpoint_sha256: str | None
    training_method: TrainingMethod
    training_run_id: str | None
    training_config_sha256: str | None
    policy_runtime_manifest_sha256: str
    tokenizer_identity_manifest_sha256: str
    chat_template_sha256: str
    served_model_name: str
    policy_version: str
    memory_version: str
    raw_protocol_sha256: str
    runtime_core_commit: str
    evaluator_commit: str

    _KEYS: ClassVar[set[str]] = {
        "schema_id", "schema_version", "policy_condition_id",
        "base_model_repository", "base_model_revision",
        "checkpoint_kind", "checkpoint_path", "checkpoint_sha256",
        "training_method", "training_run_id",
        "training_config_sha256", "policy_runtime_manifest_sha256",
        "tokenizer_identity_manifest_sha256", "chat_template_sha256",
        "served_model_name", "policy_version", "memory_version",
        "raw_protocol_sha256", "runtime_core_commit",
        "evaluator_commit",
    }

    def __post_init__(self) -> None:
        if self.schema_id != self.SCHEMA_ID:
            raise ValueError("schema_id mismatch")
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("schema_version mismatch")
        _text("policy_condition_id", self.policy_condition_id)
        if _CONDITION.fullmatch(self.policy_condition_id) is None:
            raise ValueError("policy_condition_id has invalid syntax")
        _text("base_model_repository", self.base_model_repository)
        _commit("base_model_revision", self.base_model_revision)
        if type(self.checkpoint_kind) is not CheckpointKind:
            raise TypeError("checkpoint_kind must be CheckpointKind")
        _optional_text("checkpoint_path", self.checkpoint_path)
        if self.checkpoint_sha256 is not None:
            require_lower_sha256(
                "checkpoint_sha256",
                self.checkpoint_sha256,
            )
        if type(self.training_method) is not TrainingMethod:
            raise TypeError("training_method must be TrainingMethod")
        _optional_text("training_run_id", self.training_run_id)
        if self.training_config_sha256 is not None:
            require_lower_sha256(
                "training_config_sha256",
                self.training_config_sha256,
            )
        for name in (
            "policy_runtime_manifest_sha256",
            "tokenizer_identity_manifest_sha256",
            "chat_template_sha256",
            "raw_protocol_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        for name in (
            "served_model_name",
            "policy_version",
            "memory_version",
        ):
            _text(name, getattr(self, name))
        _commit("runtime_core_commit", self.runtime_core_commit)
        _commit("evaluator_commit", self.evaluator_commit)

        if self.checkpoint_kind is CheckpointKind.BASE_MODEL:
            if self.training_method is not TrainingMethod.NONE:
                raise ValueError(
                    "BASE_MODEL requires training_method NONE"
                )
            if any(
                item is not None
                for item in (
                    self.checkpoint_path,
                    self.checkpoint_sha256,
                    self.training_run_id,
                    self.training_config_sha256,
                )
            ):
                raise ValueError(
                    "BASE_MODEL forbids checkpoint/training artifacts"
                )
        else:
            if self.training_method is not TrainingMethod.SFT:
                raise ValueError(
                    "trained checkpoint kinds require SFT"
                )
            if any(
                item is None
                for item in (
                    self.checkpoint_path,
                    self.checkpoint_sha256,
                    self.training_run_id,
                    self.training_config_sha256,
                )
            ):
                raise ValueError(
                    "SFT requires checkpoint and training identity"
                )
            if self.policy_version == "pi0":
                raise ValueError("SFT policy_version must not be pi0")
            if self.served_model_name == _PI0_SERVED_NAME:
                raise ValueError(
                    "trained served_model_name must not reuse pi0"
                )

        if self.policy_condition_id == _PI0_CONDITION_ID:
            if self.checkpoint_kind is not CheckpointKind.BASE_MODEL:
                raise ValueError(
                    "P4-R0-PI0 requires BASE_MODEL checkpoint identity"
                )
            if self.training_method is not TrainingMethod.NONE:
                raise ValueError(
                    "P4-R0-PI0 requires training_method NONE"
                )
            if self.policy_version != _PI0_POLICY_VERSION:
                raise ValueError(
                    "P4-R0-PI0 requires policy_version pi0"
                )
            if self.memory_version != _PI0_MEMORY_VERSION:
                raise ValueError(
                    "P4-R0-PI0 requires MEMORY_M0_V1"
                )
            if self.served_model_name != _PI0_SERVED_NAME:
                raise ValueError(
                    "P4-R0-PI0 requires the frozen pi0 served_model_name"
                )

        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "policy_condition_id": self.policy_condition_id,
            "base_model_repository": self.base_model_repository,
            "base_model_revision": self.base_model_revision,
            "checkpoint_kind": self.checkpoint_kind.value,
            "checkpoint_path": self.checkpoint_path,
            "checkpoint_sha256": self.checkpoint_sha256,
            "training_method": self.training_method.value,
            "training_run_id": self.training_run_id,
            "training_config_sha256": self.training_config_sha256,
            "policy_runtime_manifest_sha256": (
                self.policy_runtime_manifest_sha256
            ),
            "tokenizer_identity_manifest_sha256": (
                self.tokenizer_identity_manifest_sha256
            ),
            "chat_template_sha256": self.chat_template_sha256,
            "served_model_name": self.served_model_name,
            "policy_version": self.policy_version,
            "memory_version": self.memory_version,
            "raw_protocol_sha256": self.raw_protocol_sha256,
            "runtime_core_commit": self.runtime_core_commit,
            "evaluator_commit": self.evaluator_commit,
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> Self:
        payload = _mapping(value)
        _expect_keys(payload, cls._KEYS)
        try:
            checkpoint_kind = CheckpointKind(
                payload["checkpoint_kind"]
            )
            training_method = TrainingMethod(
                payload["training_method"]
            )
        except (TypeError, ValueError) as error:
            raise ValueError("unknown policy condition enum") from error
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            policy_condition_id=payload["policy_condition_id"],
            base_model_repository=payload["base_model_repository"],
            base_model_revision=payload["base_model_revision"],
            checkpoint_kind=checkpoint_kind,
            checkpoint_path=payload["checkpoint_path"],
            checkpoint_sha256=payload["checkpoint_sha256"],
            training_method=training_method,
            training_run_id=payload["training_run_id"],
            training_config_sha256=payload[
                "training_config_sha256"
            ],
            policy_runtime_manifest_sha256=payload[
                "policy_runtime_manifest_sha256"
            ],
            tokenizer_identity_manifest_sha256=payload[
                "tokenizer_identity_manifest_sha256"
            ],
            chat_template_sha256=payload["chat_template_sha256"],
            served_model_name=payload["served_model_name"],
            policy_version=payload["policy_version"],
            memory_version=payload["memory_version"],
            raw_protocol_sha256=payload["raw_protocol_sha256"],
            runtime_core_commit=payload["runtime_core_commit"],
            evaluator_commit=payload["evaluator_commit"],
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> Self:
        return cls.from_dict(strict_json_loads(value))
