from __future__ import annotations

import json
from pathlib import Path

import pytest

from pchsi.security.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    sha256_hex,
    strict_json_loadb,
    strict_json_loads,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "canonical_vectors.json"
)


def _vectors() -> list[dict[str, object]]:
    payload = json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )
    return list(payload["vectors"])


@pytest.mark.parametrize(
    "vector",
    _vectors(),
    ids=lambda vector: str(vector["id"]),
)
def test_python_strict_json_vectors(
    vector: dict[str, object],
) -> None:
    payload = bytes.fromhex(
        str(vector["input_hex"])
    )
    accepted = bool(vector["accepted"])

    if not accepted:
        with pytest.raises(CanonicalJsonError):
            strict_json_loadb(payload)
        return

    value = strict_json_loadb(payload)
    canonical = canonical_json_bytes(value)

    assert canonical.hex() == vector["canonical_hex"]


def test_string_wrapper_matches_bytes_parser() -> None:
    text = '{"b":2,"a":1}'

    assert strict_json_loads(text) == strict_json_loadb(
        text.encode("utf-8")
    )


def test_canonical_json_rejects_float() -> None:
    with pytest.raises(
        CanonicalJsonError,
        match="unsupported",
    ):
        canonical_json_bytes(
            {"value": 1.5}
        )


@pytest.mark.parametrize(
    "value",
    [
        2**63,
        -(2**63) - 1,
    ],
)
def test_canonical_json_rejects_out_of_range_integer(
    value: int,
) -> None:
    with pytest.raises(
        CanonicalJsonError,
        match="signed 64-bit",
    ):
        canonical_json_bytes(value)


def test_canonical_json_is_deterministic() -> None:
    value = {
        "z": [3, 2, 1],
        "a": {
            "β": True,
            "n": None,
        },
    }

    first = canonical_json_bytes(value)
    second = canonical_json_bytes(value)

    assert first == second
    assert first.endswith(b"\n")
    assert first == (
        '{"a":{"n":null,"β":true},"z":[3,2,1]}\n'
    ).encode("utf-8")


def test_sha256_hex_is_lowercase_and_stable() -> None:
    assert sha256_hex(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


@pytest.mark.parametrize(
    "bad_value",
    [
        bytearray(b"{}"),
        memoryview(b"{}"),
        "{}",
    ],
)
def test_strict_json_loadb_rejects_non_bytes(
    bad_value: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="data must be bytes",
    ):
        strict_json_loadb(
            bad_value  # type: ignore[arg-type]
        )


def test_strict_json_loads_rejects_non_string() -> None:
    with pytest.raises(
        TypeError,
        match="text must be str",
    ):
        strict_json_loads(
            b"{}"  # type: ignore[arg-type]
        )
