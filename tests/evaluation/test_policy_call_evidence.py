import base64
import pytest

from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_text,
)
from pchsi.evaluation.policy_call_evidence import (
    PolicyCallEvidenceV1,
    allowlisted_response_headers,
    exact_policy_call_payload,
    semantic_policy_call_payload,
)
from pchsi.evaluation.raw_policy_prompt import (
    sha256_executed_transitions,
)


def evidence(latency=7, client="c1"):
    request_dict = {
        "model": "m",
        "request_id": client,
    }
    req = canonical_json_bytes(request_dict)
    semantic_request = {
        "model": "m",
    }
    semantic_json = canonical_json_text(semantic_request)
    raw_text = "{}"
    body = canonical_json_bytes(
        {
            "id": "provider",
            "choices": [
                {
                    "message": {"content": raw_text},
                    "finish_reason": "stop",
                    "token_ids": [3],
                }
            ],
            "usage": {
                "prompt_tokens": 2,
                "completion_tokens": 1,
            },
            "prompt_token_ids": [1, 2],
        }
    )
    prompt = "hello"
    rendered = "<u>hello</u>"
    return PolicyCallEvidenceV1(
        "POLICY_CALL_EVIDENCE_V1",
        1,
        0,
        0,
        client,
        "p1",
        prompt,
        sha256_text(prompt),
        rendered,
        sha256_text(rendered),
        (1, 2),
        2,
        semantic_json,
        sha256_text(semantic_json),
        base64.b64encode(req).decode(),
        sha256_bytes(req),
        200,
        tuple(
            allowlisted_response_headers(
                {
                    "x-request-id": "p1",
                    "content-type": "application/json",
                }
            ).items()
        ),
        base64.b64encode(body).decode(),
        sha256_bytes(body),
        raw_text,
        sha256_text(raw_text),
        "stop",
        2,
        1,
        (1, 2),
        (3,),
        latency,
        "goal",
        sha256_text("goal"),
        "obs",
        sha256_text("obs"),
        ("look",),
        sha256_string_sequence(("look",)),
        (),
        sha256_executed_transitions(()),
        None,
        (
            ("policy_attempt_count", 0),
            ("environment_step_count", 0),
            ("protocol_failure_count", 0),
            ("inadmissible_action_count", 0),
            ("consecutive_nonexecuted_attempt_count", 0),
        ),
    )


def test_exact_bytes_roundtrip():
    e = evidence()
    assert b'"request_id":"c1"' in e.request_wire_bytes
    assert e.raw_response_body.startswith(b"{")


def test_secret_header_rejected():
    with pytest.raises(ValueError):
        allowlisted_response_headers({"Authorization": "secret"})


def test_operational_changes_leave_semantic_projection_stable():
    a = evidence(7, "c1")
    b = evidence(99, "c2")
    assert exact_policy_call_payload(a) != exact_policy_call_payload(b)
    assert semantic_policy_call_payload(a) == semantic_policy_call_payload(b)


def test_semantic_request_is_bound_to_exact_request():
    e = evidence()
    payload = e.to_dict()
    payload["request_semantics_json"] = '{"model":"other"}\n'
    payload["request_semantics_sha256"] = sha256_text(
        payload["request_semantics_json"]
    )
    with pytest.raises(ValueError, match="request semantics"):
        PolicyCallEvidenceV1.from_dict(payload)
