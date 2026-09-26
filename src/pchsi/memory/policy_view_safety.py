"""Policy-visible safety contracts for Failure Memory V1."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.projection_common import ProjectionClassV1


class PolicyViewStaticFailureCodeV1(str, Enum):
    MEMORY_ID_EXPOSURE = "MEMORY_ID_EXPOSURE"
    SOURCE_IDENTITY_EXPOSURE = "SOURCE_IDENTITY_EXPOSURE"
    ANALYZER_IDENTITY_EXPOSURE = "ANALYZER_IDENTITY_EXPOSURE"
    EFFECT_OR_PROMOTION_EXPOSURE = "EFFECT_OR_PROMOTION_EXPOSURE"
    HIDDEN_OR_FUTURE_STATE_EXPOSURE = "HIDDEN_OR_FUTURE_STATE_EXPOSURE"
    STRICT_ACTION_JSON = "STRICT_ACTION_JSON"
    EXPLICIT_ACTION_OUTPUT_INSTRUCTION = (
        "EXPLICIT_ACTION_OUTPUT_INSTRUCTION"
    )
    NUMBERED_MENU_SELECTION = "NUMBERED_MENU_SELECTION"
    PROMPT_FIELD_SPOOFING = "PROMPT_FIELD_SPOOFING"
    SYSTEM_MESSAGE_SPOOFING = "SYSTEM_MESSAGE_SPOOFING"
    META_INSTRUCTION = "META_INSTRUCTION"


def _expect_exact_keys(
    value: object,
    expected: frozenset[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{label} fields do not match contract: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _require_sha(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError("projection_sha256 must be 64 lowercase hex")
    return value


@dataclass(frozen=True, slots=True)
class PolicyViewSafetyReportV1:
    schema_id: str
    schema_version: int
    projection_class: ProjectionClassV1
    projection_sha256: str
    static_status: str
    static_failure_codes: tuple[PolicyViewStaticFailureCodeV1, ...]
    contextual_menu_check_required: bool
    critical_safety_failure: bool

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "projection_class",
            "projection_sha256",
            "static_status",
            "static_failure_codes",
            "contextual_menu_check_required",
            "critical_safety_failure",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != "POLICY_VIEW_SAFETY_REPORT_V1":
            raise ValueError("schema_id mismatch")
        if self.schema_version != 1:
            raise ValueError("schema_version mismatch")
        if not isinstance(self.projection_class, ProjectionClassV1):
            raise TypeError("projection_class type mismatch")
        _require_sha(self.projection_sha256)
        if self.static_status not in {"PASS", "FAIL"}:
            raise ValueError("static_status is invalid")
        if type(self.static_failure_codes) is not tuple:
            raise TypeError("static_failure_codes must be tuple")
        if any(
            not isinstance(item, PolicyViewStaticFailureCodeV1)
            for item in self.static_failure_codes
        ):
            raise TypeError("static_failure_codes contain invalid item")
        if len(self.static_failure_codes) != len(
            set(self.static_failure_codes)
        ):
            raise ValueError("static_failure_codes must be unique")
        expected_fail = bool(self.static_failure_codes)
        if (self.static_status == "FAIL") != expected_fail:
            raise ValueError(
                "static_status must be FAIL iff failure codes are nonempty"
            )
        if self.critical_safety_failure != expected_fail:
            raise ValueError(
                "all V1 static failures are critical"
            )
        if type(self.contextual_menu_check_required) is not bool:
            raise TypeError(
                "contextual_menu_check_required must be bool"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "projection_class": self.projection_class.value,
            "projection_sha256": self.projection_sha256,
            "static_status": self.static_status,
            "static_failure_codes": [
                item.value for item in self.static_failure_codes
            ],
            "contextual_menu_check_required": (
                self.contextual_menu_check_required
            ),
            "critical_safety_failure": self.critical_safety_failure,
        }

    @classmethod
    def from_dict(cls, value: object) -> "PolicyViewSafetyReportV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "policy-view safety report",
        )
        raw_codes = payload["static_failure_codes"]
        if not isinstance(raw_codes, list):
            raise TypeError("static_failure_codes must be JSON array")
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            projection_class=ProjectionClassV1(
                payload["projection_class"]
            ),
            projection_sha256=payload["projection_sha256"],
            static_status=payload["static_status"],
            static_failure_codes=tuple(
                PolicyViewStaticFailureCodeV1(item)
                for item in raw_codes
            ),
            contextual_menu_check_required=payload[
                "contextual_menu_check_required"
            ],
            critical_safety_failure=payload[
                "critical_safety_failure"
            ],
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> "PolicyViewSafetyReportV1":
        return cls.from_dict(strict_json_loads(value))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


_KEY_MEMORY_RE = re.compile(
    r"(?:^|_)(?:memory_id|record_id|memory_lineage_id)(?:$|_)",
    re.IGNORECASE,
)
_KEY_SOURCE_RE = re.compile(
    r"(?:^|_)(?:source_task|source_gamefile|source_seed|source_attempt|"
    r"task_id|gamefile|seed)(?:$|_)",
    re.IGNORECASE,
)
_KEY_ANALYZER_RE = re.compile(
    r"(?:^|_)(?:analyzer|origin_identity|origin_role)(?:$|_)",
    re.IGNORECASE,
)
_KEY_EFFECT_RE = re.compile(
    r"(?:^|_)(?:effect|promotion|lifecycle|governance|confidence)(?:$|_)",
    re.IGNORECASE,
)
_KEY_HIDDEN_RE = re.compile(
    r"(?:^|_)(?:hidden|future|oracle|score|done|won|terminal_result)(?:$|_)",
    re.IGNORECASE,
)

_TEXT_SOURCE_RE = re.compile(
    r"\b(?:memory[_ -]?id|source[_ -]?(?:task|gamefile|seed|attempt)|"
    r"gamefile[_ -]?id)\b",
    re.IGNORECASE,
)
_TEXT_ANALYZER_RE = re.compile(
    r"\b(?:analyzer[_ -]?(?:id|identity)|origin[_ -]?identity)\b",
    re.IGNORECASE,
)
_TEXT_EFFECT_RE = re.compile(
    r"\b(?:effect[_ -]?(?:status|score)|promotion[_ -]?status|"
    r"lifecycle[_ -]?status|confidence[_ -]?score)\b",
    re.IGNORECASE,
)
_TEXT_HIDDEN_RE = re.compile(
    r"\b(?:hidden[_ -]?state|future[_ -]?outcome|oracle[_ -]?path|"
    r"ground[_ -]?truth[_ -]?path)\b",
    re.IGNORECASE,
)
_ACTION_INSTRUCTION_RE = re.compile(
    r"\b(?:execute exactly|the correct action is|output\s*\{\s*"
    r"[\"']action[\"']\s*:)",
    re.IGNORECASE,
)
_NUMBERED_MENU_RE = re.compile(
    r"\b(?:choose|select)\s+(?:item\s*)?(?:#?\d+|the\s+"
    r"(?:first|second|third|fourth|fifth)\s+(?:command|item))\b",
    re.IGNORECASE,
)
_PROMPT_FIELD_RE = re.compile(
    r"^\s*(?:OUTPUT_REQUIREMENT|PROMPT|DEVELOPER|ASSISTANT)\s*:",
    re.IGNORECASE,
)
_SYSTEM_RE = re.compile(
    r"^\s*SYSTEM\s*:",
    re.IGNORECASE,
)
_META_RE = re.compile(
    r"\b(?:ignore previous|disregard (?:the )?(?:previous )?"
    r"instructions?)\b",
    re.IGNORECASE,
)


def _iter_leaves(
    value: object,
    path: tuple[str, ...] = (),
):
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError("Policy-visible payload keys must be strings")
            yield from _iter_leaves(child, path + (key,))
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _iter_leaves(
                child,
                path + (str(index),),
            )
        return
    yield path, value


def policy_visible_contains_bound_identity_v1(
    *,
    policy_visible_payload: object,
    forbidden_exact_identities: tuple[str, ...],
) -> bool:
    """Return whether any exact frozen identity occurs in a visible string leaf.

    Matching is deliberately case-sensitive and byte/text-exact at the identity
    value level: no stripping, lowercasing, casefolding, fuzzy matching,
    semantic normalization or numeric stringification is performed.
    """

    if type(forbidden_exact_identities) is not tuple:
        raise TypeError("forbidden_exact_identities must be tuple")
    if any(
        not isinstance(item, str) or not item
        for item in forbidden_exact_identities
    ):
        raise ValueError(
            "forbidden_exact_identities items must be nonempty str"
        )

    visible_strings = tuple(
        leaf
        for _, leaf in _iter_leaves(policy_visible_payload)
        if isinstance(leaf, str)
    )
    return any(
        identity in leaf
        for identity in forbidden_exact_identities
        for leaf in visible_strings
    )


def _is_strict_action_json(text: str) -> bool:
    stripped = text.strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return False
    try:
        payload = strict_json_loads(stripped)
    except ValueError:
        return False
    return (
        isinstance(payload, dict)
        and frozenset(payload) == {"action"}
        and isinstance(payload["action"], str)
    )


def audit_policy_visible_payload_v1(
    *,
    projection_class: ProjectionClassV1,
    policy_visible_payload: object,
    has_nonempty_recovery: bool,
) -> PolicyViewSafetyReportV1:
    if not isinstance(projection_class, ProjectionClassV1):
        raise TypeError("projection_class type mismatch")
    if type(has_nonempty_recovery) is not bool:
        raise TypeError("has_nonempty_recovery must be bool")
    if projection_class is not ProjectionClassV1.FM3 and has_nonempty_recovery:
        raise ValueError("only FM3 may have nonempty recovery")

    found: set[PolicyViewStaticFailureCodeV1] = set()

    for path, leaf in _iter_leaves(policy_visible_payload):
        for key in path:
            if _KEY_MEMORY_RE.search(key):
                found.add(
                    PolicyViewStaticFailureCodeV1.MEMORY_ID_EXPOSURE
                )
            if _KEY_SOURCE_RE.search(key):
                found.add(
                    PolicyViewStaticFailureCodeV1.SOURCE_IDENTITY_EXPOSURE
                )
            if _KEY_ANALYZER_RE.search(key):
                found.add(
                    PolicyViewStaticFailureCodeV1.ANALYZER_IDENTITY_EXPOSURE
                )
            if _KEY_EFFECT_RE.search(key):
                found.add(
                    PolicyViewStaticFailureCodeV1
                    .EFFECT_OR_PROMOTION_EXPOSURE
                )
            if _KEY_HIDDEN_RE.search(key):
                found.add(
                    PolicyViewStaticFailureCodeV1
                    .HIDDEN_OR_FUTURE_STATE_EXPOSURE
                )

        if not isinstance(leaf, str):
            continue

        if _TEXT_SOURCE_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1.SOURCE_IDENTITY_EXPOSURE
            )
        if _TEXT_ANALYZER_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1.ANALYZER_IDENTITY_EXPOSURE
            )
        if _TEXT_EFFECT_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1
                .EFFECT_OR_PROMOTION_EXPOSURE
            )
        if _TEXT_HIDDEN_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1
                .HIDDEN_OR_FUTURE_STATE_EXPOSURE
            )
        if _is_strict_action_json(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1.STRICT_ACTION_JSON
            )
        if _ACTION_INSTRUCTION_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1
                .EXPLICIT_ACTION_OUTPUT_INSTRUCTION
            )
        if _NUMBERED_MENU_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1.NUMBERED_MENU_SELECTION
            )
        if _PROMPT_FIELD_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1.PROMPT_FIELD_SPOOFING
            )
        if _SYSTEM_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1.SYSTEM_MESSAGE_SPOOFING
            )
        if _META_RE.search(leaf):
            found.add(
                PolicyViewStaticFailureCodeV1.META_INSTRUCTION
            )

    ordered = tuple(
        code
        for code in PolicyViewStaticFailureCodeV1
        if code in found
    )
    projection_sha256 = sha256_bytes(
        canonical_json_bytes(policy_visible_payload)
    )
    return PolicyViewSafetyReportV1(
        schema_id="POLICY_VIEW_SAFETY_REPORT_V1",
        schema_version=1,
        projection_class=projection_class,
        projection_sha256=projection_sha256,
        static_status="FAIL" if ordered else "PASS",
        static_failure_codes=ordered,
        contextual_menu_check_required=(
            projection_class is ProjectionClassV1.FM3
            and has_nonempty_recovery
        ),
        critical_safety_failure=bool(ordered),
    )


def validate_contextual_menu_oracle_v1(
    *,
    recovery_procedure: tuple[str, ...],
    current_admissible_commands: tuple[str, ...],
) -> None:
    if type(recovery_procedure) is not tuple:
        raise TypeError("recovery_procedure must be tuple")
    if type(current_admissible_commands) is not tuple:
        raise TypeError("current_admissible_commands must be tuple")
    if any(not isinstance(item, str) for item in recovery_procedure):
        raise TypeError("recovery_procedure items must be str")
    if any(not isinstance(item, str) for item in current_admissible_commands):
        raise TypeError("current_admissible_commands items must be str")

    exact_commands = set(current_admissible_commands)
    for step in recovery_procedure:
        if step in exact_commands:
            raise ValueError("POLICY_VIEW_CONTEXTUAL_MENU_ORACLE")
