from __future__ import annotations

from dataclasses import FrozenInstanceError
import json

import pytest

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_text,
)
from pchsi.evaluation.interface_isolation_request import (
    I1StructuredPolicyRequestV1,
    i1_structured_serialization_schema_dict,
)
from pchsi.evaluation.policy_client import PolicyClient
from pchsi.evaluation.policy_execution_profile import (
    I1_EXECUTION_PROFILE_V1,
    R0_EXECUTION_PROFILE_V1,
)
from pchsi.evaluation.policy_request import E1PolicyRequestV1
from pchsi.evaluation.rendered_prompt import RenderedPromptEvidence


class _Transport:
    def __init__(self) -> None:
        self.calls: list[
            tuple[str, bytes, dict[str, str]]
        ] = []

    def post_exact(self, *, path: str, body: bytes, headers):
        self.calls.append((path, body, dict(headers)))
        response = {
            "id": "provider",
            "model": "Qwen2.5-3B-Instruct-E1",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": '{"action":"look"}',
                    },
                    "finish_reason": "stop",
                    "token_ids": [4],
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 1,
            },
            "prompt_token_ids": [1, 2, 3],
        }
        return (
            200,
            {"x-request-id": "provider"},
            json.dumps(response).encode("utf-8"),
        )


def _expected() -> RenderedPromptEvidence:
    ids = (1, 2, 3)
    return RenderedPromptEvidence(
        raw_policy_prompt_sha256=sha256_text("PROMPT"),
        chat_template_sha256="b" * 64,
        rendered_prompt_text_sha256=sha256_text("rendered"),
        rendered_token_ids=ids,
        rendered_token_ids_sha256=sha256_bytes(
            canonical_json_bytes(list(ids))
        ),
        prompt_token_count=3,
        rendered_prompt_text="rendered",
    )


def test_r0_profile_is_exact_default_contract() -> None:
    request = R0_EXECUTION_PROFILE_V1.build_request(
        prompt_text="PROMPT",
        seed=17,
        request_id="req",
    )

    assert isinstance(request, E1PolicyRequestV1)
    assert R0_EXECUTION_PROFILE_V1.arm_id == "R0_RAW_WITH_MENU_V1"
    assert (
        R0_EXECUTION_PROFILE_V1.policy_version
        == "RAW_WITH_MENU_V1"
    )
    assert (
        R0_EXECUTION_PROFILE_V1
        .requires_diagnostic_policy_call_evidence
        is False
    )


def test_i1_profile_builds_i1_request() -> None:
    request = I1_EXECUTION_PROFILE_V1.build_request(
        prompt_text="PROMPT",
        seed=17,
        request_id="req",
    )

    assert isinstance(request, I1StructuredPolicyRequestV1)
    assert (
        I1_EXECUTION_PROFILE_V1.arm_id
        == "I1_STRUCTURED_SERIALIZATION_CONSTRAINT_V1"
    )
    assert (
        I1_EXECUTION_PROFILE_V1.policy_version
        == "STRUCTURED_SERIALIZATION_CONSTRAINT_V1"
    )
    assert (
        I1_EXECUTION_PROFILE_V1
        .requires_diagnostic_policy_call_evidence
        is True
    )


def test_profiles_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        I1_EXECUTION_PROFILE_V1.arm_id = "other"  # type: ignore[misc]


def test_policy_client_sends_exact_i1_request_bytes() -> None:
    transport = _Transport()
    client = PolicyClient(
        transport=transport,
        clock_ns=iter([1_000_000, 2_000_000]).__next__,
    )
    request = I1_EXECUTION_PROFILE_V1.build_request(
        prompt_text="PROMPT",
        seed=17,
        request_id="client",
    )

    result = client.generate(
        request=request,
        expected_prompt=_expected(),
    )

    assert result.raw_response_text == '{"action":"look"}'
    assert len(transport.calls) == 1
    path, body, headers = transport.calls[0]

    assert path == "/v1/chat/completions"
    assert body == request.to_wire_bytes()
    assert headers["X-Request-Id"] == "client"

    payload = json.loads(body)
    assert payload["structured_outputs"] == {
        "json": i1_structured_serialization_schema_dict()
    }
