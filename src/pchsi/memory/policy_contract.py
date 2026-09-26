"""Pure frozen-policy identity contracts for Failure Memory V1."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
import hashlib
import json


REGISTERED_TRAINING_SEEDS = (17, 31, 47)
PRIMARY_SELECTION_RULE = (
    "MINIMUM_POLICY_TRAINING_SEED_FROM_FROZEN_ROUND1_CHECKPOINT_SET"
)
SOURCE_RECORD_EFFECT_POLICY = "ORIGINAL_SOURCE_CHECKPOINT"
SECONDARY_AUDIT_CONDITION = (
    "FM0_NO_PERSISTENT_MEMORY_VS_FM3_GATED_PRESCRIPTIVE_MEMORY"
)


def _require_lower_sha256(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if (
        len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(
            f"{name} must be a 64-character lowercase hexadecimal SHA-256"
        )
    return value


def _require_training_seed(value: object) -> int:
    if type(value) is not int:
        raise TypeError("training_seed must be int")
    if value <= 0:
        raise ValueError("training_seed must be positive")
    return value


@dataclass(frozen=True, slots=True)
class PolicyCheckpointIdentityV1:
    """Exact immutable identity for one registered frozen policy source."""

    training_seed: int
    formal_run_manifest_sha256: str
    adapter_artifact_manifest_sha256: str

    def __post_init__(self) -> None:
        _require_training_seed(self.training_seed)
        _require_lower_sha256(
            "formal_run_manifest_sha256",
            self.formal_run_manifest_sha256,
        )
        _require_lower_sha256(
            "adapter_artifact_manifest_sha256",
            self.adapter_artifact_manifest_sha256,
        )


@dataclass(frozen=True, slots=True)
class PolicySourceRegistryV1:
    """Frozen registry against which observed source bytes are checked."""

    checkpoint_set_root_seal: str
    source_identities: tuple[PolicyCheckpointIdentityV1, ...]

    def __post_init__(self) -> None:
        _require_lower_sha256(
            "checkpoint_set_root_seal",
            self.checkpoint_set_root_seal,
        )
        if type(self.source_identities) is not tuple:
            raise TypeError("source_identities must be tuple")
        if not all(
            isinstance(identity, PolicyCheckpointIdentityV1)
            for identity in self.source_identities
        ):
            raise TypeError(
                "source_identities must contain PolicyCheckpointIdentityV1"
            )

        seeds = tuple(
            identity.training_seed
            for identity in self.source_identities
        )
        if len(set(seeds)) != len(seeds):
            raise ValueError("duplicate training seed")
        if tuple(sorted(seeds)) != REGISTERED_TRAINING_SEEDS:
            raise ValueError(
                "registered training seed set must be exactly (17, 31, 47)"
            )


@dataclass(frozen=True, slots=True)
class FailureMemoryPrimaryPolicyContractV1:
    """Frozen primary/secondary policy identity used by Failure Memory V1."""

    checkpoint_set_root_seal: str
    selection_rule: str
    primary_training_seed: int
    primary_checkpoint_identity: PolicyCheckpointIdentityV1
    secondary_training_seeds: tuple[int, ...]
    secondary_checkpoint_identities: tuple[PolicyCheckpointIdentityV1, ...]
    source_record_effect_policy: str
    secondary_audit_condition: str
    no_best_of_checkpoint: bool
    all_secondary_results_reported: bool

    def __post_init__(self) -> None:
        _require_lower_sha256(
            "checkpoint_set_root_seal",
            self.checkpoint_set_root_seal,
        )
        if self.selection_rule != PRIMARY_SELECTION_RULE:
            raise ValueError("selection_rule mismatch")
        if self.primary_training_seed != min(REGISTERED_TRAINING_SEEDS):
            raise ValueError("primary_training_seed mismatch")
        if (
            self.primary_checkpoint_identity.training_seed
            != self.primary_training_seed
        ):
            raise ValueError("primary checkpoint seed mismatch")
        if self.secondary_training_seeds != (31, 47):
            raise ValueError("secondary_training_seeds mismatch")
        if tuple(
            identity.training_seed
            for identity in self.secondary_checkpoint_identities
        ) != self.secondary_training_seeds:
            raise ValueError("secondary checkpoint seeds mismatch")
        if self.source_record_effect_policy != SOURCE_RECORD_EFFECT_POLICY:
            raise ValueError("source_record_effect_policy mismatch")
        if self.secondary_audit_condition != SECONDARY_AUDIT_CONDITION:
            raise ValueError("secondary_audit_condition mismatch")
        if self.no_best_of_checkpoint is not True:
            raise ValueError("no_best_of_checkpoint must be true")
        if self.all_secondary_results_reported is not True:
            raise ValueError("all_secondary_results_reported must be true")


def _index_identities(
    identities: Sequence[PolicyCheckpointIdentityV1],
    *,
    label: str,
) -> dict[int, PolicyCheckpointIdentityV1]:
    if isinstance(identities, (str, bytes, bytearray)):
        raise TypeError(f"{label} must be a sequence")
    frozen = tuple(identities)
    if not all(
        isinstance(identity, PolicyCheckpointIdentityV1)
        for identity in frozen
    ):
        raise TypeError(
            f"{label} must contain PolicyCheckpointIdentityV1"
        )
    result: dict[int, PolicyCheckpointIdentityV1] = {}
    for identity in frozen:
        seed = identity.training_seed
        if seed in result:
            raise ValueError(f"{label} contains duplicate training seed")
        result[seed] = identity
    return result


def build_primary_policy_contract(
    *,
    registry: PolicySourceRegistryV1,
    observed_source_identities: Sequence[PolicyCheckpointIdentityV1],
    observed_checkpoint_set_root_seal: str,
) -> FailureMemoryPrimaryPolicyContractV1:
    """Build the deterministic contract from exact observed identities only."""

    if not isinstance(registry, PolicySourceRegistryV1):
        raise TypeError("registry must be PolicySourceRegistryV1")

    observed_checkpoint_set_root_seal = _require_lower_sha256(
        "observed_checkpoint_set_root_seal",
        observed_checkpoint_set_root_seal,
    )
    if observed_checkpoint_set_root_seal != registry.checkpoint_set_root_seal:
        raise ValueError("checkpoint_set_root_seal mismatch")

    expected = _index_identities(
        registry.source_identities,
        label="registry.source_identities",
    )
    observed = _index_identities(
        observed_source_identities,
        label="observed_source_identities",
    )

    if set(observed) != set(expected):
        raise ValueError("observed source identity seed set mismatch")

    for seed in REGISTERED_TRAINING_SEEDS:
        if observed[seed] != expected[seed]:
            raise ValueError(
                f"observed source identity mismatch for training seed {seed}"
            )

    primary_seed = min(REGISTERED_TRAINING_SEEDS)
    secondary_seeds = tuple(
        seed
        for seed in REGISTERED_TRAINING_SEEDS
        if seed != primary_seed
    )

    return FailureMemoryPrimaryPolicyContractV1(
        checkpoint_set_root_seal=registry.checkpoint_set_root_seal,
        selection_rule=PRIMARY_SELECTION_RULE,
        primary_training_seed=primary_seed,
        primary_checkpoint_identity=expected[primary_seed],
        secondary_training_seeds=secondary_seeds,
        secondary_checkpoint_identities=tuple(
            expected[seed]
            for seed in secondary_seeds
        ),
        source_record_effect_policy=SOURCE_RECORD_EFFECT_POLICY,
        secondary_audit_condition=SECONDARY_AUDIT_CONDITION,
        no_best_of_checkpoint=True,
        all_secondary_results_reported=True,
    )


def policy_contract_dict(
    contract: FailureMemoryPrimaryPolicyContractV1,
) -> dict[str, object]:
    """Return the JSON-ready closed contract object."""

    if not isinstance(contract, FailureMemoryPrimaryPolicyContractV1):
        raise TypeError(
            "contract must be FailureMemoryPrimaryPolicyContractV1"
        )
    return asdict(contract)


def canonical_policy_contract_json(
    contract: FailureMemoryPrimaryPolicyContractV1,
) -> bytes:
    """Return deterministic canonical JSON with exactly one trailing LF."""

    payload = policy_contract_dict(contract)
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_policy_contract(
    contract: FailureMemoryPrimaryPolicyContractV1,
) -> str:
    """Hash the exact canonical policy-contract bytes."""

    return hashlib.sha256(
        canonical_policy_contract_json(contract)
    ).hexdigest()
