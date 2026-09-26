from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib

import pytest

from pchsi.evaluation.interface_isolation_request import (
    I1_STRUCTURED_SERIALIZATION_SCHEMA_SHA256,
    I1StructuredPolicyRequestV1,
    i1_structured_serialization_schema_dict,
)
from pchsi.evaluation.policy_request import E1PolicyRequestV1


R0_GOLDEN_WIRE_SHA256 = (
    "81156664eefa3e43c9c8771a23ec7ba7"
    "84ea8b781f78783c7b4b04baa37c1468"
)
I1_SCHEMA_GOLDEN_SHA256 = (
    "ddca85be85528f1720614e9bfad1fd59"
    "9f975737a43c51da130a402b312cce6a"
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


def test_r0_wire_bytes_remain_frozen() -> None:
    request = _r0()
    assert hashlib.sha256(
        request.to_wire_bytes()
    ).hexdigest() == R0_GOLDEN_WIRE_SHA256
    assert request.to_wire_dict()["structured_outputs"] is None


def test_i1_schema_is_action_string_only_without_enum() -> None:
    schema = i1_structured_serialization_schema_dict()

    assert schema == {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
            },
        },
        "required": ["action"],
        "additionalProperties": False,
    }
    action_schema = schema["properties"]["action"]
    assert isinstance(action_schema, dict)
    assert "enum" not in action_schema


def test_i1_schema_sha256_is_frozen() -> None:
    assert (
        I1_STRUCTURED_SERIALIZATION_SCHEMA_SHA256
        == I1_SCHEMA_GOLDEN_SHA256
    )


def test_i1_changes_only_structured_outputs_semantics() -> None:
    r0 = _r0().to_wire_dict()
    i1 = _i1().to_wire_dict()

    assert set(i1) == set(r0)
    assert {
        key
        for key in r0
        if r0[key] != i1[key]
    } == {"structured_outputs"}

    assert i1["structured_outputs"] == {
        "json": i1_structured_serialization_schema_dict()
    }

    for forbidden in (
        "response_format",
        "guided_json",
        "guided_regex",
        "guided_choice",
        "guided_grammar",
        "logits_processors",
        "vllm_xargs",
    ):
        assert forbidden not in i1


def test_i1_preserves_r0_sampling_and_message_semantics() -> None:
    r0 = _r0().to_wire_dict()
    i1 = _i1().to_wire_dict()

    for key in (
        "model",
        "messages",
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
        "n",
        "stream",
        "truncate_prompt_tokens",
        "return_token_ids",
        "request_id",
    ):
        assert i1[key] == r0[key]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "prompt_text": "",
            "seed": 17,
            "request_id": "r",
        },
        {
            "prompt_text": "P",
            "seed": -1,
            "request_id": "r",
        },
        {
            "prompt_text": "P",
            "seed": 17,
            "request_id": "",
        },
    ],
)
def test_i1_reuses_r0_request_validation(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        I1StructuredPolicyRequestV1(
            **kwargs  # type: ignore[arg-type]
        )


def test_i1_request_is_immutable() -> None:
    request = _i1()

    with pytest.raises(FrozenInstanceError):
        request.seed = 31  # type: ignore[misc]
