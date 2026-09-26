"""OpenAI Responses request/response and no-retry ledger for strong reference.

The network transport is injected.  This module deliberately does not create a
second OpenAI/httpx client; the live integration must bind the already audited
P2 transport primitive.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Mapping, Protocol


class OpenAIResponsesPolicyError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_new(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise


@dataclass(frozen=True, slots=True)
class OpenAIResponsesPolicyRequestV1:
    prompt_text: str
    request_id: str
    model: str = "gpt-5.6-sol"
    reasoning_effort: str = "high"
    reasoning_context: str = "current_turn"
    max_output_tokens: int = 32768

    def __post_init__(self) -> None:
        if not isinstance(self.prompt_text, str) or not self.prompt_text:
            raise ValueError("prompt_text must be non-empty")
        if not isinstance(self.request_id, str) or not self.request_id:
            raise ValueError("request_id must be non-empty")
        if self.model != "gpt-5.6-sol":
            raise ValueError(
                "strong-model reference must request exact gpt-5.6-sol"
            )
        if self.reasoning_effort not in {"none", "high"}:
            raise ValueError("reasoning_effort must be none or high")
        if self.reasoning_context != "current_turn":
            raise ValueError("reasoning_context must be current_turn")
        expected_max = 128 if self.reasoning_effort == "none" else 32768
        if self.max_output_tokens != expected_max:
            raise ValueError(
                "max_output_tokens does not match registered reasoning arm"
            )

    def to_wire_dict(self) -> dict[str, object]:
        return {
            "model": self.model,
            "input": self.prompt_text,
            "reasoning": {
                "effort": self.reasoning_effort,
                "context": self.reasoning_context,
            },
            "max_output_tokens": self.max_output_tokens,
            "store": False,
            "tools": [],
            "truncation": "disabled",
        }

    def to_wire_bytes(self) -> bytes:
        return _canonical(self.to_wire_dict())


@dataclass(frozen=True, slots=True)
class ParsedOpenAIResponseV1:
    response_id: str
    returned_model: str
    status: str
    output_text: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None


def parse_openai_response(body: bytes) -> ParsedOpenAIResponseV1:
    if not isinstance(body, bytes):
        raise TypeError("body must be bytes")
    try:
        value = json.loads(body)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise OpenAIResponsesPolicyError(
            "response is not valid JSON"
        ) from error
    if not isinstance(value, dict):
        raise OpenAIResponsesPolicyError("response must be an object")

    response_id = value.get("id")
    model = value.get("model")
    status = value.get("status")
    if not all(
        isinstance(item, str) and item
        for item in (response_id, model, status)
    ):
        raise OpenAIResponsesPolicyError(
            "response identity or status is missing"
        )
    if status != "completed":
        raise OpenAIResponsesPolicyError(
            f"response status is not completed: {status}"
        )

    texts: list[str] = []
    output = value.get("output")
    if not isinstance(output, list):
        raise OpenAIResponsesPolicyError("response.output must be an array")
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            ):
                texts.append(part["text"])
    if not texts:
        raise OpenAIResponsesPolicyError(
            "completed response has no output_text"
        )

    usage = value.get("usage")
    if not isinstance(usage, dict):
        raise OpenAIResponsesPolicyError("response.usage is missing")
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if (
        type(input_tokens) is not int
        or input_tokens < 0
        or type(output_tokens) is not int
        or output_tokens < 0
    ):
        raise OpenAIResponsesPolicyError("usage token counts are invalid")

    reasoning_tokens: int | None = None
    details = usage.get("output_tokens_details")
    if isinstance(details, dict):
        observed = details.get("reasoning_tokens")
        if observed is not None:
            if type(observed) is not int or observed < 0:
                raise OpenAIResponsesPolicyError(
                    "reasoning token count is invalid"
                )
            reasoning_tokens = observed

    return ParsedOpenAIResponseV1(
        response_id=response_id,
        returned_model=model,
        status=status,
        output_text="".join(texts),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
    )


class P2TransportPrimitive(Protocol):
    def __call__(
        self,
        *,
        api_key: str,
        body: bytes,
        client_request_id: str,
    ) -> tuple[int, Mapping[str, str], bytes]:
        ...


@dataclass(frozen=True, slots=True)
class OpenAIPolicyCallReservationV1:
    request_id: str
    directory: Path
    started_path: Path


@dataclass(frozen=True, slots=True)
class OpenAIPolicyCallLedgerV1:
    root: Path

    def reserve(
        self,
        request: OpenAIResponsesPolicyRequestV1,
    ) -> OpenAIPolicyCallReservationV1:
        root = self.root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", request.request_id)
        directory = root / safe_id
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError as error:
            raise FileExistsError(
                f"policy call already reserved: {request.request_id}"
            ) from error
        started_path = directory / "STARTED.json"
        payload = {
            "schema_id": "OPENAI_POLICY_CALL_STARTED_V1",
            "client_request_id": request.request_id,
            "requested_model": request.model,
            "reasoning_effort": request.reasoning_effort,
            "reasoning_context": request.reasoning_context,
            "max_output_tokens": request.max_output_tokens,
            "endpoint": "/v1/responses",
            "request_wire_base64": base64.b64encode(
                request.to_wire_bytes()
            ).decode("ascii"),
            "request_wire_sha256": _sha256(request.to_wire_bytes()),
            "automatic_retry_count": 0,
            "store": False,
            "tools": [],
            "previous_response_id": None,
            "transport_primitive": "P2_TRANSPORT_PRIMITIVE_ADAPTER_V1",
        }
        _write_new(started_path, _canonical(payload))
        return OpenAIPolicyCallReservationV1(
            request_id=request.request_id,
            directory=directory,
            started_path=started_path,
        )

    def write_terminal(
        self,
        *,
        reservation: OpenAIPolicyCallReservationV1,
        request: OpenAIResponsesPolicyRequestV1,
        status_code: int,
        headers: Mapping[str, str],
        body: bytes,
        parsed: ParsedOpenAIResponseV1,
        latency_ms: int,
    ) -> Path:
        path = reservation.directory / "TERMINAL.json"
        allowlisted_headers = {
            str(key).casefold(): str(value)
            for key, value in headers.items()
            if str(key).casefold()
            in {
                "x-request-id",
                "content-type",
                "content-length",
                "openai-processing-ms",
            }
        }
        payload = {
            "schema_id": "OPENAI_POLICY_CALL_TERMINAL_V1",
            "client_request_id": request.request_id,
            "requested_model": request.model,
            "returned_model": parsed.returned_model,
            "provider_response_id": parsed.response_id,
            "endpoint": "/v1/responses",
            "http_status": status_code,
            "response_headers_allowlisted": allowlisted_headers,
            "raw_response_base64": base64.b64encode(body).decode("ascii"),
            "raw_response_sha256": _sha256(body),
            "status": parsed.status,
            "output_text": parsed.output_text,
            "input_tokens": parsed.input_tokens,
            "output_tokens": parsed.output_tokens,
            "reasoning_tokens": parsed.reasoning_tokens,
            "latency_ms": latency_ms,
            "automatic_retry_count": 0,
        }
        _write_new(path, _canonical(payload))
        return path

    def write_transport_exception(
        self,
        *,
        reservation: OpenAIPolicyCallReservationV1,
        error: BaseException,
    ) -> Path:
        path = reservation.directory / "TRANSPORT_EXCEPTION.json"
        payload = {
            "schema_id": "OPENAI_POLICY_CALL_TRANSPORT_EXCEPTION_V1",
            "exception_type": type(error).__name__,
            "automatic_retry_count": 0,
            "retry_authority": getattr(
                error,
                "retry_authority",
                "NO_AUTOMATIC_RETRY",
            ),
            "transmission_state": getattr(
                error,
                "transmission_state",
                "CONSERVATIVE_UNKNOWN",
            ),
        }
        _write_new(path, _canonical(payload))
        return path

    def write_post_transport_failure(
        self,
        *,
        reservation: OpenAIPolicyCallReservationV1,
        request: OpenAIResponsesPolicyRequestV1,
        status_code: int,
        headers: Mapping[str, str],
        body: bytes,
        latency_ms: int,
        failure_code: str,
    ) -> Path:
        path = reservation.directory / "POST_TRANSPORT_FAILURE.json"
        payload = {
            "schema_id": "OPENAI_POLICY_CALL_POST_TRANSPORT_FAILURE_V1",
            "client_request_id": request.request_id,
            "requested_model": request.model,
            "http_status": status_code,
            "response_headers_allowlisted": {
                str(key).casefold(): str(value)
                for key, value in headers.items()
                if str(key).casefold()
                in {
                    "x-request-id",
                    "content-type",
                    "content-length",
                    "openai-processing-ms",
                }
            },
            "raw_response_base64": base64.b64encode(body).decode("ascii"),
            "raw_response_sha256": _sha256(body),
            "latency_ms": latency_ms,
            "failure_code": failure_code,
            "automatic_retry_count": 0,
            "retry_authority": "NO_AUTOMATIC_RETRY",
            "transmission_state": "CONFIRMED_SENT",
        }
        _write_new(path, _canonical(payload))
        return path


@dataclass(frozen=True, slots=True)
class OpenAIResponsesPolicyClientV1:
    api_key: str
    ledger: OpenAIPolicyCallLedgerV1
    transport: P2TransportPrimitive

    def generate(
        self,
        *,
        request: OpenAIResponsesPolicyRequestV1,
        expected_prompt: object,
    ) -> object:
        if not isinstance(request, OpenAIResponsesPolicyRequestV1):
            raise TypeError(
                "request must be OpenAIResponsesPolicyRequestV1"
            )
        if not isinstance(self.api_key, str) or not self.api_key:
            raise OpenAIResponsesPolicyError("api_key must be non-empty")

        # Reservation happens before the one allowed transport attempt.
        reservation = self.ledger.reserve(request)
        started = time.monotonic()
        try:
            status_code, headers, body = self.transport(
                api_key=self.api_key,
                body=request.to_wire_bytes(),
                client_request_id=request.request_id,
            )
        except BaseException as error:
            self.ledger.write_transport_exception(
                reservation=reservation,
                error=error,
            )
            raise
        latency_ms = int((time.monotonic() - started) * 1000)

        if status_code != 200:
            self.ledger.write_post_transport_failure(
                reservation=reservation,
                request=request,
                status_code=status_code,
                headers=headers,
                body=body,
                latency_ms=latency_ms,
                failure_code="HTTP_STATUS_NOT_200",
            )
            raise OpenAIResponsesPolicyError(
                f"HTTP status must be 200, observed {status_code}"
            )
        try:
            parsed = parse_openai_response(body)
        except OpenAIResponsesPolicyError:
            self.ledger.write_post_transport_failure(
                reservation=reservation,
                request=request,
                status_code=status_code,
                headers=headers,
                body=body,
                latency_ms=latency_ms,
                failure_code="RESPONSE_PARSE_OR_STATUS_INVALID",
            )
            raise
        if not (
            parsed.returned_model == request.model
            or parsed.returned_model.startswith(request.model + "-")
        ):
            self.ledger.write_post_transport_failure(
                reservation=reservation,
                request=request,
                status_code=status_code,
                headers=headers,
                body=body,
                latency_ms=latency_ms,
                failure_code="RETURNED_MODEL_MISMATCH",
            )
            raise OpenAIResponsesPolicyError(
                f"returned model mismatch: {parsed.returned_model}"
            )
        self.ledger.write_terminal(
            reservation=reservation,
            request=request,
            status_code=status_code,
            headers=headers,
            body=body,
            parsed=parsed,
            latency_ms=latency_ms,
        )

        from .policy_response import PolicyGeneration

        return PolicyGeneration(
            raw_response_text=parsed.output_text,
            raw_response_body=body,
            provider_request_id=parsed.response_id,
            client_request_id=request.request_id,
            finish_reason=parsed.status,
            prompt_tokens=parsed.input_tokens,
            completion_tokens=parsed.output_tokens,
            prompt_token_ids=(),
            token_ids=None,
            latency_ms=latency_ms,
            provider_model_name=parsed.returned_model,
        )
