from __future__ import annotations

import json
import pytest

from pchsi.evaluation.openai_responses_policy import (
    OpenAIPolicyCallLedgerV1,
    OpenAIResponsesPolicyClientV1,
    OpenAIResponsesPolicyError,
    OpenAIResponsesPolicyRequestV1,
    parse_openai_response,
)


def response_bytes(model: str = "gpt-5.6-sol") -> bytes:
    return json.dumps(
        {
            "id": "resp_123",
            "model": model,
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"action":"look"}',
                        }
                    ],
                }
            ],
            "usage": {
                "input_tokens": 90,
                "output_tokens": 7,
                "output_tokens_details": {"reasoning_tokens": 0},
            },
        },
        separators=(",", ":"),
    ).encode()


def test_high_reasoning_request_is_stateless_tool_free_and_unconstrained() -> None:
    request = OpenAIResponsesPolicyRequestV1(
        prompt_text="prompt",
        request_id="r1",
    )
    body = request.to_wire_dict()
    assert body["model"] == "gpt-5.6-sol"
    assert body["store"] is False
    assert body["tools"] == []
    assert body["reasoning"] == {
        "effort": "high",
        "context": "current_turn",
    }
    assert body["max_output_tokens"] == 32768
    assert body["truncation"] == "disabled"
    assert "previous_response_id" not in body
    assert "conversation" not in body
    assert "text" not in body
    assert "response_format" not in body


def test_direct_arm_uses_visible_output_ceiling() -> None:
    request = OpenAIResponsesPolicyRequestV1(
        prompt_text="prompt",
        request_id="r1",
        reasoning_effort="none",
        max_output_tokens=128,
    )
    assert request.to_wire_dict()["max_output_tokens"] == 128


def test_response_parser_preserves_raw_output_and_usage() -> None:
    parsed = parse_openai_response(response_bytes())
    assert parsed.output_text == '{"action":"look"}'
    assert parsed.input_tokens == 90
    assert parsed.output_tokens == 7
    assert parsed.reasoning_tokens == 0


def test_reservation_blocks_duplicate_before_second_transport(tmp_path) -> None:
    calls: list[str] = []

    def transport(*, api_key: str, body: bytes, client_request_id: str):
        calls.append(client_request_id)
        return 200, {"content-type": "application/json"}, response_bytes()

    client = OpenAIResponsesPolicyClientV1(
        api_key="key",
        ledger=OpenAIPolicyCallLedgerV1(tmp_path),
        transport=transport,
    )
    request = OpenAIResponsesPolicyRequestV1(
        prompt_text="prompt",
        request_id="r1",
    )
    generation = client.generate(request=request, expected_prompt=object())
    assert generation.raw_response_text == '{"action":"look"}'
    assert calls == ["r1"]

    with pytest.raises(FileExistsError):
        client.generate(request=request, expected_prompt=object())
    assert calls == ["r1"]


def test_returned_model_mismatch_fails_closed(tmp_path) -> None:
    def transport(*, api_key: str, body: bytes, client_request_id: str):
        return 200, {}, response_bytes(model="different-model")

    client = OpenAIResponsesPolicyClientV1(
        api_key="key",
        ledger=OpenAIPolicyCallLedgerV1(tmp_path),
        transport=transport,
    )
    with pytest.raises(OpenAIResponsesPolicyError, match="returned model"):
        client.generate(
            request=OpenAIResponsesPolicyRequestV1("prompt", "r1"),
            expected_prompt=object(),
        )
    failure = tmp_path / "r1" / "POST_TRANSPORT_FAILURE.json"
    assert failure.is_file()
    assert "RETURNED_MODEL_MISMATCH" in failure.read_text(encoding="utf-8")
