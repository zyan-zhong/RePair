from __future__ import annotations
from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.evaluation.policy_request import E1PolicyRequestV1

EXPECTED_KEYS = {
    "model","messages","temperature","top_p","max_tokens","seed","n","stream","stop",
    "presence_penalty","frequency_penalty","logprobs","top_logprobs","best_of","use_beam_search",
    "top_k","min_p","repetition_penalty","length_penalty","stop_token_ids",
    "include_stop_str_in_output","ignore_eos","min_tokens","skip_special_tokens",
    "spaces_between_special_tokens","truncate_prompt_tokens","prompt_logprobs","allowed_token_ids",
    "bad_words","echo","add_generation_prompt","continue_final_message","add_special_tokens",
    "documents","chat_template","chat_template_kwargs","structured_outputs","priority",
    "return_token_ids","request_id",
}
FORBIDDEN = {"tools","tool_choice","parallel_tool_calls","response_format","guided_json","guided_regex","guided_choice","guided_grammar","logits_processors","vllm_xargs"}

def _request(): return E1PolicyRequestV1(prompt_text="PROMPT\n", seed=17, request_id="req-1")

def test_policy_request_has_exact_key_set_and_canonical_bytes() -> None:
    payload=_request().to_wire_dict()
    assert set(payload)==EXPECTED_KEYS
    assert _request().to_wire_bytes()==canonical_json_bytes(payload)
    assert payload["model"]=="Qwen2.5-3B-Instruct-E1"
    assert payload["messages"]==[{"role":"user","content":"PROMPT\n"}]
    assert payload["temperature"]==0.2 and payload["top_p"]==0.95
    assert payload["max_tokens"]==128 and payload["stream"] is False
    assert payload["truncate_prompt_tokens"] is None and payload["return_token_ids"] is True

def test_policy_request_forbidden_keys_are_absent() -> None:
    assert FORBIDDEN.isdisjoint(_request().to_wire_dict())

def test_policy_request_seed_and_request_id_are_exact() -> None:
    payload=_request().to_wire_dict()
    assert payload["seed"]==17 and payload["request_id"]=="req-1"

def test_r0_request_golden_wire_sha256() -> None:
    from pchsi.evaluation.canonical_evidence import sha256_bytes

    assert sha256_bytes(
        _request().to_wire_bytes()
    ) == (
        "81156664eefa3e43c9c8771a23ec7ba7"
        "84ea8b781f78783c7b4b04baa37c1468"
    )
    assert _request().to_wire_dict()["structured_outputs"] is None
