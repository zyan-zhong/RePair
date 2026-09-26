from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pchsi.reference_loop.canonical import (
    canonical_json_bytes,
    domain_hash,
    write_new_json,
)
from .access import validate_task_access
from .identity import build_logical_call_record, build_transport_attempt_record
from .ledger import (
    create_call_directory,
    monotonic_ms,
    record_raw_request,
    record_raw_response,
    record_rendered_request,
)
from .manifest import load_runtime_manifest
from .output_validation import (
    validate_stage_output,
    validated_artifact_identity,
)
from .p2_bridge import P2TransportError, execute_via_existing_p2
from .request_renderer import render_stage_request
from .response import (
    ProviderResponseError,
    extract_output_text,
    parse_provider_response,
    usage_summary,
)


def _write_logical_call(
    *,
    call_dir: Path,
    logical_call_id: str,
    unit_identity: Mapping[str, object],
    stage_id: str,
    condition_id: str | None,
    round_id: str,
    policy_version: str,
    request_body_sha256: str,
    terminal_method_status: str,
    contributing_attempt_id: str,
) -> None:
    logical = build_logical_call_record(
        logical_call_id=logical_call_id,
        scientific_unit_identity_sha256=unit_identity["identity_sha256"],
        role=(
            "ANALYZER"
            if not stage_id.startswith("R-")
            else "TRAINING_RESEARCHER"
        ),
        stage_id=stage_id,
        condition_id=condition_id,
        round_id=round_id,
        policy_version=policy_version,
        runtime_manifest_sha256=load_runtime_manifest()[
            "runtime_manifest_sha256"
        ],
        request_body_sha256=request_body_sha256,
        terminal_method_status=terminal_method_status,
        contributing_attempt_id=contributing_attempt_id,
    )
    write_new_json(call_dir / "logical_call.json", logical)


def _transport_meta(
    *,
    http_status: int | None,
    response_headers: Mapping[str, str],
    provider_http_request_id: str | None,
    failure_class: str | None,
    counts_as_method_failure: bool | None,
    hard_stop: bool | None,
) -> dict[str, object]:
    return {
        "schema_id": "P2_TRANSPORT_HTTP_META_V2",
        "schema_version": 2,
        "http_status": http_status,
        "response_headers_allowlisted": dict(response_headers),
        "provider_http_request_id": provider_http_request_id,
        "failure_class": failure_class,
        "counts_as_method_failure": counts_as_method_failure,
        "hard_stop": hard_stop,
    }


def execute_one(
    *,
    output_root: Path,
    unit_identity: Mapping[str, object],
    stage_id: str,
    condition_id: str | None,
    round_id: str,
    policy_version: str,
    projection: Mapping[str, object],
    task_access: Mapping[str, object],
    max_infrastructure_attempt_restarts: int = 0,
) -> dict[str, object]:
    if (
        type(max_infrastructure_attempt_restarts) is not int
        or max_infrastructure_attempt_restarts < 0
    ):
        raise ValueError(
            "max_infrastructure_attempt_restarts must be nonnegative int"
        )
    validate_task_access(task_access, live_call=True)
    bundle = render_stage_request(stage_id=stage_id, projection=projection)
    logical_call_id = domain_hash(
        "COGNITIVE_LOGICAL_CALL_ID_V1",
        {
            "scientific_unit_identity_sha256": unit_identity[
                "identity_sha256"
            ],
            "stage_id": stage_id,
            "condition_id": condition_id,
            "round_id": round_id,
            "policy_version": policy_version,
            "request_body_sha256": bundle["request_body_sha256"],
        },
    )
    call_dir = create_call_directory(output_root, logical_call_id)
    record_rendered_request(call_dir, bundle)
    raw_request = canonical_json_bytes(bundle["provider_request"])
    raw_request_sha = record_raw_request(call_dir, raw_request)

    def write_attempt_raw(index: int, raw: bytes) -> str:
        path = call_dir / f"raw_response_attempt_{index:03d}.json"
        if path.exists():
            raise FileExistsError(path)
        path.write_bytes(raw)
        from pchsi.reference_loop.canonical import sha256_bytes
        return sha256_bytes(raw)

    def write_attempt_meta(index: int, value: Mapping[str, object]) -> None:
        write_new_json(
            call_dir / f"transport_http_meta_attempt_{index:03d}.json",
            dict(value),
        )

    transport = None
    contributing_attempt_id = None
    last_retry_class: str | None = None
    for attempt_index in range(max_infrastructure_attempt_restarts + 1):
        start = monotonic_ms()
        attempt_id = f"{logical_call_id}:{attempt_index}"
        try:
            transport = execute_via_existing_p2(
                bundle,
                call_dir,
                client_request_id=logical_call_id,
            )
        except P2TransportError as error:
            raw_response_sha = None
            if error.raw_response is not None:
                raw_response_sha = write_attempt_raw(
                    attempt_index,
                    error.raw_response,
                )
            meta = _transport_meta(
                http_status=error.http_status,
                response_headers=error.response_headers,
                provider_http_request_id=error.provider_http_request_id,
                failure_class=error.failure_class,
                counts_as_method_failure=error.counts_as_method_failure,
                hard_stop=error.hard_stop,
            )
            write_attempt_meta(attempt_index, meta)
            attempt = build_transport_attempt_record(
                logical_call_id=logical_call_id,
                transport_attempt_id=attempt_id,
                transport_attempt_index=attempt_index,
                bytes_transmission_state=error.bytes_transmission_state,
                retry_class=error.retry_class,
                retry_reason=error.failure_class,
                retry_authority=error.retry_authority,
                provider_response_id=None,
                terminal_attempt_status=error.terminal_attempt_status,
                ambiguous_post_send_disposition_id=None,
                raw_request_sha256=raw_request_sha,
                raw_response_sha256=raw_response_sha,
                input_tokens=None,
                output_tokens=None,
                reasoning_tokens=None,
                latency_ms=monotonic_ms() - start,
                cost_usd=None,
            )
            write_new_json(
                call_dir / f"attempt_{attempt_index:03d}.json",
                attempt,
            )
            retryable = error.retry_class in {
                "SAFE_PRE_SEND",
                "SAFE_PROVIDER_REJECTION",
            }
            if (
                retryable
                and not error.hard_stop
                and attempt_index
                < max_infrastructure_attempt_restarts
            ):
                last_retry_class = error.retry_class
                continue

            exhausted_infrastructure = (
                retryable
                and not error.hard_stop
                and attempt_index
                >= max_infrastructure_attempt_restarts
            )
            terminal_hard_stop = (
                True if exhausted_infrastructure else error.hard_stop
            )
            write_new_json(
                call_dir / "transport_http_meta.json",
                {
                    **meta,
                    "hard_stop": terminal_hard_stop,
                },
            )
            if error.raw_response is not None:
                record_raw_response(call_dir, error.raw_response)
            write_new_json(
                call_dir / "method_result.json",
                {
                    "status": error.logical_method_status,
                    "error_type": type(error).__name__,
                    "failure_class": error.failure_class,
                    "message": str(error),
                    "counts_as_method_failure": (
                        error.counts_as_method_failure
                    ),
                    "hard_stop": terminal_hard_stop,
                    "infrastructure_retry_budget_exhausted": (
                        exhausted_infrastructure
                    ),
                    "transport_attempt_count": attempt_index + 1,
                },
            )
            _write_logical_call(
                call_dir=call_dir,
                logical_call_id=logical_call_id,
                unit_identity=unit_identity,
                stage_id=stage_id,
                condition_id=condition_id,
                round_id=round_id,
                policy_version=policy_version,
                request_body_sha256=bundle["request_body_sha256"],
                terminal_method_status=error.logical_method_status,
                contributing_attempt_id=attempt_id,
            )
            return {
                "logical_call_id": logical_call_id,
                "call_dir": str(call_dir),
                "status": error.logical_method_status,
                "method_failure_reason": error.failure_class,
                "hard_stop": terminal_hard_stop,
                "transport_attempt_count": attempt_index + 1,
            }
        except Exception as error:
            attempt = build_transport_attempt_record(
                logical_call_id=logical_call_id,
                transport_attempt_id=attempt_id,
                transport_attempt_index=attempt_index,
                bytes_transmission_state="MAY_HAVE_BEEN_SENT",
                retry_class="NO_RETRY",
                retry_reason=type(error).__name__,
                retry_authority="FROZEN_RUNTIME_POLICY",
                provider_response_id=None,
                terminal_attempt_status="AMBIGUOUS_POST_SEND",
                ambiguous_post_send_disposition_id=None,
                raw_request_sha256=raw_request_sha,
                raw_response_sha256=None,
                input_tokens=None,
                output_tokens=None,
                reasoning_tokens=None,
                latency_ms=monotonic_ms() - start,
                cost_usd=None,
            )
            write_new_json(
                call_dir / f"attempt_{attempt_index:03d}.json",
                attempt,
            )
            write_new_json(
                call_dir / "method_result.json",
                {
                    "status": "AMBIGUOUS_POST_SEND",
                    "error_type": type(error).__name__,
                    "failure_class": "UNEXPECTED_BRIDGE_EXCEPTION",
                    "message": str(error),
                    "counts_as_method_failure": False,
                    "hard_stop": True,
                    "transport_attempt_count": attempt_index + 1,
                },
            )
            _write_logical_call(
                call_dir=call_dir,
                logical_call_id=logical_call_id,
                unit_identity=unit_identity,
                stage_id=stage_id,
                condition_id=condition_id,
                round_id=round_id,
                policy_version=policy_version,
                request_body_sha256=bundle["request_body_sha256"],
                terminal_method_status="AMBIGUOUS_POST_SEND",
                contributing_attempt_id=attempt_id,
            )
            return {
                "logical_call_id": logical_call_id,
                "call_dir": str(call_dir),
                "status": "AMBIGUOUS_POST_SEND",
                "method_failure_reason": type(error).__name__,
                "hard_stop": True,
                "transport_attempt_count": attempt_index + 1,
            }
        else:
            contributing_attempt_id = attempt_id
            meta = _transport_meta(
                http_status=transport.http_status,
                response_headers=transport.response_headers,
                provider_http_request_id=(
                    transport.provider_http_request_id
                ),
                failure_class=None,
                counts_as_method_failure=None,
                hard_stop=None,
            )
            write_attempt_meta(attempt_index, meta)
            write_new_json(
                call_dir / "transport_http_meta.json",
                meta,
            )
            break

    if transport is None or contributing_attempt_id is None:
        raise RuntimeError("transport loop ended without terminal outcome")

    raw_response = transport.raw_response
    raw_response_sha = record_raw_response(call_dir, raw_response)

    try:
        response = parse_provider_response(raw_response)
        usage = usage_summary(response)
    except ProviderResponseError as error:
        response = {}
        usage = {
            "provider_response_id": None,
            "returned_model": None,
            "response_created_at": None,
            "status": None,
            "service_tier": None,
            "input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
        }
        provider_error: ProviderResponseError | None = error
    else:
        provider_error = None

    final_index = int(contributing_attempt_id.rsplit(":", 1)[1])
    attempt = build_transport_attempt_record(
        logical_call_id=logical_call_id,
        transport_attempt_id=contributing_attempt_id,
        transport_attempt_index=final_index,
        bytes_transmission_state="CONFIRMED_SENT",
        retry_class=(
            "INITIAL"
            if final_index == 0
            else (last_retry_class or "SAFE_PRE_SEND")
        ),
        retry_reason=None,
        retry_authority=(
            "NOT_APPLICABLE"
            if final_index == 0
            else "FROZEN_RUNTIME_POLICY"
        ),
        provider_response_id=usage["provider_response_id"],
        terminal_attempt_status="SUCCEEDED",
        ambiguous_post_send_disposition_id=None,
        raw_request_sha256=raw_request_sha,
        raw_response_sha256=raw_response_sha,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        reasoning_tokens=usage["reasoning_tokens"],
        latency_ms=monotonic_ms() - start,
        cost_usd=None,
    )
    write_new_json(
        call_dir / f"attempt_{final_index:03d}.json",
        attempt,
    )
    write_new_json(
        call_dir / "provider_identity.json",
        {
            "requested_model": bundle["provider_request"].get("model"),
            "returned_model": usage["returned_model"],
            "response_created_at": usage["response_created_at"],
            "provider_response_id": usage["provider_response_id"],
            "service_tier": usage["service_tier"],
            "provider_behavior_bitwise_reproducibility": False,
        },
    )

    try:
        if provider_error is not None:
            raise provider_error
        text = extract_output_text(response)
        artifact = validate_stage_output(
            stage_id=stage_id,
            text=text,
            raw_response_sha256=raw_response_sha,
            projection=projection,
        )
        artifact_sha = validated_artifact_identity(
            stage_id=stage_id,
            artifact=artifact,
        )
        write_new_json(call_dir / "validated_artifact.json", artifact)
        status = "ACCEPTED"
        reason = None
    except ProviderResponseError as error:
        artifact_sha = None
        status = error.logical_method_status
        reason = error.failure_class
        write_new_json(
            call_dir / "validation_error.json",
            {
                "error_type": type(error).__name__,
                "failure_class": error.failure_class,
                "message": str(error),
                "counts_as_method_failure": error.counts_as_method_failure,
            },
        )
    except Exception as error:
        artifact_sha = None
        status = "SEMANTIC_INVALID"
        reason = f"{type(error).__name__}:{error}"
        write_new_json(
            call_dir / "validation_error.json",
            {
                "error_type": type(error).__name__,
                "failure_class": "METHOD_OUTPUT_INVALID",
                "message": str(error),
                "counts_as_method_failure": True,
            },
        )

    _write_logical_call(
        call_dir=call_dir,
        logical_call_id=logical_call_id,
        unit_identity=unit_identity,
        stage_id=stage_id,
        condition_id=condition_id,
        round_id=round_id,
        policy_version=policy_version,
        request_body_sha256=bundle["request_body_sha256"],
        terminal_method_status=status,
        contributing_attempt_id=contributing_attempt_id,
    )
    return {
        "logical_call_id": logical_call_id,
        "call_dir": str(call_dir),
        "status": status,
        "method_failure_reason": reason,
        "validated_artifact_sha256": artifact_sha,
        "usage": usage,
        "hard_stop": False,
        "transport_attempt_count": final_index + 1,
    }
