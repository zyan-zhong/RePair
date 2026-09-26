from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib

import pytest

from pchsi.evaluation.interface_isolation_request import (
    I1StructuredPolicyRequestV1,
    I2AdmissiblePolicyRequestV1,
    i1_structured_serialization_schema_dict,
    i2_admissible_action_schema_dict,
    i2_admissible_action_schema_sha256,
)
from pchsi.evaluation.policy_execution_profile import (
    I1_EXECUTION_PROFILE_V1,
    I2_EXECUTION_PROFILE_V1,
    R0_EXECUTION_PROFILE_V1,
)
from pchsi.evaluation.policy_request import E1PolicyRequestV1


R0_GOLDEN_WIRE_SHA256 = (
    "81156664eefa3e43c9c8771a23ec7ba7"
    "84ea8b781f78783c7b4b04baa37c1468"
)
I1_GOLDEN_WIRE_SHA256 = (
    "c242af154968bba82a94ae8febca725b"
    "279e7479e228489ea23989f793b316c0"
)


def _r0() -> E1PolicyRequestV1:
    return E1PolicyRequestV1(
        prompt_text="PROMPT\n",
        seed=17,
        request_id="req-1",
    )


def _i1() -> I1StructuredPolicyRequestV1:
    return I1StructuredPolicyRequestV1(
        prompt_text="PROMPT\n",
        seed=17,
        request_id="req-1",
    )


def _i2(menu=("go to desk 2", "look", "inventory")):
    return I2AdmissiblePolicyRequestV1(
        prompt_text="PROMPT\n",
        seed=17,
        request_id="req-1",
        admissible_commands=menu,
    )


def test_r0_and_i1_wire_bytes_remain_exactly_frozen() -> None:
    assert hashlib.sha256(
        _r0().to_wire_bytes()
    ).hexdigest() == R0_GOLDEN_WIRE_SHA256
    assert hashlib.sha256(
        _i1().to_wire_bytes()
    ).hexdigest() == I1_GOLDEN_WIRE_SHA256


def test_i1_schema_remains_enum_free() -> None:
    schema = i1_structured_serialization_schema_dict()
    assert schema == {
        "type": "object",
        "properties": {"action": {"type": "string"}},
        "required": ["action"],
        "additionalProperties": False,
    }
    assert "enum" not in schema["properties"]["action"]


def test_i2_schema_preserves_exact_menu_sequence() -> None:
    menu = (
        "go to desk 2",
        "go to desk 1",
        "look",
        "inventory",
    )
    schema = i2_admissible_action_schema_dict(menu)
    assert schema["properties"]["action"]["enum"] == list(menu)


def test_i2_schema_hash_is_sequence_sensitive() -> None:
    a = ("go to desk 1", "go to desk 2")
    b = ("go to desk 2", "go to desk 1")
    assert (
        i2_admissible_action_schema_sha256(a)
        != i2_admissible_action_schema_sha256(b)
    )


@pytest.mark.parametrize(
    "menu",
    [(), ("look", "look")],
)
def test_i2_rejects_unrepresentable_enum_menu(
    menu: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError):
        i2_admissible_action_schema_dict(menu)


def test_i2_rejects_non_string_menu_member() -> None:
    with pytest.raises(TypeError):
        i2_admissible_action_schema_dict(
            ("look", 3)  # type: ignore[arg-type]
        )


def test_i2_request_changes_only_structured_outputs() -> None:
    r0 = _r0().to_wire_dict()
    i2 = _i2().to_wire_dict()

    assert set(i2) == set(r0)
    assert {
        key
        for key in r0
        if r0[key] != i2[key]
    } == {"structured_outputs"}

    assert i2["structured_outputs"] == {
        "json": i2_admissible_action_schema_dict(
            ("go to desk 2", "look", "inventory")
        )
    }


def test_i2_request_freezes_input_menu() -> None:
    source = ["look", "inventory"]
    request = I2AdmissiblePolicyRequestV1(
        prompt_text="PROMPT",
        seed=17,
        request_id="r",
        admissible_commands=source,  # type: ignore[arg-type]
    )
    source.reverse()
    assert request.admissible_commands == ("look", "inventory")


def test_i2_request_is_immutable() -> None:
    request = _i2()
    with pytest.raises(FrozenInstanceError):
        request.seed = 31  # type: ignore[misc]


def test_profiles_keep_r0_i1_semantics_and_add_i2() -> None:
    r0 = R0_EXECUTION_PROFILE_V1
    i1 = I1_EXECUTION_PROFILE_V1
    i2 = I2_EXECUTION_PROFILE_V1

    assert r0.requires_current_admissible_commands is False
    assert i1.requires_current_admissible_commands is False
    assert i2.requires_current_admissible_commands is True
    assert i2.profile_id == "I2_EXECUTION_PROFILE_V1"
    assert i2.arm_id == "I2_ADMISSIBLE_ACTION_CONSTRAINT_V1"
    assert i2.policy_version == "ADMISSIBLE_ACTION_CONSTRAINT_V1"
    assert i2.requires_diagnostic_policy_call_evidence is True

    request = i2.build_request(
        prompt_text="PROMPT",
        seed=17,
        request_id="r",
        admissible_commands=("look", "inventory"),
    )
    assert isinstance(request, I2AdmissiblePolicyRequestV1)


def test_i2_profile_requires_current_menu() -> None:
    with pytest.raises(ValueError):
        I2_EXECUTION_PROFILE_V1.build_request(
            prompt_text="PROMPT",
            seed=17,
            request_id="r",
        )


def test_r0_i1_profiles_reject_accidental_dynamic_menu() -> None:
    for profile in (
        R0_EXECUTION_PROFILE_V1,
        I1_EXECUTION_PROFILE_V1,
    ):
        with pytest.raises(ValueError):
            profile.build_request(
                prompt_text="PROMPT",
                seed=17,
                request_id="r",
                admissible_commands=("look",),
            )
