"""Strict parser for the E1 RAW_WITH_MENU_V1 policy interface.

This module validates only the model-output envelope and the literal
action string. It does not check whether the action is present in the
environment's admissible-command menu; that is the responsibility of
the Runtime Core admissibility stage.

The parser performs no repair, canonicalisation, case conversion,
spelling correction, fuzzy matching or action substitution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Final, NoReturn


__all__ = [
    "FailureStage",
    "ParserFailureCode",
    "ParserStatus",
    "RawPolicyParseResult",
    "parse_raw_policy_response",
]


class ParserStatus(str, Enum):
    """Overall parser result."""

    SUCCESS = "success"
    FAILED = "failed"


class FailureStage(str, Enum):
    """Stage at which parsing failed."""

    ENVELOPE = "envelope"
    ACTION_NORMALIZATION = "action_normalization"


class ParserFailureCode(str, Enum):
    """Frozen failure codes for RAW_POLICY_PARSER_V1."""

    ENVELOPE_INVALID_JSON = "ENVELOPE_INVALID_JSON"
    ENVELOPE_TRAILING_DATA = "ENVELOPE_TRAILING_DATA"
    ENVELOPE_TOP_LEVEL_NOT_OBJECT = (
        "ENVELOPE_TOP_LEVEL_NOT_OBJECT"
    )
    ENVELOPE_DUPLICATE_MEMBER = (
        "ENVELOPE_DUPLICATE_MEMBER"
    )
    ENVELOPE_MEMBER_COUNT_INVALID = (
        "ENVELOPE_MEMBER_COUNT_INVALID"
    )
    ENVELOPE_MEMBER_NAME_INVALID = (
        "ENVELOPE_MEMBER_NAME_INVALID"
    )
    ENVELOPE_ACTION_NOT_STRING = (
        "ENVELOPE_ACTION_NOT_STRING"
    )
    ACTION_EMPTY = "ACTION_EMPTY"
    ACTION_MULTILINE = "ACTION_MULTILINE"
    ACTION_CONTROL_CHARACTER = "ACTION_CONTROL_CHARACTER"
    ACTION_TOO_LONG = "ACTION_TOO_LONG"


@dataclass(frozen=True, slots=True)
class RawPolicyParseResult:
    """Immutable result of parsing one completed model response."""

    status: ParserStatus
    normalized_action: str | None
    failure_stage: FailureStage | None
    failure_code: ParserFailureCode | None


@dataclass(frozen=True, slots=True)
class _JsonObject:
    """Ordered JSON object preserved before dictionary conversion."""

    pairs: tuple[tuple[str, object], ...]


class _DuplicateMemberError(ValueError):
    """Raised when any decoded JSON object repeats a key."""


class _NonStandardConstantError(ValueError):
    """Raised for NaN and positive or negative Infinity."""


_OUTER_RESPONSE_WHITESPACE: Final[str] = " \t\r\n"
_ACTION_EDGE_WHITESPACE: Final[str] = " "


def _build_object(
    pairs: list[tuple[str, object]],
) -> _JsonObject:
    """Preserve object members and reject duplicate names."""

    seen: set[str] = set()
    preserved: list[tuple[str, object]] = []

    for name, value in pairs:
        if name in seen:
            raise _DuplicateMemberError(name)

        seen.add(name)
        preserved.append((name, value))

    return _JsonObject(
        pairs=tuple(preserved),
    )


def _reject_nonstandard_constant(
    value: str,
) -> NoReturn:
    """Reject NaN, Infinity and -Infinity."""

    raise _NonStandardConstantError(value)


_DECODER: Final[json.JSONDecoder] = json.JSONDecoder(
    object_pairs_hook=_build_object,
    parse_constant=_reject_nonstandard_constant,
    strict=True,
)


def _failure(
    *,
    stage: FailureStage,
    code: ParserFailureCode,
) -> RawPolicyParseResult:
    """Construct an immutable failed result."""

    return RawPolicyParseResult(
        status=ParserStatus.FAILED,
        normalized_action=None,
        failure_stage=stage,
        failure_code=code,
    )


def _success(
    action: str,
) -> RawPolicyParseResult:
    """Construct an immutable successful result."""

    return RawPolicyParseResult(
        status=ParserStatus.SUCCESS,
        normalized_action=action,
        failure_stage=None,
        failure_code=None,
    )


def _contains_forbidden_control_character(
    action: str,
) -> bool:
    """Return whether action contains a C0, DEL or C1 control."""

    for character in action:
        codepoint = ord(character)

        if codepoint <= 0x1F:
            return True

        if 0x7F <= codepoint <= 0x9F:
            return True

    return False


def parse_raw_policy_response(
    raw_response: str,
    *,
    max_action_codepoints: int = 256,
) -> RawPolicyParseResult:
    """Parse exactly one RAW_POLICY_PARSER_V1 response.

    The accepted envelope is exactly one JSON object containing
    exactly one string-valued member named ``action``.

    Only ASCII spaces are removed from the two ends of the action.
    No other transformation is performed.
    """

    if not isinstance(raw_response, str):
        raise TypeError(
            "raw_response must be str"
        )

    source = raw_response.strip(
        _OUTER_RESPONSE_WHITESPACE
    )

    try:
        decoded, end_index = _DECODER.raw_decode(
            source
        )
    except _DuplicateMemberError:
        return _failure(
            stage=FailureStage.ENVELOPE,
            code=(
                ParserFailureCode
                .ENVELOPE_DUPLICATE_MEMBER
            ),
        )
    except (
        _NonStandardConstantError,
        json.JSONDecodeError,
    ):
        return _failure(
            stage=FailureStage.ENVELOPE,
            code=ParserFailureCode.ENVELOPE_INVALID_JSON,
        )

    if end_index != len(source):
        return _failure(
            stage=FailureStage.ENVELOPE,
            code=ParserFailureCode.ENVELOPE_TRAILING_DATA,
        )

    if not isinstance(decoded, _JsonObject):
        return _failure(
            stage=FailureStage.ENVELOPE,
            code=(
                ParserFailureCode
                .ENVELOPE_TOP_LEVEL_NOT_OBJECT
            ),
        )

    if len(decoded.pairs) != 1:
        return _failure(
            stage=FailureStage.ENVELOPE,
            code=(
                ParserFailureCode
                .ENVELOPE_MEMBER_COUNT_INVALID
            ),
        )

    member_name, member_value = decoded.pairs[0]

    if member_name != "action":
        return _failure(
            stage=FailureStage.ENVELOPE,
            code=(
                ParserFailureCode
                .ENVELOPE_MEMBER_NAME_INVALID
            ),
        )

    if not isinstance(member_value, str):
        return _failure(
            stage=FailureStage.ENVELOPE,
            code=(
                ParserFailureCode
                .ENVELOPE_ACTION_NOT_STRING
            ),
        )

    action = member_value.strip(
        _ACTION_EDGE_WHITESPACE
    )

    if not action:
        return _failure(
            stage=FailureStage.ACTION_NORMALIZATION,
            code=ParserFailureCode.ACTION_EMPTY,
        )

    if "\n" in action or "\r" in action:
        return _failure(
            stage=FailureStage.ACTION_NORMALIZATION,
            code=ParserFailureCode.ACTION_MULTILINE,
        )

    if _contains_forbidden_control_character(
        action
    ):
        return _failure(
            stage=FailureStage.ACTION_NORMALIZATION,
            code=(
                ParserFailureCode
                .ACTION_CONTROL_CHARACTER
            ),
        )

    if len(action) > max_action_codepoints:
        return _failure(
            stage=FailureStage.ACTION_NORMALIZATION,
            code=ParserFailureCode.ACTION_TOO_LONG,
        )

    return _success(action)
