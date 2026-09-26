"""Exact-byte HTTP policy transport and token-aligned E1 policy client."""

from __future__ import annotations

from collections.abc import (
    Callable,
    Mapping,
)
import http.client
import time
from typing import Protocol
from urllib.parse import urlparse

from .policy_call_evidence import (
    PolicyCallResultV1,
    PolicyCallTransportEvidenceV1,
    allowlisted_response_headers,
)
from .policy_execution_profile import (
    PolicyRequestProtocol,
)
from .policy_response import (
    PolicyGeneration,
    PolicyResponseError,
    parse_policy_response,
)
from .rendered_prompt import (
    RenderedPromptEvidence,
)


class PolicyTransportError(
    RuntimeError
):
    pass


class PromptTokenMismatchError(
    RuntimeError
):
    pass


class PolicyTransport(
    Protocol
):
    def post_exact(
        self,
        *,
        path: str,
        body: bytes,
        headers:
            Mapping[
                str,
                str,
            ],
    ) -> tuple[
        int,
        Mapping[
            str,
            str,
        ],
        bytes,
    ]:
        ...


class HttpPolicyTransport:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds:
            float = 60.0,
        connection_factory=None,
    ):
        parsed = urlparse(
            base_url
        )

        if (
            parsed.scheme
            not in {
                "http",
                "https",
            }
            or not parsed.hostname
            or parsed.path
            not in (
                "",
                "/",
            )
        ):
            raise ValueError(
                "invalid base_url"
            )

        if (
            type(
                timeout_seconds
            )
            not in (
                int,
                float,
            )
            or timeout_seconds
            <= 0
        ):
            raise ValueError(
                "timeout_seconds must be positive"
            )

        self._scheme = (
            parsed.scheme
        )
        self._host = (
            parsed.hostname
        )
        self._port = (
            parsed.port
        )
        self._timeout = float(
            timeout_seconds
        )
        self._factory = (
            connection_factory
            or self._default_factory
        )

    @staticmethod
    def _default_factory(
        *,
        scheme,
        host,
        port,
        timeout,
    ):
        kind = (
            http.client.HTTPSConnection
            if scheme == "https"
            else http.client.HTTPConnection
        )

        return kind(
            host=host,
            port=port,
            timeout=timeout,
        )

    def post_exact(
        self,
        *,
        path: str,
        body: bytes,
        headers:
            Mapping[
                str,
                str,
            ],
    ) -> tuple[
        int,
        Mapping[
            str,
            str,
        ],
        bytes,
    ]:
        if (
            not isinstance(
                path,
                str,
            )
            or not path.startswith(
                "/"
            )
        ):
            raise ValueError(
                "path must be absolute"
            )

        if not isinstance(
            body,
            bytes,
        ):
            raise TypeError(
                "body must be bytes"
            )

        frozen = {}

        for (
            key,
            value,
        ) in headers.items():
            if (
                not isinstance(
                    key,
                    str,
                )
                or not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    "headers must be string pairs"
                )

            frozen[
                key
            ] = value

        connection = (
            self._factory(
                scheme=
                    self._scheme,
                host=
                    self._host,
                port=
                    self._port,
                timeout=
                    self._timeout,
            )
        )

        try:
            connection.request(
                "POST",
                path,
                body=body,
                headers=frozen,
            )

            response = (
                connection
                .getresponse()
            )

            response_body = (
                response.read()
            )

            return (
                int(
                    response.status
                ),
                {
                    str(key):
                        str(value)
                    for (
                        key,
                        value,
                    ) in (
                        response
                        .getheaders()
                    )
                },
                response_body,
            )

        except OSError as error:
            raise PolicyTransportError(
                "HTTP transport failed"
            ) from error

        finally:
            connection.close()


def _request_model_name(
    request:
        PolicyRequestProtocol,
) -> str:
    payload = (
        request
        .to_wire_dict()
    )

    model_name = (
        payload.get(
            "model"
        )
    )

    if (
        not isinstance(
            model_name,
            str,
        )
        or not model_name
    ):
        raise ValueError(
            "request model must be non-empty str"
        )

    return model_name


class PolicyClient:
    def __init__(
        self,
        *,
        transport:
            PolicyTransport,
        clock_ns:
            Callable[
                [],
                int,
            ]
            | None = None,
    ):
        self._transport = (
            transport
        )

        self._clock = (
            time.monotonic_ns
            if clock_ns is None
            else clock_ns
        )

    def generate_with_evidence(
        self,
        *,
        request:
            PolicyRequestProtocol,
        expected_prompt:
            RenderedPromptEvidence,
    ) -> PolicyCallResultV1:

        request_model_name = (
            _request_model_name(
                request
            )
        )

        request_bytes = (
            request
            .to_wire_bytes()
        )

        start = (
            self._clock()
        )

        (
            status,
            headers,
            body,
        ) = (
            self._transport
            .post_exact(
                path=(
                    "/v1/chat/completions"
                ),
                body=
                    request_bytes,
                headers={
                    "Content-Type":
                        "application/json",
                    "X-Request-Id":
                        request.request_id,
                },
            )
        )

        end = (
            self._clock()
        )

        elapsed = (
            end
            - start
        )

        if elapsed < 0:
            raise PolicyTransportError(
                "monotonic clock moved backwards"
            )

        latency = (
            elapsed
            // 1_000_000
        )

        generation = (
            parse_policy_response(
                status_code=
                    status,
                headers=
                    headers,
                body=
                    body,
                client_request_id=(
                    request
                    .request_id
                ),
                latency_ms=
                    latency,
            )
        )

        if (
            generation
            .provider_model_name
            != request_model_name
        ):
            raise PolicyResponseError(
                "response model identity "
                "does not match request model"
            )

        if (
            generation
            .prompt_token_ids
            != expected_prompt
            .rendered_token_ids
            or generation
            .prompt_tokens
            != expected_prompt
            .prompt_token_count
        ):
            raise PromptTokenMismatchError(
                "server prompt token IDs "
                "do not match local frozen rendering"
            )

        transport = (
            PolicyCallTransportEvidenceV1(
                request_bytes,
                status,
                tuple(
                    allowlisted_response_headers(
                        headers
                    ).items()
                ),
                body,
                latency,
            )
        )

        return PolicyCallResultV1(
            generation,
            transport,
        )

    def generate(
        self,
        *,
        request:
            PolicyRequestProtocol,
        expected_prompt:
            RenderedPromptEvidence,
    ) -> PolicyGeneration:
        return (
            self.generate_with_evidence(
                request=
                    request,
                expected_prompt=
                    expected_prompt,
            )
            .generation
        )
