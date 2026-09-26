from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pchsi.evaluation.raw_policy_parser import (
    FailureStage,
    ParserFailureCode,
    ParserStatus,
    parse_raw_policy_response,
)


def _assert_failure(
    raw_response: str,
    *,
    stage: FailureStage,
    code: ParserFailureCode,
) -> None:
    result = parse_raw_policy_response(
        raw_response
    )

    assert result.status is ParserStatus.FAILED
    assert result.normalized_action is None
    assert result.failure_stage is stage
    assert result.failure_code is code


def test_accepts_exact_single_action_object() -> None:
    result = parse_raw_policy_response(
        ' \n{"action":"  look  "}\t'
    )

    assert result.status is ParserStatus.SUCCESS
    assert result.normalized_action == "look"
    assert result.failure_stage is None
    assert result.failure_code is None


@pytest.mark.parametrize(
    (
        "raw_response",
        "expected_code",
    ),
    [
        (
            'Here is my action: {"action":"look"}',
            ParserFailureCode.ENVELOPE_INVALID_JSON,
        ),
        (
            '```json\n{"action":"look"}\n```',
            ParserFailureCode.ENVELOPE_INVALID_JSON,
        ),
        (
            '{"action":"look"}{"action":"done"}',
            ParserFailureCode.ENVELOPE_TRAILING_DATA,
        ),
        (
            '["look"]',
            ParserFailureCode.ENVELOPE_TOP_LEVEL_NOT_OBJECT,
        ),
        (
            "null",
            ParserFailureCode.ENVELOPE_TOP_LEVEL_NOT_OBJECT,
        ),
        (
            '{"action":null}',
            ParserFailureCode.ENVELOPE_ACTION_NOT_STRING,
        ),
        (
            '{"action":123}',
            ParserFailureCode.ENVELOPE_ACTION_NOT_STRING,
        ),
        (
            '{"action":"look","reason":"inspect"}',
            ParserFailureCode.ENVELOPE_MEMBER_COUNT_INVALID,
        ),
        (
            '{"other":"look"}',
            ParserFailureCode.ENVELOPE_MEMBER_NAME_INVALID,
        ),
        (
            '{"action":"look","action":"done"}',
            ParserFailureCode.ENVELOPE_DUPLICATE_MEMBER,
        ),
        (
            '{"action":NaN}',
            ParserFailureCode.ENVELOPE_INVALID_JSON,
        ),
        (
            "\ufeff{\"action\":\"look\"}",
            ParserFailureCode.ENVELOPE_INVALID_JSON,
        ),
    ],
)
def test_rejects_invalid_envelopes(
    raw_response: str,
    expected_code: ParserFailureCode,
) -> None:
    _assert_failure(
        raw_response,
        stage=FailureStage.ENVELOPE,
        code=expected_code,
    )


@pytest.mark.parametrize(
    (
        "raw_response",
        "expected_code",
    ),
    [
        (
            '{"action":"   "}',
            ParserFailureCode.ACTION_EMPTY,
        ),
        (
            '{"action":"look\\nnow"}',
            ParserFailureCode.ACTION_MULTILINE,
        ),
        (
            '{"action":"look\\rnow"}',
            ParserFailureCode.ACTION_MULTILINE,
        ),
        (
            '{"action":"look\\u0001"}',
            ParserFailureCode.ACTION_CONTROL_CHARACTER,
        ),
        (
            '{"action":"look\\t"}',
            ParserFailureCode.ACTION_CONTROL_CHARACTER,
        ),
        (
            '{"action":"' + "x" * 257 + '"}',
            ParserFailureCode.ACTION_TOO_LONG,
        ),
    ],
)
def test_rejects_invalid_action_strings(
    raw_response: str,
    expected_code: ParserFailureCode,
) -> None:
    _assert_failure(
        raw_response,
        stage=FailureStage.ACTION_NORMALIZATION,
        code=expected_code,
    )


@pytest.mark.parametrize(
    (
        "raw_response",
        "expected_action",
    ),
    [
        (
            '{"action":"Action: look"}',
            "Action: look",
        ),
        (
            '{"action":"LOOK"}',
            "LOOK",
        ),
        (
            '{"action":"go  to desk 1"}',
            "go  to desk 1",
        ),
    ],
)
def test_parser_does_not_repair_or_canonicalize(
    raw_response: str,
    expected_action: str,
) -> None:
    result = parse_raw_policy_response(
        raw_response
    )

    assert result.status is ParserStatus.SUCCESS
    assert result.normalized_action == expected_action
    assert result.failure_stage is None
    assert result.failure_code is None


def test_exactly_256_action_codepoints_are_allowed() -> None:
    action = "x" * 256

    result = parse_raw_policy_response(
        '{"action":"' + action + '"}'
    )

    assert result.status is ParserStatus.SUCCESS
    assert result.normalized_action == action


def test_custom_action_limit_is_enforced() -> None:
    result = parse_raw_policy_response(
        '{"action":"look"}',
        max_action_codepoints=3,
    )

    assert result.status is ParserStatus.FAILED
    assert (
        result.failure_stage
        is FailureStage.ACTION_NORMALIZATION
    )
    assert (
        result.failure_code
        is ParserFailureCode.ACTION_TOO_LONG
    )


def test_parse_result_is_immutable() -> None:
    result = parse_raw_policy_response(
        '{"action":"look"}'
    )

    with pytest.raises(FrozenInstanceError):
        result.normalized_action = "done"  # type: ignore[misc]


@pytest.mark.parametrize(
    (
        "raw_response",
        "expected_code",
    ),
    [
        (
            "",
            ParserFailureCode.ENVELOPE_INVALID_JSON,
        ),
        (
            " \t\r\n",
            ParserFailureCode.ENVELOPE_INVALID_JSON,
        ),
        (
            '"look"',
            ParserFailureCode.ENVELOPE_TOP_LEVEL_NOT_OBJECT,
        ),
        (
            "123",
            ParserFailureCode.ENVELOPE_TOP_LEVEL_NOT_OBJECT,
        ),
        (
            "true",
            ParserFailureCode.ENVELOPE_TOP_LEVEL_NOT_OBJECT,
        ),
        (
            "{}",
            ParserFailureCode.ENVELOPE_MEMBER_COUNT_INVALID,
        ),
        (
            '{"action":false}',
            ParserFailureCode.ENVELOPE_ACTION_NOT_STRING,
        ),
        (
            '{"action":[]}',
            ParserFailureCode.ENVELOPE_ACTION_NOT_STRING,
        ),
        (
            '{"action":{}}',
            ParserFailureCode.ENVELOPE_ACTION_NOT_STRING,
        ),
        (
            '{"action":Infinity}',
            ParserFailureCode.ENVELOPE_INVALID_JSON,
        ),
        (
            '{"action":-Infinity}',
            ParserFailureCode.ENVELOPE_INVALID_JSON,
        ),
    ],
)
def test_additional_envelope_boundaries(
    raw_response: str,
    expected_code: ParserFailureCode,
) -> None:
    _assert_failure(
        raw_response,
        stage=FailureStage.ENVELOPE,
        code=expected_code,
    )


@pytest.mark.parametrize(
    "raw_response",
    [
        (
            '{"action":"look",'
            '"reason":"first","reason":"second"}'
        ),
        '{"action":{"x":1,"x":2}}',
    ],
)
def test_rejects_duplicate_members_at_any_depth(
    raw_response: str,
) -> None:
    _assert_failure(
        raw_response,
        stage=FailureStage.ENVELOPE,
        code=ParserFailureCode.ENVELOPE_DUPLICATE_MEMBER,
    )


@pytest.mark.parametrize(
    "raw_response",
    [
        '{"action":"look\\u007f"}',
        '{"action":"look\\u0085"}',
        '{"action":"look\\u009f"}',
    ],
)
def test_rejects_c1_control_characters(
    raw_response: str,
) -> None:
    _assert_failure(
        raw_response,
        stage=FailureStage.ACTION_NORMALIZATION,
        code=ParserFailureCode.ACTION_CONTROL_CHARACTER,
    )


def test_only_protocol_outer_whitespace_is_ignored() -> None:
    result = parse_raw_policy_response(
        '\t\r\n {"action":"look"} \n\t'
    )

    assert result.status is ParserStatus.SUCCESS
    assert result.normalized_action == "look"


def test_nonprotocol_outer_whitespace_is_not_trimmed() -> None:
    _assert_failure(
        '\v{"action":"look"}',
        stage=FailureStage.ENVELOPE,
        code=ParserFailureCode.ENVELOPE_INVALID_JSON,
    )

    _assert_failure(
        '{"action":"look"}\f',
        stage=FailureStage.ENVELOPE,
        code=ParserFailureCode.ENVELOPE_TRAILING_DATA,
    )


def test_action_trims_only_ascii_space() -> None:
    result = parse_raw_policy_response(
        '{"action":"\\u00a0look\\u00a0"}'
    )

    assert result.status is ParserStatus.SUCCESS
    assert result.normalized_action == "\u00a0look\u00a0"


def test_unicode_action_is_preserved_exactly() -> None:
    result = parse_raw_policy_response(
        '{"action":"go to caf\\u00e9 1"}'
    )

    assert result.status is ParserStatus.SUCCESS
    assert result.normalized_action == "go to café 1"


def test_length_is_measured_after_ascii_space_trim() -> None:
    action = "x" * 256

    result = parse_raw_policy_response(
        '{"action":" ' + action + ' "}'
    )

    assert result.status is ParserStatus.SUCCESS
    assert result.normalized_action == action


@pytest.mark.parametrize(
    "raw_response",
    [
        b'{"action":"look"}',
        bytearray(b'{"action":"look"}'),
    ],
)
def test_public_parser_rejects_non_string_input(
    raw_response: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="raw_response must be str",
    ):
        parse_raw_policy_response(
            raw_response  # type: ignore[arg-type]
        )
