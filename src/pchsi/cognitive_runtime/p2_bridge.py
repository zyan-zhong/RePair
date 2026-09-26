"""Hash-pinned bridge to one frozen historical P2 transport attempt."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
import inspect
import os
from pathlib import Path
import sys
import threading
from types import ModuleType

from pchsi.reference_loop.canonical import canonical_json_bytes
from .p2_assets import binding_config, locate_p2_root, verify_httpx_runtime


_LOAD_LOCK = threading.Lock()


@dataclass(frozen=True, slots=True)
class P2TransportResult:
    http_status: int
    response_headers: dict[str, str]
    raw_response: bytes
    provider_http_request_id: str | None


class P2TransportError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        failure_class: str,
        bytes_transmission_state: str,
        retry_class: str,
        retry_authority: str,
        terminal_attempt_status: str,
        logical_method_status: str,
        counts_as_method_failure: bool,
        hard_stop: bool,
        http_status: int | None = None,
        response_headers: Mapping[str, str] | None = None,
        raw_response: bytes | None = None,
    ) -> None:
        super().__init__(message)
        self.failure_class = failure_class
        self.bytes_transmission_state = bytes_transmission_state
        self.retry_class = retry_class
        self.retry_authority = retry_authority
        self.terminal_attempt_status = terminal_attempt_status
        self.logical_method_status = logical_method_status
        self.counts_as_method_failure = counts_as_method_failure
        self.hard_stop = hard_stop
        self.http_status = http_status
        self.response_headers = dict(response_headers or {})
        self.raw_response = raw_response
        self.provider_http_request_id = self.response_headers.get(
            "x-request-id"
        )


def _load_source_module(name: str, path: Path) -> ModuleType:
    """Execute the exact hash-verified source bytes, never a cached .pyc."""
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"frozen P2 source path is invalid: {path}")

    previous = sys.modules.get(name)
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = name.rpartition(".")[0]
    module.__loader__ = None
    module.__spec__ = None
    sys.modules[name] = module

    try:
        source_bytes = path.read_bytes()
        code = compile(
            source_bytes,
            str(path),
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        exec(code, module.__dict__)
    except BaseException:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise

    return module


@lru_cache(maxsize=2)
def _load_transport_module(root: Path) -> ModuleType:
    cfg = binding_config()
    adapter_path = root / "runtime/p2_openai_adapter.py"
    execute_path = root / str(cfg["transport_module_relative_path"])

    with _LOAD_LOCK:
        previous_adapter = sys.modules.get("p2_openai_adapter")
        try:
            adapter = _load_source_module("p2_openai_adapter", adapter_path)
            sys.modules["p2_openai_adapter"] = adapter
            execute = _load_source_module(
                "pchsi_frozen_p2_openai_execute",
                execute_path,
            )
        finally:
            if previous_adapter is None:
                sys.modules.pop("p2_openai_adapter", None)
            else:
                sys.modules["p2_openai_adapter"] = previous_adapter
    return execute


def _validated_transport_callable(module: ModuleType):
    cfg = binding_config()
    fn = getattr(module, str(cfg["transport_callable_name"]), None)
    if not callable(fn):
        raise ValueError("hash-pinned P2 transport callable is missing")
    signature = inspect.signature(fn)
    observed = tuple(
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
    )
    expected = tuple(cfg["transport_required_kwonly_parameters"])
    if observed != expected:
        raise ValueError(
            f"P2 transport signature mismatch: observed={observed} "
            f"expected={expected}"
        )
    return fn


def inspect_bridge() -> dict[str, object]:
    root = locate_p2_root()
    cfg = binding_config()
    module = _load_transport_module(root)
    fn = _validated_transport_callable(module)
    return {
        "p2_root_private": str(root),
        "transport_module_path_private": str(
            root / str(cfg["transport_module_relative_path"])
        ),
        "transport_callable_name": cfg["transport_callable_name"],
        "transport_callable_signature": str(inspect.signature(fn)),
        "transport_return_tuple": cfg["transport_return_tuple"],
        "transport_exception_contract": cfg[
            "transport_exception_contract"
        ],
        "httpx_version": verify_httpx_runtime(),
        "legacy_callable_probe_removed": True,
        "command_override_present": False,
        "direct_openai_sdk_fallback_allowed": False,
        "automatic_transport_retry_count": 0,
    }


def _error(
    message: str,
    *,
    failure_class: str,
    bytes_transmission_state: str,
    retry_class: str,
    retry_authority: str,
    terminal_attempt_status: str,
    logical_method_status: str,
    counts_as_method_failure: bool,
    hard_stop: bool,
    http_status: int | None = None,
    response_headers: Mapping[str, str] | None = None,
    raw_response: bytes | None = None,
) -> P2TransportError:
    return P2TransportError(
        message,
        failure_class=failure_class,
        bytes_transmission_state=bytes_transmission_state,
        retry_class=retry_class,
        retry_authority=retry_authority,
        terminal_attempt_status=terminal_attempt_status,
        logical_method_status=logical_method_status,
        counts_as_method_failure=counts_as_method_failure,
        hard_stop=hard_stop,
        http_status=http_status,
        response_headers=response_headers,
        raw_response=raw_response,
    )


def _configuration_error(message: str, failure_class: str) -> P2TransportError:
    return _error(
        message,
        failure_class=failure_class,
        bytes_transmission_state="NOT_SENT",
        retry_class="NO_RETRY",
        retry_authority="FROZEN_RUNTIME_POLICY",
        terminal_attempt_status="INFRASTRUCTURE_ERROR",
        logical_method_status="INFRASTRUCTURE_UNAVAILABLE",
        counts_as_method_failure=False,
        hard_stop=True,
    )


def execute_via_existing_p2(
    request_bundle: Mapping[str, object],
    output_dir: Path,
    *,
    client_request_id: str,
) -> P2TransportResult:
    if not isinstance(client_request_id, str):
        raise _configuration_error(
            "client_request_id must be a string",
            "CLIENT_REQUEST_ID_INVALID_TYPE",
        )
    if (
        not client_request_id
        or not client_request_id.isascii()
        or len(client_request_id) > 512
    ):
        raise _configuration_error(
            "client_request_id must be non-empty ASCII and <= 512 characters",
            "CLIENT_REQUEST_ID_INVALID_FORMAT",
        )
    if not output_dir.is_dir():
        raise _configuration_error(
            "output_dir must already exist",
            "OUTPUT_DIRECTORY_INVALID",
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise _configuration_error(
            "OPENAI_API_KEY is not set",
            "AUTH_OR_CONFIGURATION_INVALID",
        )

    provider_request = request_bundle.get("provider_request")
    if not isinstance(provider_request, Mapping):
        raise _configuration_error(
            "provider_request must be one mapping",
            "PROVIDER_REQUEST_INVALID",
        )
    body = canonical_json_bytes(dict(provider_request))

    try:
        root = locate_p2_root()
        verify_httpx_runtime()
        module = _load_transport_module(root)
        fn = _validated_transport_callable(module)
        ambiguous_type = getattr(module, "HaltCaseAmbiguous", None)
        halt_batch_type = getattr(module, "HaltBatch", None)
        if not isinstance(ambiguous_type, type):
            raise ValueError("frozen P2 HaltCaseAmbiguous is missing")
        if not isinstance(halt_batch_type, type):
            raise ValueError("frozen P2 HaltBatch is missing")
    except P2TransportError:
        raise
    except Exception as error:
        raise _configuration_error(
            str(error),
            "RUNTIME_ADAPTER_DEFECT",
        ) from error

    try:
        status, headers, raw = fn(
            api_key=api_key,
            body=body,
            client_request_id=client_request_id,
        )
    except ConnectionError as error:
        raise _error(
            str(error),
            failure_class="PRE_SEND_INFRASTRUCTURE_UNAVAILABLE",
            bytes_transmission_state="NOT_SENT",
            retry_class="SAFE_PRE_SEND",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="INFRASTRUCTURE_ERROR",
            logical_method_status="INFRASTRUCTURE_UNAVAILABLE",
            counts_as_method_failure=False,
            hard_stop=False,
        ) from error
    except ambiguous_type as error:
        raise _error(
            str(error),
            failure_class="AMBIGUOUS_POST_SEND",
            bytes_transmission_state="MAY_HAVE_BEEN_SENT",
            retry_class="NO_RETRY",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="AMBIGUOUS_POST_SEND",
            logical_method_status="AMBIGUOUS_POST_SEND",
            counts_as_method_failure=False,
            hard_stop=True,
        ) from error
    except halt_batch_type as error:
        message = str(error)
        lowered = message.lower()
        failure_class = (
            "AUTH_OR_CONFIGURATION_INVALID"
            if "proxy" in lowered
            or "approval" in lowered
            or "api_key" in lowered
            or "configuration" in lowered
            else "RUNTIME_ADAPTER_DEFECT"
        )
        raise _configuration_error(message, failure_class) from error
    except Exception as error:
        raise _error(
            str(error),
            failure_class="UNCLASSIFIED_POST_SEND_EXCEPTION",
            bytes_transmission_state="MAY_HAVE_BEEN_SENT",
            retry_class="NO_RETRY",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="AMBIGUOUS_POST_SEND",
            logical_method_status="AMBIGUOUS_POST_SEND",
            counts_as_method_failure=False,
            hard_stop=True,
        ) from error

    if not isinstance(status, int):
        raise _error(
            "P2 transport returned a non-integer HTTP status",
            failure_class="TRANSPORT_RETURN_STATUS_INVALID",
            bytes_transmission_state="MAY_HAVE_BEEN_SENT",
            retry_class="NO_RETRY",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="AMBIGUOUS_POST_SEND",
            logical_method_status="AMBIGUOUS_POST_SEND",
            counts_as_method_failure=False,
            hard_stop=True,
        )
    if not isinstance(headers, Mapping) or not isinstance(raw, bytes):
        raise _error(
            "P2 transport returned a malformed result tuple",
            failure_class="TRANSPORT_RETURN_SHAPE_INVALID",
            bytes_transmission_state="MAY_HAVE_BEEN_SENT",
            retry_class="NO_RETRY",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="AMBIGUOUS_POST_SEND",
            logical_method_status="AMBIGUOUS_POST_SEND",
            counts_as_method_failure=False,
            hard_stop=True,
        )

    normalized_headers = {
        str(key).lower(): str(value)
        for key, value in headers.items()
    }
    provider_http_request_id = normalized_headers.get("x-request-id")

    if 200 <= status <= 299:
        return P2TransportResult(
            http_status=status,
            response_headers=normalized_headers,
            raw_response=raw,
            provider_http_request_id=provider_http_request_id,
        )

    classifier = getattr(module, "classify_http_failure", None)
    classification = (
        classifier(status, raw)
        if callable(classifier)
        else "REJECT_PROVIDER_HTTP_ERROR_NO_RETRY"
    )

    if classification == "RETRY_PROVIDER_INFRASTRUCTURE":
        return_error = _error(
            classification,
            failure_class="PROVIDER_TRANSIENT_UNAVAILABLE",
            bytes_transmission_state="CONFIRMED_SENT",
            retry_class="SAFE_PROVIDER_REJECTION",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="PROVIDER_REJECTED",
            logical_method_status="INFRASTRUCTURE_UNAVAILABLE",
            counts_as_method_failure=False,
            hard_stop=False,
            http_status=status,
            response_headers=normalized_headers,
            raw_response=raw,
        )
    elif classification == "REJECT_TEACHER_CONTEXT_OVERFLOW":
        return_error = _error(
            classification,
            failure_class="METHOD_CONTEXT_OVERFLOW",
            bytes_transmission_state="CONFIRMED_SENT",
            retry_class="NO_RETRY",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="PROVIDER_REJECTED",
            logical_method_status="SEMANTIC_INVALID",
            counts_as_method_failure=True,
            hard_stop=False,
            http_status=status,
            response_headers=normalized_headers,
            raw_response=raw,
        )
    elif classification == "HALT_BATCH_PROVIDER_AUTH_OR_CONFIG":
        return_error = _error(
            classification,
            failure_class="AUTH_OR_CONFIGURATION_INVALID",
            bytes_transmission_state="CONFIRMED_SENT",
            retry_class="NO_RETRY",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="PROVIDER_REJECTED",
            logical_method_status="INFRASTRUCTURE_UNAVAILABLE",
            counts_as_method_failure=False,
            hard_stop=True,
            http_status=status,
            response_headers=normalized_headers,
            raw_response=raw,
        )
    elif classification == "HALT_BATCH_PROVIDER_ADAPTER_DEFECT":
        return_error = _error(
            classification,
            failure_class="RUNTIME_ADAPTER_DEFECT",
            bytes_transmission_state="CONFIRMED_SENT",
            retry_class="NO_RETRY",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="PROVIDER_REJECTED",
            logical_method_status="INFRASTRUCTURE_UNAVAILABLE",
            counts_as_method_failure=False,
            hard_stop=True,
            http_status=status,
            response_headers=normalized_headers,
            raw_response=raw,
        )
    else:
        return_error = _error(
            classification,
            failure_class="METHOD_PROVIDER_REJECTION",
            bytes_transmission_state="CONFIRMED_SENT",
            retry_class="NO_RETRY",
            retry_authority="FROZEN_RUNTIME_POLICY",
            terminal_attempt_status="PROVIDER_REJECTED",
            logical_method_status="SEMANTIC_INVALID",
            counts_as_method_failure=True,
            hard_stop=False,
            http_status=status,
            response_headers=normalized_headers,
            raw_response=raw,
        )
    raise return_error
