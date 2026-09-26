"""Deterministic classification for explicit infrastructure-only cognitive-call recovery."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _safe_provider_http(status: object) -> bool:
    return isinstance(status, int) and (status == 429 or 500 <= status <= 599)


def classify_infrastructure_recovery(
    *,
    method: Mapping[str, object],
    attempt: Mapping[str, object],
    transport_meta: Mapping[str, object],
) -> dict[str, Any]:
    """Return eligibility under the frozen P2 retry boundary.

    `INFRASTRUCTURE_UNAVAILABLE` by itself is never sufficient. Recovery is
    legal only for an exact SAFE_PRE_SEND or SAFE_PROVIDER_REJECTION
    conjunction. Ambiguous post-send, auth/config, runtime-defect and method
    failures remain no-retry.
    """

    common = (
        method.get("status") == "INFRASTRUCTURE_UNAVAILABLE"
        and method.get("counts_as_method_failure") is False
        and method.get("hard_stop") is False
        and transport_meta.get("counts_as_method_failure") is False
        and transport_meta.get("hard_stop") is False
        and attempt.get("retry_authority") == "HUMAN_DISPOSITION"
    )

    if (
        common
        and method.get("failure_class") == "PRE_SEND_INFRASTRUCTURE_UNAVAILABLE"
        and transport_meta.get("failure_class") == "PRE_SEND_INFRASTRUCTURE_UNAVAILABLE"
        and attempt.get("bytes_transmission_state") == "NOT_SENT"
        and attempt.get("retry_class") == "SAFE_PRE_SEND"
        and attempt.get("terminal_attempt_status") == "INFRASTRUCTURE_ERROR"
        and transport_meta.get("http_status") is None
    ):
        return {
            "eligible": True,
            "recovery_class": "SAFE_PRE_SEND",
            "request_confirmed_not_sent": True,
            "provider_rejection_confirmed": False,
        }

    if (
        common
        and method.get("failure_class") == "PROVIDER_TRANSIENT_UNAVAILABLE"
        and transport_meta.get("failure_class") == "PROVIDER_TRANSIENT_UNAVAILABLE"
        and attempt.get("bytes_transmission_state") == "CONFIRMED_SENT"
        and attempt.get("retry_class") == "SAFE_PROVIDER_REJECTION"
        and attempt.get("terminal_attempt_status") == "PROVIDER_REJECTED"
        and _safe_provider_http(transport_meta.get("http_status"))
    ):
        return {
            "eligible": True,
            "recovery_class": "SAFE_PROVIDER_REJECTION",
            "request_confirmed_not_sent": False,
            "provider_rejection_confirmed": True,
        }

    return {
        "eligible": False,
        "recovery_class": None,
        "request_confirmed_not_sent": False,
        "provider_rejection_confirmed": False,
    }
