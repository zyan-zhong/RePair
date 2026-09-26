"""Immutable policy-execution profiles.

The profile selects request construction and trace identity only.
It does not own prompt construction, menu handling, Runtime Core
logic, environment execution, artifact publication, or retry policy.
"""

from __future__ import annotations

from collections.abc import (
    Sequence,
)
from dataclasses import dataclass
from typing import (
    Protocol,
    runtime_checkable,
)

from .interface_isolation_request import (
    I1StructuredPolicyRequestV1,
    I2AdmissiblePolicyRequestV1,
)
from .policy_request import (
    E1PolicyRequestV1,
    PI0_SERVED_MODEL_NAME,
)


__all__ = [
    "PolicyRequestProtocol",
    "PolicyExecutionProfileV1",
    "R0_EXECUTION_PROFILE_V1",
    "I1_EXECUTION_PROFILE_V1",
    "I2_EXECUTION_PROFILE_V1",
]


@runtime_checkable
class PolicyRequestProtocol(
    Protocol
):
    prompt_text: str
    request_id: str

    def to_wire_dict(
        self,
    ) -> dict[str, object]:
        ...

    def to_wire_bytes(
        self,
    ) -> bytes:
        ...


@dataclass(
    frozen=True,
    slots=True,
)
class PolicyExecutionProfileV1:
    profile_id: str
    arm_id: str
    policy_version: str
    request_kind: str
    requires_diagnostic_policy_call_evidence: bool
    requires_current_admissible_commands: bool = False

    # The concrete model identity requested from vLLM.
    #
    # Defaulting to pi0 preserves all existing E1 / P1 callers.
    # Formal SELECT will later construct this profile explicitly
    # from its frozen PolicyCondition identity.
    served_model_name: str = (
        PI0_SERVED_MODEL_NAME
    )

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "profile_id",
            "arm_id",
            "policy_version",
            "request_kind",
            "served_model_name",
        ):
            value = getattr(
                self,
                name,
            )

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

        if self.request_kind not in {
            "R0",
            "I1",
            "I2",
        }:
            raise ValueError(
                "request_kind must be R0, I1 or I2"
            )

        if (
            type(
                self
                .requires_diagnostic_policy_call_evidence
            )
            is not bool
        ):
            raise TypeError(
                "requires_diagnostic_policy_call_evidence "
                "must be bool"
            )

        if (
            type(
                self
                .requires_current_admissible_commands
            )
            is not bool
        ):
            raise TypeError(
                "requires_current_admissible_commands "
                "must be bool"
            )

        # Current I1/I2 diagnostic request schemas remain frozen
        # to the original model version pi0. SELECT compatibility
        # only extends the normal R0 request semantics to a trained
        # LoRA realization.
        if (
            self.request_kind
            in {
                "I1",
                "I2",
            }
            and self.served_model_name
            != PI0_SERVED_MODEL_NAME
        ):
            raise ValueError(
                "I1/I2 served_model_name must remain pi0"
            )

    def build_request(
        self,
        *,
        prompt_text: str,
        seed: int,
        request_id: str,
        admissible_commands:
            Sequence[str]
            | None = None,
    ) -> PolicyRequestProtocol:

        if (
            self
            .requires_current_admissible_commands
        ):
            if (
                admissible_commands
                is None
            ):
                raise ValueError(
                    "this profile requires current "
                    "admissible commands"
                )

        elif (
            admissible_commands
            is not None
        ):
            raise ValueError(
                "R0/I1 request construction "
                "must not receive a dynamic "
                "admissible-menu argument"
            )

        if (
            self.request_kind
            == "R0"
        ):
            return E1PolicyRequestV1(
                prompt_text=
                    prompt_text,
                seed=
                    seed,
                request_id=
                    request_id,
                served_model_name=(
                    self
                    .served_model_name
                ),
            )

        if (
            self.request_kind
            == "I1"
        ):
            return (
                I1StructuredPolicyRequestV1(
                    prompt_text=
                        prompt_text,
                    seed=
                        seed,
                    request_id=
                        request_id,
                )
            )

        if (
            admissible_commands
            is None
        ):
            raise AssertionError(
                "I2 menu validation "
                "was bypassed"
            )

        return (
            I2AdmissiblePolicyRequestV1(
                prompt_text=
                    prompt_text,
                seed=
                    seed,
                request_id=
                    request_id,
                admissible_commands=
                    tuple(
                        admissible_commands
                    ),
            )
        )


R0_EXECUTION_PROFILE_V1 = (
    PolicyExecutionProfileV1(
        profile_id=(
            "R0_EXECUTION_PROFILE_V1"
        ),
        arm_id=(
            "R0_RAW_WITH_MENU_V1"
        ),
        policy_version=(
            "RAW_WITH_MENU_V1"
        ),
        request_kind="R0",
        requires_diagnostic_policy_call_evidence=False,
        requires_current_admissible_commands=False,
        served_model_name=(
            PI0_SERVED_MODEL_NAME
        ),
    )
)


I1_EXECUTION_PROFILE_V1 = (
    PolicyExecutionProfileV1(
        profile_id=(
            "I1_EXECUTION_PROFILE_V1"
        ),
        arm_id=(
            "I1_STRUCTURED_SERIALIZATION_CONSTRAINT_V1"
        ),
        policy_version=(
            "STRUCTURED_SERIALIZATION_CONSTRAINT_V1"
        ),
        request_kind="I1",
        requires_diagnostic_policy_call_evidence=True,
        requires_current_admissible_commands=False,
        served_model_name=(
            PI0_SERVED_MODEL_NAME
        ),
    )
)


I2_EXECUTION_PROFILE_V1 = (
    PolicyExecutionProfileV1(
        profile_id=(
            "I2_EXECUTION_PROFILE_V1"
        ),
        arm_id=(
            "I2_ADMISSIBLE_ACTION_CONSTRAINT_V1"
        ),
        policy_version=(
            "ADMISSIBLE_ACTION_CONSTRAINT_V1"
        ),
        request_kind="I2",
        requires_diagnostic_policy_call_evidence=True,
        requires_current_admissible_commands=True,
        served_model_name=(
            PI0_SERVED_MODEL_NAME
        ),
    )
)
