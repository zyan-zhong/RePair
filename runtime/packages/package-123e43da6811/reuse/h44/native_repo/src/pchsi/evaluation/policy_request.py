"""Exact E1 vLLM Chat Completions request bytes."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical_evidence import (
    canonical_json_bytes,
)


PI0_SERVED_MODEL_NAME = (
    "Qwen2.5-3B-Instruct-E1"
)


@dataclass(
    frozen=True,
    slots=True,
)
class E1PolicyRequestV1:
    """Frozen RAW_WITH_MENU_V1 request.

    The default served-model identity remains the original model
    version pi0. SELECT may explicitly bind a trained pi1 LoRA
    realization through ``served_model_name``.
    """

    prompt_text: str
    seed: int
    request_id: str
    served_model_name: str = (
        PI0_SERVED_MODEL_NAME
    )

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.prompt_text,
                str,
            )
            or self.prompt_text == ""
        ):
            raise ValueError(
                "prompt_text must be non-empty str"
            )

        if (
            type(self.seed) is not int
            or self.seed < 0
        ):
            raise ValueError(
                "seed must be non-negative int"
            )

        if (
            not isinstance(
                self.request_id,
                str,
            )
            or not self.request_id
        ):
            raise ValueError(
                "request_id must be non-empty"
            )

        if (
            not isinstance(
                self.served_model_name,
                str,
            )
            or not self.served_model_name
        ):
            raise ValueError(
                "served_model_name must be non-empty str"
            )

    def to_wire_dict(
        self,
    ) -> dict[str, object]:
        return {
            "model":
                self.served_model_name,
            "messages": [
                {
                    "role": "user",
                    "content":
                        self.prompt_text,
                }
            ],
            "temperature": 0.2,
            "top_p": 0.95,
            "max_tokens": 128,
            "seed": self.seed,
            "n": 1,
            "stream": False,
            "stop": None,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "logprobs": False,
            "top_logprobs": None,
            "best_of": None,
            "use_beam_search": False,
            "top_k": -1,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "length_penalty": 1.0,
            "stop_token_ids": [],
            "include_stop_str_in_output":
                False,
            "ignore_eos": False,
            "min_tokens": 0,
            "skip_special_tokens": True,
            "spaces_between_special_tokens":
                True,
            "truncate_prompt_tokens": None,
            "prompt_logprobs": None,
            "allowed_token_ids": None,
            "bad_words": [],
            "echo": False,
            "add_generation_prompt": True,
            "continue_final_message":
                False,
            "add_special_tokens": False,
            "documents": None,
            "chat_template": None,
            "chat_template_kwargs": {},
            "structured_outputs": None,
            "priority": 0,
            "return_token_ids": True,
            "request_id":
                self.request_id,
        }

    def to_wire_bytes(
        self,
    ) -> bytes:
        return canonical_json_bytes(
            self.to_wire_dict()
        )
