"""Strict non-streaming vLLM Chat Completions response parsing."""

from __future__ import annotations

from collections.abc import (
    Mapping,
)
from dataclasses import dataclass

from .canonical_evidence import (
    require_nonnegative_int,
    strict_json_loads,
)


class PolicyResponseError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class PolicyGeneration:
    raw_response_text: str
    raw_response_body: bytes
    provider_request_id: str
    client_request_id: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    prompt_token_ids: tuple[
        int,
        ...,
    ]
    token_ids: (
        tuple[
            int,
            ...,
        ]
        | None
    )
    latency_ms: int

    # Optional default preserves any old direct constructors.
    # parse_policy_response() always supplies a real value.
    provider_model_name: (
        str
        | None
    ) = None


def _mapping(
    name,
    value,
):
    if not isinstance(
        value,
        Mapping,
    ):
        raise PolicyResponseError(
            f"{name} must be a JSON object"
        )

    return value


def _text(
    name,
    value,
):
    if (
        not isinstance(
            value,
            str,
        )
        or not value
    ):
        raise PolicyResponseError(
            f"{name} must be non-empty str"
        )

    return value


def _ids(
    name,
    value,
):
    if not isinstance(
        value,
        list,
    ):
        raise PolicyResponseError(
            f"{name} must be a JSON array"
        )

    result = []

    for (
        index,
        item,
    ) in enumerate(
        value
    ):
        try:
            result.append(
                require_nonnegative_int(
                    f"{name}[{index}]",
                    item,
                )
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise PolicyResponseError(
                str(error)
            ) from error

    return tuple(
        result
    )


def parse_policy_response(
    *,
    status_code: int,
    headers:
        Mapping[
            str,
            str,
        ],
    body: bytes,
    client_request_id: str,
    latency_ms: int,
) -> PolicyGeneration:

    if status_code != 200:
        raise PolicyResponseError(
            "HTTP status must be 200, "
            f"observed {status_code}"
        )

    if not isinstance(
        body,
        bytes,
    ):
        raise TypeError(
            "body must be bytes"
        )

    if (
        not isinstance(
            client_request_id,
            str,
        )
        or not client_request_id
    ):
        raise ValueError(
            "client_request_id must be non-empty"
        )

    try:
        latency = (
            require_nonnegative_int(
                "latency_ms",
                latency_ms,
            )
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise PolicyResponseError(
            str(error)
        ) from error

    root = _mapping(
        "response",
        strict_json_loads(
            body
        ),
    )

    response_id = _text(
        "response.id",
        root.get(
            "id"
        ),
    )

    provider_model_name = (
        _text(
            "response.model",
            root.get(
                "model"
            ),
        )
    )

    choices = root.get(
        "choices"
    )

    if (
        not isinstance(
            choices,
            list,
        )
        or len(
            choices
        )
        != 1
    ):
        raise PolicyResponseError(
            "choices must contain exactly one item"
        )

    choice = _mapping(
        "choice",
        choices[0],
    )

    message = _mapping(
        "message",
        choice.get(
            "message"
        ),
    )

    content = message.get(
        "content"
    )

    if not isinstance(
        content,
        str,
    ):
        raise PolicyResponseError(
            "message.content must be str"
        )

    finish = _text(
        "finish_reason",
        choice.get(
            "finish_reason"
        ),
    )

    usage = _mapping(
        "usage",
        root.get(
            "usage"
        ),
    )

    try:
        prompt = (
            require_nonnegative_int(
                "usage.prompt_tokens",
                usage.get(
                    "prompt_tokens"
                ),
            )
        )

        completion = (
            require_nonnegative_int(
                "usage.completion_tokens",
                usage.get(
                    "completion_tokens"
                ),
            )
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise PolicyResponseError(
            str(error)
        ) from error

    prompt_ids = _ids(
        "prompt_token_ids",
        root.get(
            "prompt_token_ids"
        ),
    )

    token_ids = (
        None
        if choice.get(
            "token_ids"
        )
        is None
        else _ids(
            "token_ids",
            choice.get(
                "token_ids"
            ),
        )
    )

    normalized = {
        str(key).casefold():
            str(value)
        for (
            key,
            value,
        ) in headers.items()
    }

    provider_request_id = (
        normalized.get(
            "x-request-id"
        )
        or response_id
    )

    return PolicyGeneration(
        raw_response_text=
            content,
        raw_response_body=
            body,
        provider_request_id=
            provider_request_id,
        client_request_id=
            client_request_id,
        finish_reason=
            finish,
        prompt_tokens=
            prompt,
        completion_tokens=
            completion,
        prompt_token_ids=
            prompt_ids,
        token_ids=
            token_ids,
        latency_ms=
            latency,
        provider_model_name=(
            provider_model_name
        ),
    )
