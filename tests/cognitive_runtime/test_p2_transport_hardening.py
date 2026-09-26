from __future__ import annotations

import inspect
import json
from pathlib import Path
import py_compile
import sys

import pytest

import pchsi.cognitive_runtime.orchestrator as orchestrator
import pchsi.cognitive_runtime.p2_bridge as bridge


REPO_ROOT = Path(__file__).resolve().parents[2]


def _bundle() -> dict[str, object]:
    return {
        "provider_request": {
            "model": "gpt-5.6-sol",
            "input": "test",
            "store": False,
            "tools": [],
        },
        "request_body_sha256": "a" * 64,
    }


def test_exact_transport_binding_replaces_legacy_callable_guessing() -> None:
    cfg = json.loads(
        (
            REPO_ROOT
            / "configs/cognitive_runtime/p2_asset_binding_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert "allowed_callable_names" not in cfg
    assert "command_env" not in cfg
    assert cfg["transport_callable_name"] == "_http_attempt"
    assert cfg["transport_required_kwonly_parameters"] == [
        "api_key",
        "body",
        "client_request_id",
    ]
    assert cfg["expected_httpx_version"] == "0.28.1"
    assert cfg["expected_asset_sha256"] == {
        "runtime/p2_openai_adapter.py":
            "af8d923305444bd524db1bffa99b85670625787e68f658cfc0ed87c37e713a78",
        "runtime/p2_openai_execute.py":
            "e970db06f4afe41c6c52f93f00c7eb3a9e7e785e88db74e8c02930c0928ac365",
    }


def test_bridge_has_no_shell_or_second_provider_client() -> None:
    source = inspect.getsource(bridge)
    for forbidden in (
        "PCHSI_P2_EXECUTE_COMMAND",
        "execute_canonical_request",
        "execute_request",
        "run_request",
        "subprocess",
        "shell=True",
        "import httpx",
        "from openai",
        "import openai",
    ):
        assert forbidden not in source


def test_exact_source_loader_ignores_preexisting_unchecked_hash_pyc(
    tmp_path: Path,
) -> None:
    source = tmp_path / "frozen_transport_fixture.py"
    source.write_text("VALUE = 99\n", encoding="utf-8")

    pyc = Path(
        py_compile.compile(
            str(source),
            doraise=True,
            invalidation_mode=(
                py_compile.PycInvalidationMode.UNCHECKED_HASH
            ),
        )
    )
    assert pyc.is_file()
    pyc_before = pyc.read_bytes()

    source.write_text("VALUE = 7\n", encoding="utf-8")

    name = "pchsi_exact_source_loader_regression_fixture"
    sys.modules.pop(name, None)
    try:
        module = bridge._load_source_module(name, source)
        assert module.VALUE == 7
        assert pyc.read_bytes() == pyc_before
    finally:
        sys.modules.pop(name, None)


def test_success_preserves_raw_bytes_and_request_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class Fake:
        class HaltBatch(RuntimeError):
            pass

        class HaltCaseAmbiguous(RuntimeError):
            pass

        @staticmethod
        def _http_attempt(*, api_key: str, body: bytes, client_request_id: str):
            assert api_key == "secret"
            assert client_request_id == "logical-1"
            assert isinstance(body, bytes)
            return 200, {"x-request-id": "req-1"}, b'{"status":"completed"}'

        @staticmethod
        def classify_http_failure(status: int, body: bytes) -> str:
            raise AssertionError("classifier must not be called for 2xx")

    monkeypatch.setattr(bridge, "locate_p2_root", lambda: tmp_path)
    monkeypatch.setattr(bridge, "verify_httpx_runtime", lambda: "0.28.1")
    monkeypatch.setattr(bridge, "_load_transport_module", lambda root: Fake)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    result = bridge.execute_via_existing_p2(
        _bundle(),
        tmp_path,
        client_request_id="logical-1",
    )
    assert result.http_status == 200
    assert result.provider_http_request_id == "req-1"
    assert result.raw_response == b'{"status":"completed"}'


def test_connect_failure_is_not_sent_and_not_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class Fake:
        class HaltBatch(RuntimeError):
            pass

        class HaltCaseAmbiguous(RuntimeError):
            pass

        @staticmethod
        def _http_attempt(*, api_key: str, body: bytes, client_request_id: str):
            raise ConnectionError("ConnectTimeout")

    monkeypatch.setattr(bridge, "locate_p2_root", lambda: tmp_path)
    monkeypatch.setattr(bridge, "verify_httpx_runtime", lambda: "0.28.1")
    monkeypatch.setattr(bridge, "_load_transport_module", lambda root: Fake)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    with pytest.raises(bridge.P2TransportError) as caught:
        bridge.execute_via_existing_p2(
            _bundle(),
            tmp_path,
            client_request_id="logical-2",
        )
    error = caught.value
    assert error.failure_class == "PRE_SEND_INFRASTRUCTURE_UNAVAILABLE"
    assert error.bytes_transmission_state == "NOT_SENT"
    assert error.logical_method_status == "INFRASTRUCTURE_UNAVAILABLE"
    assert error.retry_class == "SAFE_PRE_SEND"
    assert error.counts_as_method_failure is False


def test_post_send_ambiguity_is_terminal_and_nonretrying(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class Fake:
        class HaltBatch(RuntimeError):
            pass

        class HaltCaseAmbiguous(RuntimeError):
            pass

        @staticmethod
        def _http_attempt(*, api_key: str, body: bytes, client_request_id: str):
            raise Fake.HaltCaseAmbiguous("ReadTimeout")

    monkeypatch.setattr(bridge, "locate_p2_root", lambda: tmp_path)
    monkeypatch.setattr(bridge, "verify_httpx_runtime", lambda: "0.28.1")
    monkeypatch.setattr(bridge, "_load_transport_module", lambda root: Fake)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    with pytest.raises(bridge.P2TransportError) as caught:
        bridge.execute_via_existing_p2(
            _bundle(),
            tmp_path,
            client_request_id="logical-3",
        )
    error = caught.value
    assert error.failure_class == "AMBIGUOUS_POST_SEND"
    assert error.bytes_transmission_state == "MAY_HAVE_BEEN_SENT"
    assert error.logical_method_status == "AMBIGUOUS_POST_SEND"
    assert error.retry_class == "NO_RETRY"
    assert error.hard_stop is True


def test_provider_failure_taxonomy_preserves_denominator_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class Fake:
        class HaltBatch(RuntimeError):
            pass

        class HaltCaseAmbiguous(RuntimeError):
            pass

        @staticmethod
        def _http_attempt(*, api_key: str, body: bytes, client_request_id: str):
            return 400, {"x-request-id": "req-400"}, b'context_length_exceeded'

        @staticmethod
        def classify_http_failure(status: int, body: bytes) -> str:
            return "REJECT_TEACHER_CONTEXT_OVERFLOW"

    monkeypatch.setattr(bridge, "locate_p2_root", lambda: tmp_path)
    monkeypatch.setattr(bridge, "verify_httpx_runtime", lambda: "0.28.1")
    monkeypatch.setattr(bridge, "_load_transport_module", lambda root: Fake)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    with pytest.raises(bridge.P2TransportError) as caught:
        bridge.execute_via_existing_p2(
            _bundle(),
            tmp_path,
            client_request_id="logical-4",
        )
    error = caught.value
    assert error.failure_class == "METHOD_CONTEXT_OVERFLOW"
    assert error.bytes_transmission_state == "CONFIRMED_SENT"
    assert error.logical_method_status == "SEMANTIC_INVALID"
    assert error.counts_as_method_failure is True
    assert error.raw_response == b'context_length_exceeded'


def test_orchestrator_records_typed_failure_and_terminal_logical_call() -> None:
    source = inspect.getsource(orchestrator)
    assert "except P2TransportError as error" in source
    assert "client_request_id=logical_call_id" in source
    assert "counts_as_method_failure" in source
    assert "_write_logical_call" in source
    assert 'call_dir / "transport_http_meta.json"' in source
