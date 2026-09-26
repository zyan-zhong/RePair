from __future__ import annotations

import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import (
    ProxyHandler,
    Request,
    build_opener,
)

from .common import Stage0Error
from .constants import (
    CANDIDATE_CHECKPOINT_ID,
    PARENT_CHECKPOINT_ID,
)


_DIRECT_LOOPBACK_OPENER = build_opener(
    ProxyHandler({})
)


def _validate_loopback_url(
    url: str,
) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.scheme != "http":
        raise Stage0Error(
            "LOOPBACK_HTTP_SCHEME_CHANGED:"
            + repr(parsed.scheme)
        )
    if parsed.hostname not in {
        "127.0.0.1",
        "localhost",
    }:
        raise Stage0Error(
            "LOOPBACK_HTTP_HOST_CHANGED:"
            + repr(parsed.hostname)
        )
    if parsed.port is None:
        raise Stage0Error(
            "LOOPBACK_HTTP_PORT_MISSING"
        )
    return (
        parsed.hostname,
        parsed.port,
    )


def _direct_loopback_open(
    request: Request,
    *,
    timeout: float,
):
    _validate_loopback_url(
        request.full_url
    )
    return _DIRECT_LOOPBACK_OPENER.open(
        request,
        timeout=timeout,
    )


def build_vllm_command(
    *,
    server_manifest: dict[str, Any],
    base_model_path: str,
    host: str,
    port: int,
) -> list[str]:
    registry = server_manifest.get("static_lora_registry")
    if not isinstance(registry, list) or len(registry) != 2:
        raise Stage0Error("VLLM_STATIC_LORA_REGISTRY_CHANGED")
    by_name = {
        row.get("served_model_name"): row
        for row in registry
        if isinstance(row, dict)
    }
    required = {
        PARENT_CHECKPOINT_ID,
        CANDIDATE_CHECKPOINT_ID,
    }
    if set(by_name) != required:
        raise Stage0Error(
            "VLLM_STATIC_LORA_IDENTITY_CHANGED:"
            + repr(sorted(by_name))
        )
    modules = [
        (
            f"{model_name}="
            f"{by_name[model_name]['adapter_path']}"
        )
        for model_name in (
            PARENT_CHECKPOINT_ID,
            CANDIDATE_CHECKPOINT_ID,
        )
    ]
    return [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        base_model_path,
        "--host",
        host,
        "--port",
        str(port),
        "--dtype",
        str(server_manifest["dtype"]),
        "--tensor-parallel-size",
        str(server_manifest["tensor_parallel_size"]),
        "--generation-config",
        str(server_manifest["generation_config_mode"]),
        "--chat-template-content-format",
        str(server_manifest["chat_template_content_format"]),
        "--enable-lora",
        "--max-lora-rank",
        str(server_manifest["max_lora_rank"]),
        "--max-loras",
        str(server_manifest["max_loras"]),
        "--max-cpu-loras",
        str(server_manifest["max_cpu_loras"]),
        "--lora-dtype",
        str(server_manifest["lora_dtype"]),
        "--lora-modules",
        *modules,
    ]


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    request = Request(url, method="GET")
    with _direct_loopback_open(
        request,
        timeout=timeout,
    ) as response:
        body = response.read()
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise Stage0Error(f"HTTP_JSON_OBJECT_REQUIRED:{url}")
    return value


def wait_for_server(
    *,
    base_url: str,
    process,
    timeout_seconds: float = 600.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise Stage0Error(f"VLLM_EXITED_EARLY:{process.returncode}")
        try:
            with _direct_loopback_open(
                Request(
                    base_url + "/health",
                    method="GET",
                ),
                timeout=3.0,
            ) as response:
                if response.status != 200:
                    raise Stage0Error(
                        "VLLM_HEALTH_NON_200:"
                        + str(response.status)
                    )
            models = _get_json(base_url + "/v1/models", 5.0)
            model_ids = {
                row.get("id")
                for row in models.get("data", [])
                if isinstance(row, dict)
            }
            required = {PARENT_CHECKPOINT_ID, CANDIDATE_CHECKPOINT_ID}
            if not required.issubset(model_ids):
                raise Stage0Error(
                    "VLLM_MODELS_MISSING:" + repr(sorted(model_ids))
                )
            return {
                "health": "PASS",
                "model_ids": sorted(model_ids),
            }
        except HTTPError as exc:
            body = b""
            try:
                body = exc.read()
            except Exception:
                body = b""
            last_error = (
                "HTTPError("
                + "url="
                + repr(exc.geturl())
                + ",code="
                + repr(exc.code)
                + ",reason="
                + repr(exc.reason)
                + ",body="
                + repr(
                    body[
                        :512
                    ].decode(
                        "utf-8",
                        errors="replace",
                    )
                )
                + ")"
            )
            time.sleep(2.0)
        except (
            URLError,
            TimeoutError,
            OSError,
            ValueError,
            Stage0Error,
        ) as exc:
            last_error = repr(exc)
            time.sleep(2.0)
    raise Stage0Error("VLLM_READINESS_TIMEOUT:" + last_error)


def probe_registered_models(*, base_url: str) -> dict[str, Any]:
    results = []
    for model in (PARENT_CHECKPOINT_ID, CANDIDATE_CHECKPOINT_ID):
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "user", "content": "Reply with the word READY."}
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 8,
        }).encode("utf-8")
        request = Request(
            base_url + "/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _direct_loopback_open(
            request,
            timeout=180.0,
        ) as response:
            body = response.read()
        value = json.loads(body.decode("utf-8"))
        if value.get("model") != model:
            raise Stage0Error(f"VLLM_PROBE_MODEL_IDENTITY_CHANGED:{model}")
        results.append({
            "requested_model": model,
            "returned_model": value.get("model"),
            "choice_count": len(value.get("choices", [])),
        })
    return {
        "schema_id": "HUMAN_PILOT_STAGE0_VLLM_READINESS_V1",
        "schema_version": 1,
        "status": "PASS",
        "model_probe_count": len(results),
        "probes": results,
        "alfworld_execution_count": 0,
    }
