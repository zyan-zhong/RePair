"""Concrete π1 identity materialization from sealed, explicit registrations."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from .canonical import (
    directory_manifest_sha256,
    domain_hash,
    ensure_regular_no_symlink,
    exact_keyset,
    parse_canonical_json_file,
    require_nonnegative_int,
    require_object,
    require_sha256,
    require_text,
    sha256_file,
    strict_json_loads,
    write_new_json,
)


_ARTIFACT_NAMES = (
    "base_model_artifact",
    "adapter_artifact",
    "tokenizer_artifact",
    "chat_template",
    "policy_runtime_manifest",
    "decoding_contract",
    "raw_policy_prompt_protocol",
    "training_config",
    "training_data_manifest",
    "reference_evaluation_manifest",
)


@dataclass(frozen=True, slots=True)
class ArtifactRegistrationV1:
    name: str
    kind: str
    path: str
    expected_sha256: str

    _KEYS: ClassVar[set[str]] = {
        "name",
        "kind",
        "path",
        "expected_sha256",
    }

    def __post_init__(self) -> None:
        require_text("artifact name", self.name)
        if self.name not in _ARTIFACT_NAMES:
            raise ValueError(f"unsupported identity artifact: {self.name}")
        if self.kind not in {
            "FILE",
            "DIRECTORY_MANIFEST",
            "MANIFEST_VALUE_SHA256",
        }:
            raise ValueError(
                "artifact kind must be FILE, DIRECTORY_MANIFEST, "
                "or MANIFEST_VALUE_SHA256"
            )
        require_text("artifact path", self.path)
        require_sha256("artifact expected_sha256", self.expected_sha256)

    @classmethod
    def from_dict(cls, value: object) -> "ArtifactRegistrationV1":
        payload = require_object("artifact registration", value)
        exact_keyset(payload, cls._KEYS, name="artifact registration")
        return cls(
            name=payload["name"],
            kind=payload["kind"],
            path=payload["path"],
            expected_sha256=payload["expected_sha256"],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "path": self.path,
            "expected_sha256": self.expected_sha256,
        }


@dataclass(frozen=True, slots=True)
class Pi1IdentitySourceRegistrationV1:
    schema_id: str
    schema_version: int
    logical_policy_id: str
    checkpoint_instance_id: str
    base_model_id: str
    adapter_id: str
    tokenizer_identity: str
    runtime_core_commit: str
    evaluator_commit: str
    training_seed: int
    artifact_registrations: tuple[ArtifactRegistrationV1, ...]
    registration_sha256: str

    SCHEMA_ID: ClassVar[str] = "PI1_IDENTITY_SOURCE_REGISTRATION_V1"
    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "logical_policy_id",
        "checkpoint_instance_id",
        "base_model_id",
        "adapter_id",
        "tokenizer_identity",
        "runtime_core_commit",
        "evaluator_commit",
        "training_seed",
        "artifact_registrations",
        "registration_sha256",
    }

    def __post_init__(self) -> None:
        if self.schema_id != self.SCHEMA_ID or self.schema_version != 1:
            raise ValueError("π1 identity registration schema mismatch")
        for name in (
            "logical_policy_id",
            "checkpoint_instance_id",
            "base_model_id",
            "adapter_id",
            "tokenizer_identity",
            "runtime_core_commit",
            "evaluator_commit",
        ):
            require_text(name, getattr(self, name))
        if self.logical_policy_id != "P4-R1-Q2-BAD":
            raise ValueError("π1 logical policy must be P4-R1-Q2-BAD")
        require_nonnegative_int("training_seed", self.training_seed)
        if len(self.artifact_registrations) != len(_ARTIFACT_NAMES):
            raise ValueError("π1 identity registration must bind ten artifacts")
        observed = tuple(item.name for item in self.artifact_registrations)
        if observed != _ARTIFACT_NAMES:
            raise ValueError(
                "π1 artifact registrations must use the frozen order"
            )
        require_sha256("registration_sha256", self.registration_sha256)
        expected = domain_hash(
            self.SCHEMA_ID,
            self.to_dict(),
            excluded_field="registration_sha256",
        )
        if self.registration_sha256 != expected:
            raise ValueError("π1 source registration self-hash mismatch")

    @classmethod
    def from_dict(cls, value: object) -> "Pi1IdentitySourceRegistrationV1":
        payload = require_object("π1 identity registration", value)
        exact_keyset(payload, cls._KEYS, name="π1 identity registration")
        raw = payload["artifact_registrations"]
        if not isinstance(raw, list):
            raise TypeError("artifact_registrations must be an array")
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            logical_policy_id=payload["logical_policy_id"],
            checkpoint_instance_id=payload["checkpoint_instance_id"],
            base_model_id=payload["base_model_id"],
            adapter_id=payload["adapter_id"],
            tokenizer_identity=payload["tokenizer_identity"],
            runtime_core_commit=payload["runtime_core_commit"],
            evaluator_commit=payload["evaluator_commit"],
            training_seed=payload["training_seed"],
            artifact_registrations=tuple(
                ArtifactRegistrationV1.from_dict(item) for item in raw
            ),
            registration_sha256=payload["registration_sha256"],
        )

    @classmethod
    def from_file(cls, path: Path) -> "Pi1IdentitySourceRegistrationV1":
        source = ensure_regular_no_symlink(
            path, name="π1 identity source registration"
        )
        return cls.from_dict(strict_json_loads(source.read_bytes()))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "logical_policy_id": self.logical_policy_id,
            "checkpoint_instance_id": self.checkpoint_instance_id,
            "base_model_id": self.base_model_id,
            "adapter_id": self.adapter_id,
            "tokenizer_identity": self.tokenizer_identity,
            "runtime_core_commit": self.runtime_core_commit,
            "evaluator_commit": self.evaluator_commit,
            "training_seed": self.training_seed,
            "artifact_registrations": [
                item.to_dict() for item in self.artifact_registrations
            ],
            "registration_sha256": self.registration_sha256,
        }


def build_registration_payload(
    *,
    logical_policy_id: str,
    checkpoint_instance_id: str,
    base_model_id: str,
    adapter_id: str,
    tokenizer_identity: str,
    runtime_core_commit: str,
    evaluator_commit: str,
    training_seed: int,
    artifact_registrations: list[dict[str, object]],
) -> dict[str, object]:
    payload = {
        "schema_id": Pi1IdentitySourceRegistrationV1.SCHEMA_ID,
        "schema_version": 1,
        "logical_policy_id": logical_policy_id,
        "checkpoint_instance_id": checkpoint_instance_id,
        "base_model_id": base_model_id,
        "adapter_id": adapter_id,
        "tokenizer_identity": tokenizer_identity,
        "runtime_core_commit": runtime_core_commit,
        "evaluator_commit": evaluator_commit,
        "training_seed": training_seed,
        "artifact_registrations": artifact_registrations,
        "registration_sha256": "0" * 64,
    }
    payload["registration_sha256"] = domain_hash(
        Pi1IdentitySourceRegistrationV1.SCHEMA_ID,
        payload,
        excluded_field="registration_sha256",
    )
    Pi1IdentitySourceRegistrationV1.from_dict(payload)
    return payload


def _artifact_digest(item: ArtifactRegistrationV1) -> tuple[str, str]:
    path = Path(item.path)
    if item.kind == "FILE":
        source = ensure_regular_no_symlink(
            path, name=f"π1 artifact {item.name}"
        )
        return str(source), sha256_file(source)
    if item.kind == "DIRECTORY_MANIFEST":
        return str(path.resolve()), directory_manifest_sha256(path)

    source = ensure_regular_no_symlink(
        path,
        name=f"π1 manifest-value artifact {item.name}",
    )
    payload = require_object(
        "π1 manifest-value artifact",
        strict_json_loads(source.read_bytes()),
    )
    if item.name == "base_model_artifact":
        field_name = "weights_bundle_sha256"
    elif item.name == "adapter_artifact":
        field_name = "adapter_bundle_sha256"
    elif item.name == "tokenizer_artifact":
        field_name = "tokenizer_bundle_sha256"
    else:
        raise ValueError(
            "MANIFEST_VALUE_SHA256 is only valid for "
            "base/adapter/tokenizer artifacts"
        )
    observed = payload.get(field_name)
    require_sha256(field_name, observed)
    if observed != item.expected_sha256:
        raise ValueError(
            "manifest bundle SHA mismatch for "
            f"{item.name}: expected={item.expected_sha256}, observed={observed}"
        )
    return str(source), str(observed)


def _collect_checkpoint_registrations(value: object) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    if isinstance(value, dict):
        if {
            "logical_condition_id",
            "checkpoint_instance_id",
            "training_seed",
            "adapter_bundle_sha256",
        }.issubset(value):
            found.append(value)
        for child in value.values():
            found.extend(_collect_checkpoint_registrations(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_collect_checkpoint_registrations(child))
    return found


def materialize_pi1_reference_identity(
    registration: Pi1IdentitySourceRegistrationV1,
) -> dict[str, object]:
    bindings: dict[str, dict[str, object]] = {}
    for item in registration.artifact_registrations:
        resolved_path, observed_sha = _artifact_digest(item)
        if observed_sha != item.expected_sha256:
            raise ValueError(
                f"π1 artifact SHA mismatch for {item.name}: "
                f"expected={item.expected_sha256}, observed={observed_sha}"
            )
        bindings[item.name] = {
            "path": resolved_path,
            "sha256": observed_sha,
            "kind": item.kind,
        }

    runtime_path = Path(bindings["policy_runtime_manifest"]["path"])
    runtime = parse_canonical_json_file(runtime_path)
    registrations = _collect_checkpoint_registrations(runtime)
    matches = [
        item
        for item in registrations
        if item.get("logical_condition_id")
        == registration.logical_policy_id
        and item.get("checkpoint_instance_id")
        == registration.checkpoint_instance_id
        and item.get("training_seed") == registration.training_seed
    ]
    if len(matches) != 1:
        raise ValueError(
            "policy runtime must contain exactly one matching π1 checkpoint "
            f"registration, observed={len(matches)}"
        )
    match = matches[0]
    if (
        match.get("adapter_bundle_sha256")
        != bindings["adapter_artifact"]["sha256"]
    ):
        raise ValueError("runtime adapter SHA differs from registered artifact")

    identity = {
        "schema_id": "PI1_REFERENCE_IDENTITY_V1",
        "schema_version": 1,
        "logical_policy_id": registration.logical_policy_id,
        "checkpoint_instance_id": registration.checkpoint_instance_id,
        "base_model_id": registration.base_model_id,
        "base_model_artifact_sha256": bindings[
            "base_model_artifact"
        ]["sha256"],
        "adapter_id": registration.adapter_id,
        "adapter_artifact_sha256": bindings["adapter_artifact"]["sha256"],
        "tokenizer_identity": registration.tokenizer_identity,
        "tokenizer_artifact_sha256": bindings[
            "tokenizer_artifact"
        ]["sha256"],
        "chat_template_sha256": bindings["chat_template"]["sha256"],
        "policy_runtime_manifest_path": bindings[
            "policy_runtime_manifest"
        ]["path"],
        "policy_runtime_manifest_sha256": bindings[
            "policy_runtime_manifest"
        ]["sha256"],
        "decoding_contract_sha256": bindings["decoding_contract"]["sha256"],
        "raw_policy_prompt_protocol_sha256": bindings[
            "raw_policy_prompt_protocol"
        ]["sha256"],
        "runtime_core_commit": registration.runtime_core_commit,
        "evaluator_commit": registration.evaluator_commit,
        "training_config_path": bindings["training_config"]["path"],
        "training_config_sha256": bindings["training_config"]["sha256"],
        "training_data_manifest_path": bindings[
            "training_data_manifest"
        ]["path"],
        "training_data_manifest_sha256": bindings[
            "training_data_manifest"
        ]["sha256"],
        "training_seed": registration.training_seed,
        "reference_evaluation_manifest_path": bindings[
            "reference_evaluation_manifest"
        ]["path"],
        "reference_evaluation_manifest_sha256": bindings[
            "reference_evaluation_manifest"
        ]["sha256"],
        "materialization_source_artifact_sha256s": {
            key: value["sha256"] for key, value in bindings.items()
        },
        "source_registration_sha256": registration.registration_sha256,
        "identity_sha256": "0" * 64,
    }
    identity["identity_sha256"] = domain_hash(
        "PI1_REFERENCE_IDENTITY_V1",
        identity,
        excluded_field="identity_sha256",
    )
    return identity


def materialize_pi1_reference_identity_file(
    *,
    registration_path: Path,
    output_path: Path,
) -> dict[str, object]:
    registration = Pi1IdentitySourceRegistrationV1.from_file(
        registration_path
    )
    identity = materialize_pi1_reference_identity(registration)
    write_new_json(output_path, identity)
    return identity


def load_pi1_reference_identity(path: Path) -> dict[str, object]:
    payload = parse_canonical_json_file(path)
    required = {
        "schema_id",
        "schema_version",
        "logical_policy_id",
        "checkpoint_instance_id",
        "base_model_id",
        "base_model_artifact_sha256",
        "adapter_id",
        "adapter_artifact_sha256",
        "tokenizer_identity",
        "tokenizer_artifact_sha256",
        "chat_template_sha256",
        "policy_runtime_manifest_path",
        "policy_runtime_manifest_sha256",
        "decoding_contract_sha256",
        "raw_policy_prompt_protocol_sha256",
        "runtime_core_commit",
        "evaluator_commit",
        "training_config_path",
        "training_config_sha256",
        "training_data_manifest_path",
        "training_data_manifest_sha256",
        "training_seed",
        "reference_evaluation_manifest_path",
        "reference_evaluation_manifest_sha256",
        "materialization_source_artifact_sha256s",
        "source_registration_sha256",
        "identity_sha256",
    }
    exact_keyset(payload, required, name="PI1_REFERENCE_IDENTITY_V1")
    if payload["schema_id"] != "PI1_REFERENCE_IDENTITY_V1":
        raise ValueError("π1 identity schema mismatch")
    expected = domain_hash(
        "PI1_REFERENCE_IDENTITY_V1",
        payload,
        excluded_field="identity_sha256",
    )
    if payload["identity_sha256"] != expected:
        raise ValueError("π1 identity self-hash mismatch")
    return payload
