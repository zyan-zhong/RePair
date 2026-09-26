"""I1 structured-serialization constrained-decoding request contract.

This module does not alter E1PolicyRequestV1. I1 starts from the exact R0
wire dictionary and changes only ``structured_outputs`` to a JSON-schema
constraint whose ``action`` member is an unconstrained string.

The intervention is generation-time constrained decoding. It is not
post-processing, prose stripping, JSON extraction, or action repair.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from .canonical_evidence import canonical_json_bytes, sha256_bytes
from .policy_request import E1PolicyRequestV1


__all__ = [
    "I1_STRUCTURED_SERIALIZATION_SCHEMA_V1",
    "I1_STRUCTURED_SERIALIZATION_SCHEMA_SHA256",
    "I1StructuredPolicyRequestV1",
    "I2AdmissiblePolicyRequestV1",
    "i1_structured_serialization_schema_dict",
    "i2_admissible_action_schema_dict",
    "i2_admissible_action_schema_sha256",
]


def _deep_thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_deep_thaw(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return [_deep_thaw(item) for item in value]
    return value


I1_STRUCTURED_SERIALIZATION_SCHEMA_V1: Final[
    Mapping[str, object]
] = MappingProxyType(
    {
        "type": "object",
        "properties": MappingProxyType(
            {
                "action": MappingProxyType(
                    {
                        "type": "string",
                    }
                ),
            }
        ),
        "required": ("action",),
        "additionalProperties": False,
    }
)


def i1_structured_serialization_schema_dict() -> dict[str, object]:
    """Return a fresh JSON-serialisable copy of the frozen I1 schema."""

    value = _deep_thaw(I1_STRUCTURED_SERIALIZATION_SCHEMA_V1)
    if not isinstance(value, dict):
        raise AssertionError("I1 schema thaw did not produce dict")
    return value


I1_STRUCTURED_SERIALIZATION_SCHEMA_SHA256: Final[str] = sha256_bytes(
    canonical_json_bytes(i1_structured_serialization_schema_dict())
)


@dataclass(frozen=True, slots=True)
class I1StructuredPolicyRequestV1:
    """Exact E1 request plus one structured-output JSON constraint."""

    prompt_text: str
    seed: int
    request_id: str

    def __post_init__(self) -> None:
        E1PolicyRequestV1(
            prompt_text=self.prompt_text,
            seed=self.seed,
            request_id=self.request_id,
        )

    def to_wire_dict(self) -> dict[str, object]:
        payload = E1PolicyRequestV1(
            prompt_text=self.prompt_text,
            seed=self.seed,
            request_id=self.request_id,
        ).to_wire_dict()

        if payload.get("structured_outputs") is not None:
            raise AssertionError(
                "R0 request no longer has structured_outputs=None"
            )

        payload["structured_outputs"] = {
            "json": i1_structured_serialization_schema_dict(),
        }
        return payload

    def to_wire_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_wire_dict())



def _freeze_i2_admissible_commands(
    admissible_commands: Sequence[str],
) -> tuple[str, ...]:
    """Freeze an exact menu without sorting, deduplication or repair."""

    if isinstance(
        admissible_commands,
        (str, bytes, bytearray),
    ):
        raise TypeError(
            "admissible_commands must be a sequence of strings"
        )

    try:
        commands = tuple(admissible_commands)
    except TypeError as error:
        raise TypeError(
            "admissible_commands must be a sequence"
        ) from error

    if not commands:
        raise ValueError(
            "I2 JSON Schema enum requires a non-empty menu"
        )

    seen: list[str] = []
    for command in commands:
        if not isinstance(command, str):
            raise TypeError(
                "I2 admissible command members must be strings"
            )
        if command in seen:
            raise ValueError(
                "I2 cannot represent duplicate enum values "
                "without changing the menu"
            )
        seen.append(command)

    return commands


def i2_admissible_action_schema_dict(
    admissible_commands: Sequence[str],
) -> dict[str, object]:
    """Build the exact dynamic I2 JSON schema for one current menu."""

    commands = _freeze_i2_admissible_commands(
        admissible_commands
    )
    return {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": list(commands),
            }
        },
        "required": ["action"],
        "additionalProperties": False,
    }


def i2_admissible_action_schema_sha256(
    admissible_commands: Sequence[str],
) -> str:
    """Hash one exact dynamic I2 schema, including enum sequence."""

    return sha256_bytes(
        canonical_json_bytes(
            i2_admissible_action_schema_dict(
                admissible_commands
            )
        )
    )


@dataclass(frozen=True, slots=True)
class I2AdmissiblePolicyRequestV1:
    """Exact E1 request with action restricted to the current menu."""

    prompt_text: str
    seed: int
    request_id: str
    admissible_commands: tuple[str, ...]

    def __post_init__(self) -> None:
        E1PolicyRequestV1(
            prompt_text=self.prompt_text,
            seed=self.seed,
            request_id=self.request_id,
        )
        frozen = _freeze_i2_admissible_commands(
            self.admissible_commands
        )
        object.__setattr__(
            self,
            "admissible_commands",
            frozen,
        )

    def to_wire_dict(self) -> dict[str, object]:
        payload = E1PolicyRequestV1(
            prompt_text=self.prompt_text,
            seed=self.seed,
            request_id=self.request_id,
        ).to_wire_dict()

        if payload.get("structured_outputs") is not None:
            raise AssertionError(
                "R0 request no longer has structured_outputs=None"
            )

        payload["structured_outputs"] = {
            "json": i2_admissible_action_schema_dict(
                self.admissible_commands
            ),
        }
        return payload

    def to_wire_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_wire_dict())
