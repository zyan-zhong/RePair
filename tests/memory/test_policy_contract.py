"""Synthetic tests for the Failure Memory V1 frozen-policy contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from importlib import import_module
import inspect
import json

import pytest


def _policy():
    return import_module("pchsi.memory.policy_contract")


def _identity(module, seed: int, char_a: str, char_b: str):
    return module.PolicyCheckpointIdentityV1(
        training_seed=seed,
        formal_run_manifest_sha256=char_a * 64,
        adapter_artifact_manifest_sha256=char_b * 64,
    )


def _registry(module):
    return module.PolicySourceRegistryV1(
        checkpoint_set_root_seal="f" * 64,
        source_identities=(
            _identity(module, 47, "5", "6"),
            _identity(module, 17, "1", "2"),
            _identity(module, 31, "3", "4"),
        ),
    )


def _observed(module):
    registry = _registry(module)
    return tuple(registry.source_identities)


def _contract(module):
    registry = _registry(module)
    return module.build_primary_policy_contract(
        registry=registry,
        observed_source_identities=_observed(module),
        observed_checkpoint_set_root_seal=registry.checkpoint_set_root_seal,
    )


def test_registered_training_seed_set_is_exactly_17_31_47() -> None:
    module = _policy()
    assert module.REGISTERED_TRAINING_SEEDS == (17, 31, 47)
    registry = _registry(module)
    assert tuple(
        sorted(identity.training_seed for identity in registry.source_identities)
    ) == (17, 31, 47)


@pytest.mark.parametrize(
    "identities",
    [
        ((17, "1", "2"), (31, "3", "4")),
        ((17, "1", "2"), (31, "3", "4"), (47, "5", "6"), (53, "7", "8")),
        ((17, "1", "2"), (17, "3", "4"), (47, "5", "6")),
    ],
)
def test_registry_rejects_missing_extra_or_duplicate_seed(
    identities: tuple[tuple[int, str, str], ...],
) -> None:
    module = _policy()
    values = tuple(
        _identity(module, seed, left, right)
        for seed, left, right in identities
    )
    with pytest.raises(ValueError):
        module.PolicySourceRegistryV1(
            checkpoint_set_root_seal="f" * 64,
            source_identities=values,
        )


def test_primary_selection_is_minimum_registered_training_seed() -> None:
    module = _policy()
    contract = _contract(module)
    assert contract.primary_training_seed == 17
    assert contract.primary_checkpoint_identity.training_seed == 17


def test_secondary_training_seeds_are_exactly_31_47() -> None:
    module = _policy()
    contract = _contract(module)
    assert contract.secondary_training_seeds == (31, 47)
    assert tuple(
        identity.training_seed
        for identity in contract.secondary_checkpoint_identities
    ) == (31, 47)


def test_source_record_effect_and_secondary_audit_are_frozen() -> None:
    module = _policy()
    contract = _contract(module)
    assert contract.source_record_effect_policy == "ORIGINAL_SOURCE_CHECKPOINT"
    assert (
        contract.secondary_audit_condition
        == "FM0_NO_PERSISTENT_MEMORY_VS_FM3_GATED_PRESCRIPTIVE_MEMORY"
    )


def test_best_of_checkpoint_is_mechanically_disabled() -> None:
    module = _policy()
    contract = _contract(module)
    assert contract.no_best_of_checkpoint is True
    assert contract.all_secondary_results_reported is True
    signature = inspect.signature(module.build_primary_policy_contract)
    forbidden = {
        "result_metrics",
        "performance",
        "score",
        "memory_effect",
        "best_checkpoint",
        "best_seed",
    }
    assert forbidden.isdisjoint(signature.parameters)


def test_builder_rejects_performance_result_input_by_signature() -> None:
    module = _policy()
    registry = _registry(module)
    with pytest.raises(TypeError):
        module.build_primary_policy_contract(
            registry=registry,
            observed_source_identities=_observed(module),
            observed_checkpoint_set_root_seal=registry.checkpoint_set_root_seal,
            result_metrics={"17": 1.0},  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "formal_run_manifest_sha256",
        "adapter_artifact_manifest_sha256",
    ],
)
def test_observed_wrong_member_sha_is_rejected(field_name: str) -> None:
    module = _policy()
    registry = _registry(module)
    observed = list(_observed(module))
    first = observed[1]  # seed 17 in the deliberately unsorted registry
    kwargs = {
        "training_seed": first.training_seed,
        "formal_run_manifest_sha256": first.formal_run_manifest_sha256,
        "adapter_artifact_manifest_sha256": first.adapter_artifact_manifest_sha256,
    }
    kwargs[field_name] = "e" * 64
    observed[1] = module.PolicyCheckpointIdentityV1(**kwargs)
    with pytest.raises(ValueError, match="source identity mismatch"):
        module.build_primary_policy_contract(
            registry=registry,
            observed_source_identities=tuple(observed),
            observed_checkpoint_set_root_seal=registry.checkpoint_set_root_seal,
        )


def test_checkpoint_set_root_seal_mismatch_is_rejected() -> None:
    module = _policy()
    registry = _registry(module)
    with pytest.raises(ValueError, match="checkpoint_set_root_seal"):
        module.build_primary_policy_contract(
            registry=registry,
            observed_source_identities=_observed(module),
            observed_checkpoint_set_root_seal="0" * 64,
        )


def test_missing_observed_source_identity_is_rejected() -> None:
    module = _policy()
    registry = _registry(module)
    with pytest.raises(ValueError, match="seed set"):
        module.build_primary_policy_contract(
            registry=registry,
            observed_source_identities=_observed(module)[:-1],
            observed_checkpoint_set_root_seal=registry.checkpoint_set_root_seal,
        )


def test_duplicate_observed_training_seed_is_rejected() -> None:
    module = _policy()
    registry = _registry(module)
    observed = _observed(module)
    with pytest.raises(ValueError, match="duplicate training seed"):
        module.build_primary_policy_contract(
            registry=registry,
            observed_source_identities=observed + (observed[0],),
            observed_checkpoint_set_root_seal=registry.checkpoint_set_root_seal,
        )


@pytest.mark.parametrize(
    "bad_sha",
    ["", "a" * 63, "a" * 65, "G" * 64, "z" * 64],
)
def test_policy_source_identity_rejects_noncanonical_sha256(
    bad_sha: str,
) -> None:
    module = _policy()
    with pytest.raises(ValueError):
        module.PolicyCheckpointIdentityV1(
            training_seed=17,
            formal_run_manifest_sha256=bad_sha,
            adapter_artifact_manifest_sha256="b" * 64,
        )


@pytest.mark.parametrize("bad_seed", [True, 0, -1, 17.0, "17"])
def test_policy_source_identity_rejects_non_integer_positive_seed(
    bad_seed: object,
) -> None:
    module = _policy()
    with pytest.raises((TypeError, ValueError)):
        module.PolicyCheckpointIdentityV1(
            training_seed=bad_seed,  # type: ignore[arg-type]
            formal_run_manifest_sha256="a" * 64,
            adapter_artifact_manifest_sha256="b" * 64,
        )


def test_contract_and_identity_records_are_frozen() -> None:
    module = _policy()
    contract = _contract(module)
    with pytest.raises(FrozenInstanceError):
        contract.primary_training_seed = 31  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        contract.primary_checkpoint_identity.training_seed = 31  # type: ignore[misc]


def test_contract_field_surface_contains_no_outcome_or_performance_state() -> None:
    module = _policy()
    field_names = {
        field.name
        for field in fields(module.FailureMemoryPrimaryPolicyContractV1)
    }
    forbidden_fragments = (
        "metric",
        "score",
        "performance",
        "reward",
        "success",
        "effect_value",
    )
    assert not any(
        fragment in field_name
        for field_name in field_names
        for fragment in forbidden_fragments
    )


def test_canonical_policy_contract_json_is_sorted_compact_and_stable() -> None:
    module = _policy()
    contract = _contract(module)
    first = module.canonical_policy_contract_json(contract)
    second = module.canonical_policy_contract_json(contract)
    assert first == second
    assert first.endswith(b"\n")
    assert b"\n" not in first[:-1]
    decoded = json.loads(first)
    rebuilt = (
        json.dumps(
            decoded,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert first == rebuilt
    assert module.sha256_policy_contract(contract) == __import__("hashlib").sha256(first).hexdigest()
