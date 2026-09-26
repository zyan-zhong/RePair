"""Frozen runtime identities for P4 Harness-OFF SELECT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Self

from .canonical_evidence import (
    canonical_json_text,
    require_lower_sha256,
    strict_json_loads,
)
from .schema_contract import (
    validate_payload_against_schema,
)


PI0_CONDITION_ID = "P4-R0-PI0"
PI0_SERVED_MODEL_NAME = "Qwen2.5-3B-Instruct-E1"

PI1_LOGICAL_CONDITION_ID = "P4-R1-Q2-BAD"

FROZEN_BASE_MODEL_REPOSITORY = (
    "Qwen/Qwen2.5-3B-Instruct"
)

FROZEN_BASE_MODEL_REVISION = (
    "aa8e72537993ba99e69dfaafa59ed015b17504d1"
)


def _mapping(
    value: object,
) -> dict[str, object]:
    if not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            "runtime manifest wire value must be object"
        )

    if any(
        not isinstance(
            key,
            str,
        )
        for key in value
    ):
        raise TypeError(
            "runtime manifest keys must be strings"
        )

    return value


def _expect_keys(
    payload: dict[str, object],
    expected: set[str],
) -> None:
    observed = set(
        payload
    )

    missing = sorted(
        expected - observed
    )

    unknown = sorted(
        observed - expected
    )

    if missing:
        raise ValueError(
            "runtime manifest missing fields: "
            f"{missing}"
        )

    if unknown:
        raise ValueError(
            "runtime manifest contains "
            f"unknown fields: {unknown}"
        )


def _text(
    name: str,
    value: object,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or not value
    ):
        raise ValueError(
            f"{name} must be non-empty str"
        )

    if any(
        char in value
        for char in (
            "\x00",
            "\r",
            "\n",
        )
    ):
        raise ValueError(
            f"{name} contains forbidden characters"
        )

    return value


def _optional_text(
    name: str,
    value: object,
) -> str | None:
    if value is None:
        return None

    return _text(
        name,
        value,
    )


def _optional_sha256(
    name: str,
    value: object,
) -> str | None:
    if value is None:
        return None

    require_lower_sha256(
        name,
        value,
    )

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class SelectStaticLoRARegistrationV1:
    logical_condition_id: str
    checkpoint_instance_id: str
    training_seed: int
    served_model_name: str
    adapter_path: str
    adapter_bundle_sha256: str
    adapter_rank: int

    _KEYS: ClassVar[set[str]] = {
        "logical_condition_id",
        "checkpoint_instance_id",
        "training_seed",
        "served_model_name",
        "adapter_path",
        "adapter_bundle_sha256",
        "adapter_rank",
    }

    def __post_init__(
        self,
    ) -> None:
        _text(
            "logical_condition_id",
            self.logical_condition_id,
        )

        if (
            self.logical_condition_id
            == PI0_CONDITION_ID
        ):
            raise ValueError(
                "LoRA registration may not use pi0 logical condition"
            )

        for name in (
            "checkpoint_instance_id",
            "served_model_name",
            "adapter_path",
        ):
            _text(
                name,
                getattr(
                    self,
                    name,
                ),
            )

        require_lower_sha256(
            "adapter_bundle_sha256",
            self.adapter_bundle_sha256,
        )

        if (
            type(
                self.training_seed
            )
            is not int
            or self.training_seed < 0
        ):
            raise ValueError(
                "training_seed must be non-negative int"
            )

        if (
            self.adapter_rank
            != 16
        ):
            raise ValueError(
                "adapter_rank must be 16"
            )

        if (
            self.checkpoint_instance_id
            != self.served_model_name
        ):
            raise ValueError(
                "checkpoint and served-model identity mismatch"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "logical_condition_id":
                self.logical_condition_id,
            "checkpoint_instance_id":
                self.checkpoint_instance_id,
            "training_seed":
                self.training_seed,
            "served_model_name":
                self.served_model_name,
            "adapter_path":
                self.adapter_path,
            "adapter_bundle_sha256":
                self.adapter_bundle_sha256,
            "adapter_rank":
                self.adapter_rank,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> Self:
        payload = _mapping(
            value
        )

        _expect_keys(
            payload,
            cls._KEYS,
        )

        return cls(
            logical_condition_id=(
                payload[
                    "logical_condition_id"
                ]
            ),
            checkpoint_instance_id=(
                payload[
                    "checkpoint_instance_id"
                ]
            ),
            training_seed=(
                payload[
                    "training_seed"
                ]
            ),
            served_model_name=(
                payload[
                    "served_model_name"
                ]
            ),
            adapter_path=(
                payload[
                    "adapter_path"
                ]
            ),
            adapter_bundle_sha256=(
                payload[
                    "adapter_bundle_sha256"
                ]
            ),
            adapter_rank=(
                payload[
                    "adapter_rank"
                ]
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SelectServerRuntimeManifestV1:
    SCHEMA_ID: ClassVar[str] = (
        "SELECT_SERVER_RUNTIME_MANIFEST_V1"
    )
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    manifest_id: str

    vllm_version: str

    base_model_repository: str
    base_model_revision: str

    tokenizer_identity_manifest_sha256: str
    chat_template_sha256: str

    dtype: str
    tensor_parallel_size: int
    generation_config_mode: str
    chat_template_content_format: str

    enable_lora: bool
    max_lora_rank: int
    max_loras: int
    max_cpu_loras: int
    lora_dtype: str

    runtime_dynamic_lora_updates: bool

    static_lora_registry: tuple[
        SelectStaticLoRARegistrationV1,
        ...,
    ]

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "manifest_id",
        "vllm_version",
        "base_model_repository",
        "base_model_revision",
        "tokenizer_identity_manifest_sha256",
        "chat_template_sha256",
        "dtype",
        "tensor_parallel_size",
        "generation_config_mode",
        "chat_template_content_format",
        "enable_lora",
        "max_lora_rank",
        "max_loras",
        "max_cpu_loras",
        "lora_dtype",
        "runtime_dynamic_lora_updates",
        "static_lora_registry",
    }

    def __post_init__(
        self,
    ) -> None:
        if (
            self.schema_id
            != self.SCHEMA_ID
        ):
            raise ValueError(
                "schema_id mismatch"
            )

        if (
            self.schema_version
            != self.SCHEMA_VERSION
        ):
            raise ValueError(
                "schema_version mismatch"
            )

        _text(
            "manifest_id",
            self.manifest_id,
        )

        if (
            self.vllm_version
            != "0.11.0"
        ):
            raise ValueError(
                "vllm_version must remain 0.11.0"
            )

        if (
            self.base_model_repository
            != FROZEN_BASE_MODEL_REPOSITORY
        ):
            raise ValueError(
                "base model repository mismatch"
            )

        if (
            self.base_model_revision
            != FROZEN_BASE_MODEL_REVISION
        ):
            raise ValueError(
                "base model revision mismatch"
            )

        require_lower_sha256(
            "tokenizer_identity_manifest_sha256",
            self.tokenizer_identity_manifest_sha256,
        )

        require_lower_sha256(
            "chat_template_sha256",
            self.chat_template_sha256,
        )

        if (
            self.dtype
            != "bfloat16"
        ):
            raise ValueError(
                "dtype must remain bfloat16"
            )

        if (
            self.tensor_parallel_size
            != 1
        ):
            raise ValueError(
                "tensor_parallel_size must remain 1"
            )

        if (
            self.generation_config_mode
            != "vllm"
        ):
            raise ValueError(
                "generation_config_mode mismatch"
            )

        if (
            self.chat_template_content_format
            != "string"
        ):
            raise ValueError(
                "chat template format mismatch"
            )

        if (
            self.enable_lora
            is not True
        ):
            raise ValueError(
                "SELECT server must enable LoRA"
            )

        if (
            self.max_lora_rank
            != 16
        ):
            raise ValueError(
                "max_lora_rank must be 16"
            )

        if (
            self.max_loras
            != 1
        ):
            raise ValueError(
                "max_loras must be 1"
            )

        if (
            type(
                self.max_cpu_loras
            )
            is not int
            or self.max_cpu_loras < 1
        ):
            raise ValueError(
                "max_cpu_loras must be positive int"
            )

        if (
            self.max_cpu_loras
            < self.max_loras
        ):
            raise ValueError(
                "max_cpu_loras must be >= max_loras"
            )

        if (
            self.lora_dtype
            != "auto"
        ):
            raise ValueError(
                "lora_dtype must remain auto"
            )

        if (
            self.runtime_dynamic_lora_updates
            is not False
        ):
            raise ValueError(
                "runtime dynamic LoRA updates are forbidden"
            )

        if (
            type(
                self.static_lora_registry
            )
            is not tuple
        ):
            raise TypeError(
                "static_lora_registry must be tuple"
            )

        if (
            not self.static_lora_registry
        ):
            raise ValueError(
                "static_lora_registry must not be empty"
            )

        if (
            self.max_cpu_loras
            < len(
                self.static_lora_registry
            )
        ):
            raise ValueError(
                "max_cpu_loras must cover the static LoRA registry"
            )

        if any(
            type(item)
            is not SelectStaticLoRARegistrationV1
            for item
            in self.static_lora_registry
        ):
            raise TypeError(
                "invalid static LoRA registration"
            )

        names = tuple(
            item.served_model_name
            for item
            in self.static_lora_registry
        )

        logical_seed_pairs = tuple(
            (
                item.logical_condition_id,
                item.training_seed,
            )
            for item
            in self.static_lora_registry
        )

        checkpoints = tuple(
            item.checkpoint_instance_id
            for item
            in self.static_lora_registry
        )

        if (
            len(set(names))
            != len(names)
        ):
            raise ValueError(
                "duplicate served model identity"
            )

        if (
            len(set(logical_seed_pairs))
            != len(logical_seed_pairs)
        ):
            raise ValueError(
                "duplicate logical-condition/training-seed identity"
            )

        if (
            len(set(checkpoints))
            != len(checkpoints)
        ):
            raise ValueError(
                "duplicate checkpoint identity"
            )

        validate_payload_against_schema(
            schema_id=(
                self.SCHEMA_ID
            ),
            payload=(
                self.to_dict()
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema_id":
                self.schema_id,
            "schema_version":
                self.schema_version,
            "manifest_id":
                self.manifest_id,
            "vllm_version":
                self.vllm_version,
            "base_model_repository":
                self.base_model_repository,
            "base_model_revision":
                self.base_model_revision,
            "tokenizer_identity_manifest_sha256":
                self.tokenizer_identity_manifest_sha256,
            "chat_template_sha256":
                self.chat_template_sha256,
            "dtype":
                self.dtype,
            "tensor_parallel_size":
                self.tensor_parallel_size,
            "generation_config_mode":
                self.generation_config_mode,
            "chat_template_content_format":
                self.chat_template_content_format,
            "enable_lora":
                self.enable_lora,
            "max_lora_rank":
                self.max_lora_rank,
            "max_loras":
                self.max_loras,
            "max_cpu_loras":
                self.max_cpu_loras,
            "lora_dtype":
                self.lora_dtype,
            "runtime_dynamic_lora_updates":
                self.runtime_dynamic_lora_updates,
            "static_lora_registry": [
                item.to_dict()
                for item
                in self.static_lora_registry
            ],
        }

    def to_json(
        self,
    ) -> str:
        return canonical_json_text(
            self.to_dict()
        )

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> Self:
        payload = _mapping(
            value
        )

        _expect_keys(
            payload,
            cls._KEYS,
        )

        validate_payload_against_schema(
            schema_id=(
                cls.SCHEMA_ID
            ),
            payload=(
                payload
            ),
        )

        registry = payload[
            "static_lora_registry"
        ]

        if not isinstance(
            registry,
            list,
        ):
            raise TypeError(
                "static_lora_registry must be JSON array"
            )

        return cls(
            schema_id=(
                payload["schema_id"]
            ),
            schema_version=(
                payload[
                    "schema_version"
                ]
            ),
            manifest_id=(
                payload["manifest_id"]
            ),
            vllm_version=(
                payload["vllm_version"]
            ),
            base_model_repository=(
                payload[
                    "base_model_repository"
                ]
            ),
            base_model_revision=(
                payload[
                    "base_model_revision"
                ]
            ),
            tokenizer_identity_manifest_sha256=(
                payload[
                    "tokenizer_identity_manifest_sha256"
                ]
            ),
            chat_template_sha256=(
                payload[
                    "chat_template_sha256"
                ]
            ),
            dtype=(
                payload["dtype"]
            ),
            tensor_parallel_size=(
                payload[
                    "tensor_parallel_size"
                ]
            ),
            generation_config_mode=(
                payload[
                    "generation_config_mode"
                ]
            ),
            chat_template_content_format=(
                payload[
                    "chat_template_content_format"
                ]
            ),
            enable_lora=(
                payload[
                    "enable_lora"
                ]
            ),
            max_lora_rank=(
                payload[
                    "max_lora_rank"
                ]
            ),
            max_loras=(
                payload[
                    "max_loras"
                ]
            ),
            max_cpu_loras=(
                payload[
                    "max_cpu_loras"
                ]
            ),
            lora_dtype=(
                payload[
                    "lora_dtype"
                ]
            ),
            runtime_dynamic_lora_updates=(
                payload[
                    "runtime_dynamic_lora_updates"
                ]
            ),
            static_lora_registry=tuple(
                SelectStaticLoRARegistrationV1
                .from_dict(
                    item
                )
                for item in registry
            ),
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> Self:
        return cls.from_dict(
            strict_json_loads(
                value
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SelectPolicyRuntimeManifestV1:
    SCHEMA_ID: ClassVar[str] = (
        "SELECT_POLICY_RUNTIME_MANIFEST_V1"
    )
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    manifest_id: str

    server_runtime_manifest_sha256: str

    policy_condition_id: str
    logical_condition_id: str
    checkpoint_instance_id: str
    training_seed: int | None

    # No default:
    # formal SELECT must explicitly state the model.
    served_model_name: str

    adapter_path: str | None
    adapter_bundle_sha256: str | None
    adapter_rank: int | None

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "manifest_id",
        "server_runtime_manifest_sha256",
        "policy_condition_id",
        "logical_condition_id",
        "checkpoint_instance_id",
        "training_seed",
        "served_model_name",
        "adapter_path",
        "adapter_bundle_sha256",
        "adapter_rank",
    }

    def __post_init__(
        self,
    ) -> None:
        if (
            self.schema_id
            != self.SCHEMA_ID
        ):
            raise ValueError(
                "schema_id mismatch"
            )

        if (
            self.schema_version
            != self.SCHEMA_VERSION
        ):
            raise ValueError(
                "schema_version mismatch"
            )

        _text(
            "manifest_id",
            self.manifest_id,
        )

        require_lower_sha256(
            "server_runtime_manifest_sha256",
            self.server_runtime_manifest_sha256,
        )

        for name in (
            "policy_condition_id",
            "logical_condition_id",
            "checkpoint_instance_id",
            "served_model_name",
        ):
            _text(
                name,
                getattr(
                    self,
                    name,
                ),
            )

        if (
            self.policy_condition_id
            != self.checkpoint_instance_id
        ):
            raise ValueError(
                "policy/checkpoint identity mismatch"
            )

        if (
            self.logical_condition_id
            == PI0_CONDITION_ID
        ):
            if (
                self.policy_condition_id
                != PI0_CONDITION_ID
            ):
                raise ValueError(
                    "pi0 policy identity mismatch"
                )

            if (
                self.served_model_name
                != PI0_SERVED_MODEL_NAME
            ):
                raise ValueError(
                    "pi0 served-model identity mismatch"
                )

            if (
                self.training_seed
                is not None
            ):
                raise ValueError(
                    "pi0 must not have training_seed"
                )

            if any(
                value is not None
                for value in (
                    self.adapter_path,
                    self.adapter_bundle_sha256,
                    self.adapter_rank,
                )
            ):
                raise ValueError(
                    "pi0 must not bind project LoRA"
                )

        else:
            if (
                type(
                    self.training_seed
                )
                is not int
                or self.training_seed < 0
            ):
                raise ValueError(
                    "pi1 requires explicit training_seed"
                )

            _text(
                "adapter_path",
                self.adapter_path,
            )

            require_lower_sha256(
                "adapter_bundle_sha256",
                self.adapter_bundle_sha256,
            )

            if (
                self.adapter_rank
                != 16
            ):
                raise ValueError(
                    "pi1 adapter_rank must be 16"
                )

            if (
                self.served_model_name
                == PI0_SERVED_MODEL_NAME
            ):
                raise ValueError(
                    "pi1 may not reuse pi0 served-model identity"
                )

        _optional_text(
            "adapter_path",
            self.adapter_path,
        )

        _optional_sha256(
            "adapter_bundle_sha256",
            self.adapter_bundle_sha256,
        )

        validate_payload_against_schema(
            schema_id=(
                self.SCHEMA_ID
            ),
            payload=(
                self.to_dict()
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema_id":
                self.schema_id,
            "schema_version":
                self.schema_version,
            "manifest_id":
                self.manifest_id,
            "server_runtime_manifest_sha256":
                self.server_runtime_manifest_sha256,
            "policy_condition_id":
                self.policy_condition_id,
            "logical_condition_id":
                self.logical_condition_id,
            "checkpoint_instance_id":
                self.checkpoint_instance_id,
            "training_seed":
                self.training_seed,
            "served_model_name":
                self.served_model_name,
            "adapter_path":
                self.adapter_path,
            "adapter_bundle_sha256":
                self.adapter_bundle_sha256,
            "adapter_rank":
                self.adapter_rank,
        }

    def to_json(
        self,
    ) -> str:
        return canonical_json_text(
            self.to_dict()
        )

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> Self:
        payload = _mapping(
            value
        )

        _expect_keys(
            payload,
            cls._KEYS,
        )

        validate_payload_against_schema(
            schema_id=(
                cls.SCHEMA_ID
            ),
            payload=(
                payload
            ),
        )

        return cls(
            schema_id=(
                payload["schema_id"]
            ),
            schema_version=(
                payload[
                    "schema_version"
                ]
            ),
            manifest_id=(
                payload["manifest_id"]
            ),
            server_runtime_manifest_sha256=(
                payload[
                    "server_runtime_manifest_sha256"
                ]
            ),
            policy_condition_id=(
                payload[
                    "policy_condition_id"
                ]
            ),
            logical_condition_id=(
                payload[
                    "logical_condition_id"
                ]
            ),
            checkpoint_instance_id=(
                payload[
                    "checkpoint_instance_id"
                ]
            ),
            training_seed=(
                payload[
                    "training_seed"
                ]
            ),
            served_model_name=(
                payload[
                    "served_model_name"
                ]
            ),
            adapter_path=(
                payload[
                    "adapter_path"
                ]
            ),
            adapter_bundle_sha256=(
                payload[
                    "adapter_bundle_sha256"
                ]
            ),
            adapter_rank=(
                payload[
                    "adapter_rank"
                ]
            ),
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> Self:
        return cls.from_dict(
            strict_json_loads(
                value
            )
        )
