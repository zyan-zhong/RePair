from pchsi.evaluation.policy_client import PolicyClient
from pchsi.evaluation.policy_request import E1PolicyRequestV1
from pchsi.evaluation.rendered_prompt import RenderedPromptEvidence
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_text,
)


class Transport:
    def __init__(self):
        self.body = None

    def post_exact(self, *, path, body, headers):
        self.body = body
        response = {
            "id": "provider",
            "model": "Qwen2.5-3B-Instruct-E1",
            "choices": [
                {
                    "message": {"content": '{"action":"look"}'},
                    "finish_reason": "stop",
                    "token_ids": [9],
                }
            ],
            "usage": {
                "prompt_tokens": 2,
                "completion_tokens": 1,
            },
            "prompt_token_ids": [1, 2],
        }
        return (
            200,
            {
                "x-request-id": "provider",
                "content-type": "application/json",
            },
            canonical_json_bytes(response),
        )


def test_generate_with_evidence_preserves_exact_request_bytes():
    t = Transport()
    c = PolicyClient(
        transport=t,
        clock_ns=iter([0, 1_000_000]).__next__,
    )
    req = E1PolicyRequestV1("hello", 17, "c1")
    rendered = RenderedPromptEvidence(
        sha256_text("hello"),
        "a" * 64,
        sha256_text("rendered"),
        (1, 2),
        sha256_bytes(canonical_json_bytes([1, 2])),
        2,
        "rendered",
    )
    result = c.generate_with_evidence(
        request=req,
        expected_prompt=rendered,
    )
    assert (
        result.transport_evidence.request_wire_bytes
        == req.to_wire_bytes()
        == t.body
    )
    assert result.transport_evidence.raw_response_body.startswith(b"{")
