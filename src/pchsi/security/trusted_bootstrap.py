"""Pure trusted-bootstrap contracts for the S1 backend probe.

This module contains no reachable real Landlock or seccomp installation
path while backend-probe execution remains unapproved.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from .contracts import (
    BootstrapContract,
    BootstrapState,
    LandlockPolicy,
)
from .execution_gate import (
    EXECUTION_NOT_APPROVED_MARKER,
    ExecutionNotApprovedError,
)


__all__ = [
    "BootstrapKernelAdapter",
    "ClosedBootstrapKernelAdapter",
    "P18_ATTRIBUTION_SEQUENCE",
    "apply_bootstrap_security_layers",
    "validate_bootstrap_state",
    "validate_p18_attribution_events",
]


P18_ATTRIBUTION_SEQUENCE: tuple[str, ...] = (
    "close_inherited_fds",
    "verify_fd_allowlist",
    "create_fixtures",
    "baseline_child_start",
    "baseline_open_allowed_after_start",
    "baseline_open_denied_after_start",
    "baseline_perform_identical_operations",
    "baseline_child_destroyed",
    "landlock_child_start",
    "landlock_close_inherited_fds",
    "landlock_verify_fd_allowlist",
    "landlock_install",
    "landlock_open_allowed_after_restriction",
    "landlock_open_denied_after_restriction",
    "landlock_perform_identical_operations",
    "landlock_child_destroyed",
)


@runtime_checkable
class BootstrapKernelAdapter(Protocol):
    """Kernel-facing interface used only through reviewed adapters."""

    def query_landlock_abi(self) -> int | None:
        """Return the supported Landlock ABI, or None when unsupported."""

    def install_landlock(self, policy: LandlockPolicy) -> None:
        """Install the reviewed Landlock policy."""

    def install_collector_filter(self, program: bytes) -> None:
        """Install the reviewed collector seccomp filter."""


class ClosedBootstrapKernelAdapter:
    """Fail-closed placeholder until an external execution record exists."""

    @staticmethod
    def _reject() -> None:
        raise ExecutionNotApprovedError(
            f"{EXECUTION_NOT_APPROVED_MARKER}: "
            "real trusted-bootstrap kernel operations are not approved"
        )

    def query_landlock_abi(self) -> int | None:
        self._reject()

    def install_landlock(self, policy: LandlockPolicy) -> None:
        del policy
        self._reject()

    def install_collector_filter(self, program: bytes) -> None:
        del program
        self._reject()


def validate_bootstrap_state(
    *,
    state: BootstrapState,
    expected: BootstrapContract,
) -> None:
    """Validate one post-bootstrap state against exact frozen identities."""

    exact_hashes = (
        (
            "runtime_manifest_sha256",
            state.runtime_manifest_sha256,
            expected.runtime_manifest_sha256,
        ),
        (
            "bootstrap_filter_sha256",
            state.bootstrap_filter_sha256,
            expected.bootstrap_filter_sha256,
        ),
        (
            "collector_filter_sha256",
            state.collector_filter_sha256,
            expected.collector_filter_sha256,
        ),
    )

    for name, observed, required in exact_hashes:
        if observed != required:
            raise ValueError(f"{name} does not match the bootstrap contract")

    verification_flags = (
        ("mount_contract_verified", state.mount_contract_verified),
        ("procfs_contract_verified", state.procfs_contract_verified),
        ("capability_contract_verified", state.capability_contract_verified),
        ("fd_contract_verified", state.fd_contract_verified),
        ("environment_contract_verified", state.environment_contract_verified),
    )

    for name, value in verification_flags:
        if value is not True:
            raise ValueError(f"{name} must be true")

    if state.inherited_fds != expected.allowed_fds:
        raise ValueError("inherited_fds do not match the exact FD allowlist")

    if state.landlock_abi is None:
        if state.landlock_enforced:
            raise ValueError("Landlock cannot be enforced without an ABI")
        return

    if state.landlock_abi < expected.minimum_landlock_abi:
        raise ValueError("Landlock ABI is below the required minimum")

    if expected.require_landlock_when_supported and not state.landlock_enforced:
        raise ValueError("Landlock must be enforced when supported")


def validate_p18_attribution_events(
    events: Sequence[str],
) -> tuple[str, ...]:
    """Require the exact P18 baseline/Landlock attribution ordering."""

    observed = tuple(events)

    if observed != P18_ATTRIBUTION_SEQUENCE:
        raise ValueError("P18 attribution event sequence mismatch")

    install_index = observed.index("landlock_install")

    for index, event in enumerate(observed):
        if event.startswith("landlock_open_") and index <= install_index:
            raise ValueError(
                "Landlock fixture paths must be opened after restriction"
            )

    baseline_operation = observed[
        observed.index("baseline_perform_identical_operations")
    ].removeprefix("baseline_")
    landlock_operation = observed[
        observed.index("landlock_perform_identical_operations")
    ].removeprefix("landlock_")

    if baseline_operation != landlock_operation:
        raise ValueError(
            "P18 baseline and Landlock operations must be identical"
        )

    return observed


def apply_bootstrap_security_layers(
    *,
    adapter: BootstrapKernelAdapter,
    policy: LandlockPolicy,
    collector_filter: bytes,
) -> int | None:
    """Apply reviewed layers through an injected adapter.

    This function is exercised only with a fake adapter during the
    implementation phase. The real adapter remains fail-closed.
    """

    if not isinstance(collector_filter, bytes) or not collector_filter:
        raise ValueError("collector_filter must be non-empty bytes")

    abi = adapter.query_landlock_abi()

    if abi is not None:
        if abi < policy.minimum_abi:
            raise ValueError("Landlock ABI is below policy minimum")
        adapter.install_landlock(policy)

    adapter.install_collector_filter(collector_filter)
    return abi
