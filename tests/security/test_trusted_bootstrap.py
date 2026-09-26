from __future__ import annotations

from dataclasses import replace

import pytest

from pchsi.security.contracts import (
    BootstrapContract,
    BootstrapState,
    LandlockPathRule,
    LandlockPolicy,
)
from pchsi.security.execution_gate import ExecutionNotApprovedError
from pchsi.security.trusted_bootstrap import (
    ClosedBootstrapKernelAdapter,
    P18_ATTRIBUTION_SEQUENCE,
    apply_bootstrap_security_layers,
    validate_bootstrap_state,
    validate_p18_attribution_events,
)


def _sha(character: str) -> str:
    return character * 64


def _contract() -> BootstrapContract:
    return BootstrapContract(
        runtime_manifest_sha256=_sha("1"),
        bootstrap_filter_sha256=_sha("2"),
        collector_filter_sha256=_sha("3"),
        minimum_landlock_abi=1,
        require_landlock_when_supported=True,
        allowed_fds=(0, 1, 2),
    )


def _state() -> BootstrapState:
    return BootstrapState(
        runtime_manifest_sha256=_sha("1"),
        bootstrap_filter_sha256=_sha("2"),
        collector_filter_sha256=_sha("3"),
        landlock_abi=3,
        landlock_enforced=True,
        mount_contract_verified=True,
        procfs_contract_verified=True,
        capability_contract_verified=True,
        fd_contract_verified=True,
        environment_contract_verified=True,
        inherited_fds=(0, 1, 2),
    )


def _policy() -> LandlockPolicy:
    return LandlockPolicy(
        profile_id="S1_LANDLOCK_ATTRIBUTION_TEST_PROFILE_V1",
        minimum_abi=1,
        handled_access_fs=3,
        rules=(
            LandlockPathRule(
                path="/landlock/allowed",
                access_fs=1,
            ),
        ),
        profile_sha256=_sha("4"),
    )


def test_valid_bootstrap_state_matches_exact_contract() -> None:
    validate_bootstrap_state(
        state=_state(),
        expected=_contract(),
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "runtime_manifest_sha256",
            "a" * 64,
            "runtime_manifest_sha256",
        ),
        (
            "mount_contract_verified",
            False,
            "mount_contract_verified",
        ),
        (
            "inherited_fds",
            (0, 1, 2, 9),
            "FD allowlist",
        ),
        (
            "landlock_enforced",
            False,
            "must be enforced",
        ),
    ],
)
def test_bootstrap_state_rejects_mismatch(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_bootstrap_state(
            state=replace(
                _state(),
                **{field: value},
            ),
            expected=_contract(),
        )


def test_unsupported_landlock_is_allowed_but_not_claimed() -> None:
    validate_bootstrap_state(
        state=replace(
            _state(),
            landlock_abi=None,
            landlock_enforced=False,
        ),
        expected=_contract(),
    )


def test_landlock_abi_below_minimum_is_rejected() -> None:
    with pytest.raises(ValueError, match="below"):
        validate_bootstrap_state(
            state=replace(
                _state(),
                landlock_abi=1,
            ),
            expected=replace(
                _contract(),
                minimum_landlock_abi=2,
            ),
        )


def test_p18_exact_sequence_is_accepted() -> None:
    assert validate_p18_attribution_events(
        P18_ATTRIBUTION_SEQUENCE
    ) == P18_ATTRIBUTION_SEQUENCE


def test_p18_preopened_denied_path_is_rejected() -> None:
    events = list(P18_ATTRIBUTION_SEQUENCE)
    events.insert(
        events.index("landlock_install"),
        "landlock_open_denied_after_restriction",
    )

    with pytest.raises(ValueError, match="sequence"):
        validate_p18_attribution_events(events)


def test_p18_nonidentical_operation_is_rejected() -> None:
    events = list(P18_ATTRIBUTION_SEQUENCE)
    index = events.index(
        "landlock_perform_identical_operations"
    )
    events[index] = "landlock_perform_different_operations"

    with pytest.raises(ValueError, match="sequence"):
        validate_p18_attribution_events(events)


class FakeAdapter:
    def __init__(self, abi: int | None) -> None:
        self.abi = abi
        self.calls: list[str] = []

    def query_landlock_abi(self) -> int | None:
        self.calls.append("query")
        return self.abi

    def install_landlock(self, policy: LandlockPolicy) -> None:
        assert policy == _policy()
        self.calls.append("landlock")

    def install_collector_filter(self, program: bytes) -> None:
        assert program == b"filter"
        self.calls.append("filter")


def test_fake_adapter_applies_landlock_before_collector_filter() -> None:
    adapter = FakeAdapter(abi=3)

    assert apply_bootstrap_security_layers(
        adapter=adapter,
        policy=_policy(),
        collector_filter=b"filter",
    ) == 3

    assert adapter.calls == [
        "query",
        "landlock",
        "filter",
    ]


def test_fake_adapter_skips_landlock_when_unsupported() -> None:
    adapter = FakeAdapter(abi=None)

    assert apply_bootstrap_security_layers(
        adapter=adapter,
        policy=_policy(),
        collector_filter=b"filter",
    ) is None

    assert adapter.calls == [
        "query",
        "filter",
    ]


def test_real_adapter_placeholder_is_fail_closed() -> None:
    adapter = ClosedBootstrapKernelAdapter()

    with pytest.raises(
        ExecutionNotApprovedError,
        match="PCHSI_EXECUTION_NOT_APPROVED",
    ):
        adapter.query_landlock_abi()
