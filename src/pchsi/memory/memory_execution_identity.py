from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    require_nonnegative_int,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.source_state_contracts import (
    SourceDecisionStateFingerprintV1,
)


class MemoryBranchRoleV1(str, Enum):
    MEMORY_OFF = "MEMORY_OFF"
    MEMORY_ON = "MEMORY_ON"


def _budget_dict(
    value: BudgetState,
) -> dict[str, object]:
    if not isinstance(value, BudgetState):
        raise TypeError(
            "budget_state must be BudgetState"
        )
    return {
        "policy_attempt_count": value.policy_attempt_count,
        "environment_step_count": value.environment_step_count,
        "protocol_failure_count": value.protocol_failure_count,
        "inadmissible_action_count": value.inadmissible_action_count,
        "consecutive_nonexecuted_attempt_count": (
            value.consecutive_nonexecuted_attempt_count
        ),
    }


def _budget_from(
    value: object,
) -> BudgetState:
    if not isinstance(value, dict):
        raise TypeError("budget_state must be object")
    expected = {
        "policy_attempt_count",
        "environment_step_count",
        "protocol_failure_count",
        "inadmissible_action_count",
        "consecutive_nonexecuted_attempt_count",
    }
    if set(value) != expected:
        raise ValueError(
            "budget_state fields mismatch"
        )
    return BudgetState(**value)


def _sha(
    domain: bytes,
    payload: object,
) -> str:
    return sha256_bytes(
        domain
        + b"\0"
        + canonical_json_bytes(payload)
    )


def _exact(
    value: object,
    expected: set[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = set(value)
    if observed != expected:
        raise ValueError(
            f"{label} fields mismatch: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


@dataclass(frozen=True, slots=True)
class MemoryBoundReplayCellV1:
    pair_id: str
    branch_role: MemoryBranchRoleV1
    source_fingerprint_sha256: str
    source_task_id: str
    source_bundle_sha256: str
    source_policy_condition: str
    model_call_index: int
    policy_checkpoint_id: str
    memory_m0_sha256: str
    observation_sha256: str
    menu_sequence_sha256: str
    budget_state: BudgetState
    memory_snapshot_id: str
    projection_artifact_sha256s: tuple[str, ...]
    continuation_seed: int
    cell_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "pair_id",
            "source_fingerprint_sha256",
            "source_bundle_sha256",
            "memory_m0_sha256",
            "observation_sha256",
            "menu_sequence_sha256",
            "memory_snapshot_id",
        ):
            require_lower_sha256(
                name,
                getattr(self, name),
            )
        if (
            not isinstance(self.source_task_id, str)
            or not self.source_task_id
        ):
            raise ValueError(
                "source_task_id must be nonempty str"
            )
        if (
            not isinstance(
                self.source_policy_condition,
                str,
            )
            or not self.source_policy_condition
        ):
            raise ValueError(
                "source_policy_condition must be nonempty str"
            )
        if (
            not isinstance(
                self.policy_checkpoint_id,
                str,
            )
            or not self.policy_checkpoint_id
        ):
            raise ValueError(
                "policy_checkpoint_id must be nonempty str"
            )
        require_nonnegative_int(
            "model_call_index",
            self.model_call_index,
        )
        require_nonnegative_int(
            "continuation_seed",
            self.continuation_seed,
        )
        _budget_dict(self.budget_state)
        if (
            type(
                self.projection_artifact_sha256s
            )
            is not tuple
        ):
            raise TypeError(
                "projection_artifact_sha256s "
                "must be tuple"
            )
        for value in (
            self.projection_artifact_sha256s
        ):
            require_lower_sha256(
                "projection sha",
                value,
            )
        if (
            self.branch_role
            is MemoryBranchRoleV1.MEMORY_OFF
            and self.projection_artifact_sha256s
        ):
            raise ValueError(
                "MEMORY_OFF rejects projections"
            )
        if (
            self.branch_role
            is MemoryBranchRoleV1.MEMORY_ON
            and not self.projection_artifact_sha256s
        ):
            raise ValueError(
                "MEMORY_ON requires projection"
            )
        expected = _sha(
            b"MEMORY_BOUND_REPLAY_CELL_V1",
            self._identity_payload(),
        )
        if self.cell_id is None:
            object.__setattr__(
                self,
                "cell_id",
                expected,
            )
        elif self.cell_id != expected:
            raise ValueError("cell_id mismatch")

    def _identity_payload(
        self,
    ) -> dict[str, object]:
        return {
            "pair_id": self.pair_id,
            "branch_role": self.branch_role.value,
            "source_fingerprint_sha256": (
                self.source_fingerprint_sha256
            ),
            "source_task_id": self.source_task_id,
            "source_bundle_sha256": (
                self.source_bundle_sha256
            ),
            "source_policy_condition": (
                self.source_policy_condition
            ),
            "model_call_index": (
                self.model_call_index
            ),
            "policy_checkpoint_id": (
                self.policy_checkpoint_id
            ),
            "memory_m0_sha256": (
                self.memory_m0_sha256
            ),
            "observation_sha256": (
                self.observation_sha256
            ),
            "menu_sequence_sha256": (
                self.menu_sequence_sha256
            ),
            "budget_state": _budget_dict(
                self.budget_state
            ),
            "memory_snapshot_id": (
                self.memory_snapshot_id
            ),
            "projection_artifact_sha256s": list(
                self.projection_artifact_sha256s
            ),
            "continuation_seed": (
                self.continuation_seed
            ),
        }

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema_id": (
                "MEMORY_BOUND_REPLAY_CELL_V1"
            ),
            "schema_version": 1,
            **self._identity_payload(),
            "cell_id": self.cell_id,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(
            self.to_dict()
        )

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryBoundReplayCellV1":
        payload = _exact(
            value,
            {
                "schema_id",
                "schema_version",
                "pair_id",
                "branch_role",
                "source_fingerprint_sha256",
                "source_task_id",
                "source_bundle_sha256",
                "source_policy_condition",
                "model_call_index",
                "policy_checkpoint_id",
                "memory_m0_sha256",
                "observation_sha256",
                "menu_sequence_sha256",
                "budget_state",
                "memory_snapshot_id",
                "projection_artifact_sha256s",
                "continuation_seed",
                "cell_id",
            },
            "memory-bound replay cell",
        )
        if (
            payload["schema_id"]
            != "MEMORY_BOUND_REPLAY_CELL_V1"
            or payload["schema_version"] != 1
        ):
            raise ValueError(
                "cell schema mismatch"
            )
        raw_projection = payload[
            "projection_artifact_sha256s"
        ]
        if not isinstance(
            raw_projection,
            list,
        ):
            raise TypeError(
                "projection_artifact_sha256s "
                "must be array"
            )
        return cls(
            pair_id=payload["pair_id"],
            branch_role=MemoryBranchRoleV1(
                payload["branch_role"]
            ),
            source_fingerprint_sha256=payload[
                "source_fingerprint_sha256"
            ],
            source_task_id=payload[
                "source_task_id"
            ],
            source_bundle_sha256=payload[
                "source_bundle_sha256"
            ],
            source_policy_condition=payload[
                "source_policy_condition"
            ],
            model_call_index=payload[
                "model_call_index"
            ],
            policy_checkpoint_id=payload[
                "policy_checkpoint_id"
            ],
            memory_m0_sha256=payload[
                "memory_m0_sha256"
            ],
            observation_sha256=payload[
                "observation_sha256"
            ],
            menu_sequence_sha256=payload[
                "menu_sequence_sha256"
            ],
            budget_state=_budget_from(
                payload["budget_state"]
            ),
            memory_snapshot_id=payload[
                "memory_snapshot_id"
            ],
            projection_artifact_sha256s=tuple(
                raw_projection
            ),
            continuation_seed=payload[
                "continuation_seed"
            ],
            cell_id=payload["cell_id"],
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "MemoryBoundReplayCellV1":
        return cls.from_dict(
            strict_json_loads(value)
        )


@dataclass(frozen=True, slots=True)
class MemoryBoundReplayPairV1:
    pair_id: str
    memory_off: MemoryBoundReplayCellV1
    memory_on: MemoryBoundReplayCellV1

    def __post_init__(self) -> None:
        require_lower_sha256(
            "pair_id",
            self.pair_id,
        )
        if (
            self.memory_off.branch_role
            is not MemoryBranchRoleV1.MEMORY_OFF
        ):
            raise ValueError(
                "memory_off role mismatch"
            )
        if (
            self.memory_on.branch_role
            is not MemoryBranchRoleV1.MEMORY_ON
        ):
            raise ValueError(
                "memory_on role mismatch"
            )
        if (
            self.memory_off.pair_id
            != self.pair_id
            or self.memory_on.pair_id
            != self.pair_id
        ):
            raise ValueError("pair id mismatch")
        off = self.memory_off._identity_payload()
        on = self.memory_on._identity_payload()
        for key in (
            "branch_role",
            "projection_artifact_sha256s",
        ):
            off.pop(key)
            on.pop(key)
        if off != on:
            raise ValueError(
                "paired cells differ outside "
                "Memory exposure"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema_id": (
                "MEMORY_BOUND_REPLAY_PAIR_V1"
            ),
            "schema_version": 1,
            "pair_id": self.pair_id,
            "memory_off": (
                self.memory_off.to_dict()
            ),
            "memory_on": (
                self.memory_on.to_dict()
            ),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(
            self.to_dict()
        )

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryBoundReplayPairV1":
        payload = _exact(
            value,
            {
                "schema_id",
                "schema_version",
                "pair_id",
                "memory_off",
                "memory_on",
            },
            "memory-bound replay pair",
        )
        if (
            payload["schema_id"]
            != "MEMORY_BOUND_REPLAY_PAIR_V1"
            or payload["schema_version"] != 1
        ):
            raise ValueError(
                "pair schema mismatch"
            )
        return cls(
            pair_id=payload["pair_id"],
            memory_off=(
                MemoryBoundReplayCellV1
                .from_dict(
                    payload["memory_off"]
                )
            ),
            memory_on=(
                MemoryBoundReplayCellV1
                .from_dict(
                    payload["memory_on"]
                )
            ),
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "MemoryBoundReplayPairV1":
        return cls.from_dict(
            strict_json_loads(value)
        )


def build_memory_bound_replay_pair_v1(
    *,
    source_fingerprint: (
        SourceDecisionStateFingerprintV1
    ),
    policy_checkpoint_id: str,
    memory_snapshot_id: str,
    memory_on_projection_sha256s: tuple[str, ...],
    continuation_seed: int,
) -> MemoryBoundReplayPairV1:
    if not isinstance(
        source_fingerprint,
        SourceDecisionStateFingerprintV1,
    ):
        raise TypeError(
            "source_fingerprint type mismatch"
        )
    require_lower_sha256(
        "memory_snapshot_id",
        memory_snapshot_id,
    )
    if (
        type(memory_on_projection_sha256s)
        is not tuple
        or not memory_on_projection_sha256s
    ):
        raise ValueError(
            "Memory ON projection set "
            "must be nonempty tuple"
        )
    for value in (
        memory_on_projection_sha256s
    ):
        require_lower_sha256(
            "projection sha",
            value,
        )
    require_nonnegative_int(
        "continuation_seed",
        continuation_seed,
    )
    if (
        not isinstance(
            policy_checkpoint_id,
            str,
        )
        or not policy_checkpoint_id
    ):
        raise ValueError(
            "policy_checkpoint_id "
            "must be nonempty str"
        )

    pair_id = _sha(
        b"MEMORY_BOUND_REPLAY_PAIR_V1",
        {
            "source_fingerprint_sha256": (
                source_fingerprint
                .fingerprint_sha256
            ),
            "policy_checkpoint_id": (
                policy_checkpoint_id
            ),
            "memory_snapshot_id": (
                memory_snapshot_id
            ),
            "projection_artifact_sha256s": list(
                memory_on_projection_sha256s
            ),
            "continuation_seed": (
                continuation_seed
            ),
        },
    )

    common = dict(
        pair_id=pair_id,
        source_fingerprint_sha256=(
            source_fingerprint
            .fingerprint_sha256
        ),
        source_task_id=(
            source_fingerprint.source_task_id
        ),
        source_bundle_sha256=(
            source_fingerprint
            .source_bundle_sha256
        ),
        source_policy_condition=(
            source_fingerprint
            .source_policy_condition
        ),
        model_call_index=(
            source_fingerprint.model_call_index
        ),
        policy_checkpoint_id=(
            policy_checkpoint_id
        ),
        memory_m0_sha256=(
            source_fingerprint.memory_m0_sha256
        ),
        observation_sha256=(
            source_fingerprint
            .observation_sha256
        ),
        menu_sequence_sha256=(
            source_fingerprint
            .menu_sequence_sha256
        ),
        budget_state=(
            source_fingerprint.budget_state
        ),
        memory_snapshot_id=(
            memory_snapshot_id
        ),
        continuation_seed=(
            continuation_seed
        ),
    )

    return MemoryBoundReplayPairV1(
        pair_id=pair_id,
        memory_off=MemoryBoundReplayCellV1(
            branch_role=(
                MemoryBranchRoleV1.MEMORY_OFF
            ),
            projection_artifact_sha256s=(),
            **common,
        ),
        memory_on=MemoryBoundReplayCellV1(
            branch_role=(
                MemoryBranchRoleV1.MEMORY_ON
            ),
            projection_artifact_sha256s=(
                memory_on_projection_sha256s
            ),
            **common,
        ),
    )
