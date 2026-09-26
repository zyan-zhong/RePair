from __future__ import annotations

import math

import pytest

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    canonical_json_text,
    require_finite_number,
    require_lower_sha256,
    require_nonnegative_int,
    sha256_bytes,
    strict_json_loads,
)


def test_canonical_json_bytes_are_sorted_compact_utf8_and_lf_terminated() -> None:
    value = {"b": 2, "a": "é"}

    assert canonical_json_bytes(value) == b'{"a":"\xc3\xa9","b":2}\n'
    assert canonical_json_text(value) == '{"a":"é","b":2}\n'
    assert sha256_bytes(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


def test_canonical_json_rejects_nan_infinity_and_duplicate_keys() -> None:
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            canonical_json_bytes({"value": bad})

    with pytest.raises(ValueError, match="duplicate"):
        strict_json_loads('{"a":1,"a":2}')

    for token in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError):
            strict_json_loads(f'{{"value":{token}}}')


def test_strict_integer_rejects_bool() -> None:
    with pytest.raises(TypeError):
        require_nonnegative_int("count", True)

    assert require_nonnegative_int("count", 0) == 0

    with pytest.raises(ValueError):
        require_nonnegative_int("count", -1)

    with pytest.raises(TypeError):
        require_finite_number("score", False)

    assert require_finite_number("score", 1) == 1
    assert require_finite_number("score", 1.5) == 1.5


def test_lower_sha256_is_strict() -> None:
    digest = "a" * 64
    assert require_lower_sha256("digest", digest) == digest

    for bad in ("A" * 64, "a" * 63, "g" * 64, 1):
        with pytest.raises((TypeError, ValueError)):
            require_lower_sha256("digest", bad)
