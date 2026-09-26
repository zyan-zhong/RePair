"""Fixture-safe ALFWorld/TextWorld runtime identity manifests."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import ClassVar

from .canonical_evidence import (
    canonical_json_text,
    strict_json_loads,
)
from .schema_contract import (
    validate_payload_against_schema,
)


_REQUIRED_SOURCE_NAMES = (
    "AlfredTWEnv",
    "AlfredDemangler",
    "AlfredInfos",
    "textworld.gym.register_games",
)
_REQUIRED_WRAPPER_ORDER = (
    "AlfredDemangler(shuffle=false)",
    "AlfredInfos",
)
_REQUIRED_ENV_INFOS = (
    "won",
    "admissible_commands",
    "extra.gamefile",
)


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    logical_name: str
    source_path: str
    sha256: str

    _KEYS: ClassVar[set[str]] = {
        "logical_name",
        "source_path",
        "sha256",
    }

    def __post_init__(self) -> None:
        if (
            not isinstance(self.logical_name, str)
            or not self.logical_name
        ):
            raise ValueError(
                "logical_name must be non-empty"
            )
        if (
            not isinstance(self.source_path, str)
            or not self.source_path
        ):
            raise ValueError(
                "source_path must be non-empty"
            )
        if not Path(self.source_path).is_absolute():
            raise ValueError(
                "source_path must be absolute"
            )
        if (
            len(self.sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.sha256
            )
        ):
            raise ValueError(
                "sha256 must be lowercase SHA-256"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_name": self.logical_name,
            "source_path": self.source_path,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "SourceIdentity":
        if not isinstance(value, dict):
            raise TypeError(
                "source identity must be an object"
            )
        if set(value) != cls._KEYS:
            raise ValueError(
                "source identity fields do not match"
            )
        return cls(
            logical_name=value["logical_name"],
            source_path=value["source_path"],
            sha256=value["sha256"],
        )


@dataclass(frozen=True, slots=True)
class EnvironmentRuntimeInputs:
    python_version: str
    python_executable_sha256: str
    alfworld_version: str
    textworld_version: str
    gym_version: str
    source_identities: tuple[SourceIdentity, ...]
    wrapper_order: tuple[str, ...]
    env_infos: tuple[str, ...]
    batch_size: int
    asynchronous: bool
    auto_reset: bool
    max_episode_steps: int
    process_start_method: str

    def __post_init__(self) -> None:
        for name in (
            "python_version",
            "alfworld_version",
            "textworld_version",
            "gym_version",
            "process_start_method",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be non-empty")

        if (
            len(self.python_executable_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.python_executable_sha256
            )
        ):
            raise ValueError(
                "python_executable_sha256 must be "
                "lowercase SHA-256"
            )

        if any(
            not isinstance(item, SourceIdentity)
            for item in self.source_identities
        ):
            raise TypeError(
                "source_identities must contain SourceIdentity"
            )

        if tuple(
            item.logical_name
            for item in self.source_identities
        ) != _REQUIRED_SOURCE_NAMES:
            raise ValueError(
                "source_identities must use the frozen "
                "logical-name order"
            )

        if self.wrapper_order != _REQUIRED_WRAPPER_ORDER:
            raise ValueError(
                "wrapper_order does not match frozen contract"
            )
        if self.env_infos != _REQUIRED_ENV_INFOS:
            raise ValueError(
                "env_infos does not match frozen contract"
            )
        if type(self.batch_size) is not int or self.batch_size != 1:
            raise ValueError("batch_size must be 1")
        if self.asynchronous is not False:
            raise ValueError("asynchronous must be false")
        if self.auto_reset is not False:
            raise ValueError("auto_reset must be false")
        if (
            type(self.max_episode_steps) is not int
            or self.max_episode_steps != 31
        ):
            raise ValueError(
                "max_episode_steps must be 31"
            )
        if self.process_start_method != "spawn":
            raise ValueError(
                "process_start_method must be spawn"
            )


@dataclass(frozen=True, slots=True)
class EnvironmentRuntimeManifestV1:
    SCHEMA_ID: ClassVar[str] = (
        "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1"
    )
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    manifest_id: str
    python_version: str
    python_executable_sha256: str
    alfworld_version: str
    textworld_version: str
    gym_version: str
    source_identities: tuple[SourceIdentity, ...]
    wrapper_order: tuple[str, ...]
    env_infos: tuple[str, ...]
    batch_size: int
    asynchronous: bool
    auto_reset: bool
    max_episode_steps: int
    process_start_method: str

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "manifest_id",
        "python_version",
        "python_executable_sha256",
        "alfworld_version",
        "textworld_version",
        "gym_version",
        "source_identities",
        "wrapper_order",
        "env_infos",
        "batch_size",
        "asynchronous",
        "auto_reset",
        "max_episode_steps",
        "process_start_method",
    }

    def __post_init__(self) -> None:
        EnvironmentRuntimeInputs(
            python_version=self.python_version,
            python_executable_sha256=(
                self.python_executable_sha256
            ),
            alfworld_version=self.alfworld_version,
            textworld_version=self.textworld_version,
            gym_version=self.gym_version,
            source_identities=self.source_identities,
            wrapper_order=self.wrapper_order,
            env_infos=self.env_infos,
            batch_size=self.batch_size,
            asynchronous=self.asynchronous,
            auto_reset=self.auto_reset,
            max_episode_steps=self.max_episode_steps,
            process_start_method=self.process_start_method,
        )
        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "python_version": self.python_version,
            "python_executable_sha256": (
                self.python_executable_sha256
            ),
            "alfworld_version": self.alfworld_version,
            "textworld_version": self.textworld_version,
            "gym_version": self.gym_version,
            "source_identities": [
                item.to_dict()
                for item in self.source_identities
            ],
            "wrapper_order": list(self.wrapper_order),
            "env_infos": list(self.env_infos),
            "batch_size": self.batch_size,
            "asynchronous": self.asynchronous,
            "auto_reset": self.auto_reset,
            "max_episode_steps": self.max_episode_steps,
            "process_start_method": (
                self.process_start_method
            ),
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "EnvironmentRuntimeManifestV1":
        if not isinstance(value, dict):
            raise TypeError(
                "environment runtime manifest must be an object"
            )
        if set(value) != cls._KEYS:
            raise ValueError(
                "environment runtime manifest fields do not match"
            )

        raw_sources = value["source_identities"]
        raw_wrappers = value["wrapper_order"]
        raw_infos = value["env_infos"]

        if not isinstance(raw_sources, list):
            raise TypeError(
                "source_identities must be a JSON array"
            )
        if not isinstance(raw_wrappers, list):
            raise TypeError(
                "wrapper_order must be a JSON array"
            )
        if not isinstance(raw_infos, list):
            raise TypeError(
                "env_infos must be a JSON array"
            )

        return cls(
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            manifest_id=value["manifest_id"],
            python_version=value["python_version"],
            python_executable_sha256=(
                value["python_executable_sha256"]
            ),
            alfworld_version=value["alfworld_version"],
            textworld_version=value["textworld_version"],
            gym_version=value["gym_version"],
            source_identities=tuple(
                SourceIdentity.from_dict(item)
                for item in raw_sources
            ),
            wrapper_order=tuple(raw_wrappers),
            env_infos=tuple(raw_infos),
            batch_size=value["batch_size"],
            asynchronous=value["asynchronous"],
            auto_reset=value["auto_reset"],
            max_episode_steps=value["max_episode_steps"],
            process_start_method=(
                value["process_start_method"]
            ),
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "EnvironmentRuntimeManifestV1":
        return cls.from_dict(strict_json_loads(value))


def _write_no_clobber(
    *,
    path: Path,
    payload: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError(
                    "short write while publishing runtime manifest"
                )
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_environment_runtime_manifest(
    *,
    inputs: EnvironmentRuntimeInputs,
    output_path: Path,
) -> EnvironmentRuntimeManifestV1:
    if not isinstance(inputs, EnvironmentRuntimeInputs):
        raise TypeError(
            "inputs must be EnvironmentRuntimeInputs"
        )

    manifest = EnvironmentRuntimeManifestV1(
        schema_id=(
            "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1"
        ),
        schema_version=1,
        manifest_id=(
            "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1"
        ),
        python_version=inputs.python_version,
        python_executable_sha256=(
            inputs.python_executable_sha256
        ),
        alfworld_version=inputs.alfworld_version,
        textworld_version=inputs.textworld_version,
        gym_version=inputs.gym_version,
        source_identities=inputs.source_identities,
        wrapper_order=inputs.wrapper_order,
        env_infos=inputs.env_infos,
        batch_size=inputs.batch_size,
        asynchronous=inputs.asynchronous,
        auto_reset=inputs.auto_reset,
        max_episode_steps=inputs.max_episode_steps,
        process_start_method=inputs.process_start_method,
    )

    _write_no_clobber(
        path=Path(output_path),
        payload=manifest.to_json().encode("utf-8"),
    )
    return manifest
