from __future__ import annotations

from collections.abc import Mapping

from pchsi.reference_loop.canonical import strict_json_loads


class ProviderResponseError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        failure_class: str,
        logical_method_status: str,
        counts_as_method_failure: bool,
    ) -> None:
        super().__init__(message)
        self.failure_class = failure_class
        self.logical_method_status = logical_method_status
        self.counts_as_method_failure = counts_as_method_failure


def parse_provider_response(raw: bytes) -> dict[str, object]:
    value = strict_json_loads(raw)
    if not isinstance(value, dict):
        raise ProviderResponseError(
            "provider response must be one JSON object",
            failure_class="PROVIDER_RESPONSE_ROOT_INVALID",
            logical_method_status="SCHEMA_INVALID",
            counts_as_method_failure=True,
        )
    return value


def _extract_payload(response: Mapping[str, object]) -> dict[str, object]:
    status = response.get("status")
    if status == "incomplete":
        details = response.get("incomplete_details")
        reason = details.get("reason") if isinstance(details, dict) else None
        return {"kind": "INCOMPLETE", "reason": reason}
    if status != "completed":
        return {"kind": "NONCOMPLETED_STATUS", "reason": status}

    output = response.get("output")
    if not isinstance(output, list):
        return {"kind": "MALFORMED", "reason": "output_not_array"}

    texts: list[str] = []
    refusals: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "refusal" and isinstance(
                part.get("refusal"), str
            ):
                refusals.append(part["refusal"])
            elif part.get("type") == "output_text" and isinstance(
                part.get("text"), str
            ):
                texts.append(part["text"])

    if refusals:
        return {"kind": "REFUSAL", "refusal": "\n".join(refusals)}
    if len(texts) == 1:
        return {"kind": "OUTPUT_TEXT", "output_text": texts[0]}
    return {
        "kind": "MALFORMED",
        "reason": f"output_text_count={len(texts)}",
    }


def extract_output_text(response: Mapping[str, object]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    payload = _extract_payload(response)
    kind = payload["kind"]
    if kind == "OUTPUT_TEXT":
        return str(payload["output_text"])
    if kind == "REFUSAL":
        raise ProviderResponseError(
            str(payload.get("refusal") or "provider refusal"),
            failure_class="METHOD_REFUSAL",
            logical_method_status="REFUSED",
            counts_as_method_failure=True,
        )
    if kind == "INCOMPLETE":
        reason = payload.get("reason")
        failure_class = (
            "METHOD_OUTPUT_INCOMPLETE_MAX_OUTPUT_TOKENS"
            if reason == "max_output_tokens"
            else "METHOD_OUTPUT_INCOMPLETE"
        )
        raise ProviderResponseError(
            f"provider response incomplete: {reason}",
            failure_class=failure_class,
            logical_method_status="SEMANTIC_INVALID",
            counts_as_method_failure=True,
        )
    if kind == "NONCOMPLETED_STATUS":
        raise ProviderResponseError(
            f"provider response status is not completed: {payload.get('reason')}",
            failure_class="METHOD_PROVIDER_NONCOMPLETED_STATUS",
            logical_method_status="SEMANTIC_INVALID",
            counts_as_method_failure=True,
        )
    raise ProviderResponseError(
        f"provider response is malformed: {payload.get('reason')}",
        failure_class="METHOD_PROVIDER_RESPONSE_MALFORMED",
        logical_method_status="SCHEMA_INVALID",
        counts_as_method_failure=True,
    )


def usage_summary(response: Mapping[str, object]) -> dict[str, object]:
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    details = (
        usage.get("output_tokens_details")
        if isinstance(usage.get("output_tokens_details"), dict)
        else {}
    )
    return {
        "provider_response_id": response.get("id"),
        "returned_model": response.get("model"),
        "response_created_at": response.get("created_at"),
        "status": response.get("status"),
        "service_tier": response.get("service_tier"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
    }
